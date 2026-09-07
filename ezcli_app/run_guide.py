"""Guided Mode and safe help / static argument parser for 'ez run'.

Extracts configurable options from scripts and CLI binaries without requiring
the user to remember cryptic flags. Features:
- Safe help probing with stdin=/dev/null and timeout.
- Static AST/regex inspection for scripts to prevent execution side-effects.
- Interactive question form with skip/defaults and mini explorer path selection.
- Mandatory command preview and confirmation before running.
- Usage error fallback offering guided retries.
"""

import ast
from dataclasses import dataclass, field
import os
import re
import subprocess
from typing import List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table


@dataclass
class HelpOption:
    """Represents a parsed flag or argument option for a command."""

    flags: List[str]
    name: str
    option_type: str  # "boolean", "valued", "path", "choice"
    help_text: str = ""
    choices: List[str] = field(default_factory=list)
    default_val: str = ""
    metavar: str = ""


HELP_INDICATOR_REGEX = re.compile(
    r"(?i)\b(usage:\s*|options:\s*|arguments:\s*|commands:\s*|synopsis:\s*|flags:\s*)"
)


# =============================================================================
# 1. Static Script Argument Parsing
# =============================================================================

def static_parse_python_script(filepath: str) -> List[HelpOption]:
    """Statically parse argparse calls from a Python script using the AST."""
    options: List[HelpOption] = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        tree = ast.parse(code, filename=filepath)
    except Exception:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Look for .add_argument(...)
        func_name = ""
        if isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            func_name = node.func.id

        if func_name != "add_argument":
            continue

        flags: List[str] = []
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("-"):
                    flags.append(arg.value)

        if not flags:
            continue

        # Extract keyword arguments
        help_text = ""
        default_val = ""
        is_bool = False
        choices: List[str] = []

        for kw in node.keywords:
            if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                help_text = str(kw.value.value)
            elif kw.arg == "default" and isinstance(kw.value, ast.Constant):
                default_val = str(kw.value.value)
            elif kw.arg == "action" and isinstance(kw.value, ast.Constant):
                if kw.value.value in ("store_true", "store_false"):
                    is_bool = True
            elif kw.arg == "choices" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant):
                        choices.append(str(elt.value))

        primary_flag = max(flags, key=len)
        clean_name = primary_flag.lstrip("-").replace("-", " ")

        opt_type = "boolean" if is_bool else "valued"
        if choices:
            opt_type = "choice"
        elif any(w in clean_name.lower() or w in help_text.lower() for w in ("file", "path", "dir", "folder", "dest", "output")):
            opt_type = "path"

        options.append(
            HelpOption(
                flags=flags,
                name=clean_name,
                option_type=opt_type,
                help_text=help_text,
                choices=choices,
                default_val=default_val,
            )
        )

    return options


def static_parse_shell_script(filepath: str) -> List[HelpOption]:
    """Statically parse common getopts or case patterns from a shell script."""
    options: List[HelpOption] = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return []

    # 1. Match getopts "ab:c:"
    getopts_match = re.search(r'getopts\s+["\']([a-zA-Z0-9:]+)["\']', content)
    if getopts_match:
        optstring = getopts_match.group(1)
        i = 0
        while i < len(optstring):
            ch = optstring[i]
            if ch == ":":
                i += 1
                continue
            is_valued = (i + 1 < len(optstring) and optstring[i + 1] == ":")
            flag = f"-{ch}"
            opt_type = "valued" if is_valued else "boolean"
            options.append(
                HelpOption(
                    flags=[flag],
                    name=f"option {ch}",
                    option_type=opt_type,
                    help_text=f"Flag {flag}",
                )
            )
            i += 1

    # 2. Match case patterns: -o|--output)
    case_matches = re.findall(r'^\s*(-[a-zA-Z0-9]|--[a-zA-Z0-9-]+)(?:\|(-[a-zA-Z0-9]|--[a-zA-Z0-9-]+))*\)', content, re.MULTILINE)
    for m in case_matches:
        raw_flags = [f for f in m if f.startswith("-")]
        if raw_flags and not any(f in [o.flags[0] for o in options] for f in raw_flags):
            primary = max(raw_flags, key=len)
            clean_name = primary.lstrip("-").replace("-", " ")
            opt_type = "path" if any(w in clean_name.lower() for w in ("file", "path", "dir", "output")) else "boolean"
            options.append(
                HelpOption(
                    flags=raw_flags,
                    name=clean_name,
                    option_type=opt_type,
                    help_text=f"Option {primary}",
                )
            )

    return options


# =============================================================================
# 2. Safe Dynamic Help Probing (Fix 2)
# =============================================================================

def safe_probe_help(cmd: List[str]) -> Optional[str]:
    """Safely probe a CLI target for help output without side effects.

    Rules:
    - Probe only '--help' by default.
    - Probe '-h' ONLY if '--help' fails AND output contains help patterns (like 'Usage:').
    - Always probe with stdin=/dev/null and timeout.
    """
    try:
        # Step 1: Probe --help
        res = subprocess.run(
            [*cmd, "--help"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2.5,
        )
        combined = f"{res.stdout}\n{res.stderr}".strip()
        if HELP_INDICATOR_REGEX.search(combined):
            return combined

        # Step 2: Only probe -h if --help output specifically suggested -h
        if "-h" in combined and "help" in combined.lower():
            res_h = subprocess.run(
                [*cmd, "-h"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2.0,
            )
            combined_h = f"{res_h.stdout}\n{res_h.stderr}".strip()
            if HELP_INDICATOR_REGEX.search(combined_h):
                return combined_h
    except Exception:
        pass
    return None


# =============================================================================
# 3. Help Text Option Parser
# =============================================================================

def parse_help_text(help_text: str) -> List[HelpOption]:
    """Parse standard POSIX/GNU help output lines into HelpOption items."""
    if not help_text or not HELP_INDICATOR_REGEX.search(help_text):
        return []

    options: List[HelpOption] = []
    lines = help_text.splitlines()

    # Regex to capture: -f, --flag <ARG>   Description text
    option_regex = re.compile(
        r"^\s*(-[a-zA-Z0-9]|--[a-zA-Z0-9][a-zA-Z0-9-_]*)"
        r"(?:,\s*(-[a-zA-Z0-9]|--[a-zA-Z0-9][a-zA-Z0-9-_]*))?"
        r"(?:[ =](<[^>]+>|\[[^\]]+\]|\{[^}]+\}|[A-Z0-9_-]+))?"
        r"\s{2,}(.+)$"
    )

    seen_flags = set()

    for line in lines:
        match = option_regex.match(line)
        if not match:
            continue

        f1 = match.group(1)
        f2 = match.group(2)
        metavar = match.group(3) or ""
        help_desc = (match.group(4) or "").strip()

        flags = [f for f in (f1, f2) if f]
        if any(f in seen_flags for f in flags):
            continue

        # Skip standard help and version flags
        if any(f in ("--help", "-h", "-?", "-help") for f in flags):
            continue
        if any(f in ("--version", "-V") for f in flags) or (
            any(f in ("--version", "-V", "-v") for f in flags) and "version" in help_desc.lower()
        ):
            continue

        for f in flags:
            seen_flags.add(f)

        primary_flag = max(flags, key=len)
        clean_name = primary_flag.lstrip("-").replace("-", " ")

        # Determine type
        opt_type = "boolean"
        choices: List[str] = []

        if metavar:
            clean_meta = metavar.strip("<>[]{}")
            if "{" in metavar and "}" in metavar:
                choices = [c.strip() for c in clean_meta.split(",") if c.strip()]
                opt_type = "choice"
            elif "|" in clean_meta:
                choices = [c.strip() for c in clean_meta.split("|") if c.strip()]
                opt_type = "choice"
            elif any(
                w in clean_name.lower() or w in metavar.lower() or w in help_desc.lower()
                for w in ("file", "path", "dir", "folder", "dest", "output", "source")
            ):
                opt_type = "path"
            else:
                opt_type = "valued"

        options.append(
            HelpOption(
                flags=flags,
                name=clean_name,
                option_type=opt_type,
                help_text=help_desc,
                choices=choices,
                metavar=metavar,
            )
        )

    # Return top actionable options (limit to 12 to avoid overwhelming form)
    return options[:12]


# =============================================================================
# 4. Interactive Guided Form & Safety Confirmation
# =============================================================================

def run_guided_form(
    options: List[HelpOption],
    base_cmd: List[str],
    target_name: str,
    console: Console,
) -> Optional[List[str]]:
    """Present parsed options to the user, assemble the command, and require preview confirmation."""
    console.print()
    console.print(
        Panel(
            f"EasyCLI detected [bold cyan]{len(options)}[/bold cyan] configurable option(s) for '[bold green]{target_name}[/bold green]'.\n\n"
            "[dim]• Answer each question or press [bold]Enter[/bold] to skip and keep the default.\n"
            "• You will see a complete preview before anything is executed.[/dim]",
            title=f"🧭 [bold cyan]Guided Setup: {target_name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    assembled_flags: List[str] = []

    for idx, opt in enumerate(options, 1):
        flag_str = "/".join(opt.flags)
        desc = f"[dim]{opt.help_text}[/dim]" if opt.help_text else ""
        console.print(f"\n[bold yellow]Option {idx}/{len(options)}:[/bold yellow] [bold white]{opt.name}[/bold white] ({flag_str})")
        if desc:
            console.print(f"  {desc}")

        primary_flag = max(opt.flags, key=len)

        try:
            if opt.option_type == "boolean":
                val = Confirm.ask(f"  Enable '[bold cyan]{opt.name}[/bold cyan]'?", default=False)
                if val:
                    assembled_flags.append(primary_flag)

            elif opt.option_type == "choice":
                choices_str = ", ".join(opt.choices)
                console.print(f"  Available choices: [bold cyan]{choices_str}[/bold cyan]")
                ans = Prompt.ask(
                    "  Select choice (or press Enter to skip)",
                    default="",
                ).strip()
                if ans and (ans in opt.choices or ans.lower() in [c.lower() for c in opt.choices]):
                    matched_choice = next((c for c in opt.choices if c.lower() == ans.lower()), ans)
                    assembled_flags.extend([primary_flag, matched_choice])

            elif opt.option_type == "path":
                console.print("  [dim]Enter file/directory path, or type [bold green]choose-directory[/bold green] to pick visually.[/dim]")
                ans = Prompt.ask("  Value (or press Enter to skip)", default="").strip()
                if ans.lower() in ("choose-directory", "choose", "picker"):
                    from .explorer.explorer_app import run_destination_picker
                    picked = run_destination_picker()
                    if picked and isinstance(picked, str):
                        ans = picked
                    else:
                        ans = ""

                if ans:
                    assembled_flags.extend([primary_flag, ans])

            else:  # valued
                ans = Prompt.ask("  Value (or press Enter to skip)", default="").strip()
                if ans:
                    assembled_flags.extend([primary_flag, ans])

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Guided setup cancelled.[/dim]")
            return None

    # Assemble complete command
    final_command = list(base_cmd) + assembled_flags

    # Mandatory Command Preview & Confirmation Step (Safety Net)
    cmd_preview_str = " ".join(f'"{c}"' if " " in c else c for c in final_command)

    console.print()
    console.print(
        Panel(
            f"[bold white]{cmd_preview_str}[/bold white]",
            title="🔍 [bold green]Mandatory Command Preview[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    try:
        confirmed = Confirm.ask("Execute this command? [Y/n]", default=True)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled.[/dim]")
        return None

    if not confirmed:
        console.print("[dim]Command execution cancelled by user.[/dim]")
        return None

    return final_command
