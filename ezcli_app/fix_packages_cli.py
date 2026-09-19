"""Broken package state diagnostic and repair engine for EasyCLI (ez fix-packages)."""

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.status import Status
from rich.table import Table

from .elevation import elevated_fix_packages


def check_broken_packages() -> Dict[str, Any]:
    """
    Inspect the system for broken, half-configured, or dependency-failed package states.
    Returns diagnostic dictionary.
    """
    unconfigured: List[str] = []
    dpkg_audit_output = ""

    # 1. dpkg --audit
    if shutil.which("dpkg"):
        try:
            res = subprocess.run(["dpkg", "--audit"], capture_output=True, text=True, timeout=15)
            dpkg_audit_output = (res.stdout or "").strip()
            for line in dpkg_audit_output.splitlines():
                # Extract package name from lines like "The following packages are in a mess..."
                if line.startswith(" ") and line.strip():
                    unconfigured.append(line.strip().split()[0])
        except Exception:
            pass

    # 2. Check /var/lib/dpkg/status for non-installed states
    status_file = "/var/lib/dpkg/status"
    if os.path.isfile(status_file):
        try:
            curr_pkg = ""
            with open(status_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("Package: "):
                        curr_pkg = line.split(":", 1)[1].strip()
                    elif line.startswith("Status: "):
                        status = line.split(":", 1)[1].strip()
                        if status not in ("install ok installed", "deinstall ok config-files", "purge ok not-installed"):
                            if curr_pkg and curr_pkg not in unconfigured:
                                unconfigured.append(curr_pkg)
        except (PermissionError, OSError):
            pass

    # 3. apt-get --dry-run --fix-broken install
    to_install: List[str] = []
    to_remove: List[str] = []
    to_upgrade: List[str] = []
    apt_err = ""

    if shutil.which("apt-get"):
        env = os.environ.copy()
        env["LANG"] = "C"
        env["LC_ALL"] = "C"
        try:
            res = subprocess.run(
                ["apt-get", "--dry-run", "--fix-broken", "install"],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            raw_out = res.stdout or ""
            apt_err = (res.stderr or "").strip()

            current_section = ""
            for line in raw_out.splitlines():
                line_str = line.strip()
                if "The following additional packages will be installed:" in line or "The following NEW packages will be installed:" in line:
                    current_section = "install"
                    continue
                elif "The following packages will be REMOVED:" in line:
                    current_section = "remove"
                    continue
                elif "The following packages will be upgraded:" in line:
                    current_section = "upgrade"
                    continue
                elif line_str and not line.startswith(" "):
                    current_section = ""

                if current_section and line.startswith("  "):
                    tokens = line.split()
                    for t in tokens:
                        pkg = t.strip()
                        if pkg and not pkg.startswith("*"):
                            if current_section == "install" and pkg not in to_install:
                                to_install.append(pkg)
                            elif current_section == "remove" and pkg not in to_remove:
                                to_remove.append(pkg)
                            elif current_section == "upgrade" and pkg not in to_upgrade:
                                to_upgrade.append(pkg)
        except Exception as e:
            apt_err = str(e)

    is_broken = bool(unconfigured or to_install or to_remove or to_upgrade or ("dpkg was interrupted" in apt_err.lower()))

    # Calculate risk level
    if to_remove:
        risk = "HIGH"
        risk_desc = "Package removals required to resolve dependency conflicts"
    elif to_install or to_upgrade:
        risk = "MEDIUM"
        risk_desc = "Packages must be installed or updated to satisfy dependencies"
    elif unconfigured:
        risk = "LOW"
        risk_desc = "Packages only need their configuration finalized"
    else:
        risk = "NONE"
        risk_desc = "No repair necessary"

    return {
        "is_broken": is_broken,
        "unconfigured": unconfigured,
        "to_install": to_install,
        "to_remove": to_remove,
        "to_upgrade": to_upgrade,
        "risk": risk,
        "risk_desc": risk_desc,
        "dpkg_audit": dpkg_audit_output,
        "apt_err": apt_err,
    }


def run_fix_packages_cli(console: Optional[Console] = None) -> None:
    """Run interactive broken package check and repair."""
    if console is None:
        console = Console()

    console.print(
        Panel(
            "[bold cyan]🔧 EasyCLI Package Repair Engine[/bold cyan]\n\n"
            "Checking system for interrupted installations, unconfigured packages, and broken dependencies...\n"
            "[dim]Replaces manual 'apt --fix-broken install' and 'dpkg --configure -a'.[/dim]",
            title="[bold blue]Package Health Check[/bold blue]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    with console.status("[bold green]Inspecting package status database...[/bold green]"):
        diag = check_broken_packages()

    # All-Clear State
    if not diag["is_broken"]:
        console.print(
            Panel(
                "✨ [bold green]System Package Health is Excellent![/bold green]\n\n"
                "• All installed APT packages are properly configured.\n"
                "• No interrupted installations or unconfigured packages found.\n"
                "• Package dependency graph is fully satisfied.\n\n"
                "[dim]No repair actions are necessary. Your package database is in top condition.[/dim]",
                title="[bold green]All Clear[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return

    # Broken State: Simulation Preview
    risk_color = "green" if diag["risk"] == "LOW" else ("yellow" if diag["risk"] == "MEDIUM" else "red")
    badge = f"[bold {risk_color}]RISK LEVEL: {diag['risk']}[/bold {risk_color}] — {diag['risk_desc']}"

    preview_lines = [f"{badge}\n"]

    if diag["unconfigured"]:
        preview_lines.append(f"[bold yellow]Unconfigured / Interrupted Packages ({len(diag['unconfigured'])}):[/bold yellow]")
        preview_lines.append("  " + ", ".join(diag["unconfigured"][:15]))
        if len(diag["unconfigured"]) > 15:
            preview_lines.append(f"  [dim]...and {len(diag['unconfigured']) - 15} more[/dim]")
        preview_lines.append("")

    if diag["to_install"]:
        preview_lines.append(f"[bold cyan]Packages to Install ({len(diag['to_install'])}):[/bold cyan]")
        preview_lines.append("  " + ", ".join(diag["to_install"][:15]))
        preview_lines.append("")

    if diag["to_upgrade"]:
        preview_lines.append(f"[bold blue]Packages to Upgrade ({len(diag['to_upgrade'])}):[/bold blue]")
        preview_lines.append("  " + ", ".join(diag["to_upgrade"][:15]))
        preview_lines.append("")

    if diag["to_remove"]:
        preview_lines.append(f"[bold red]Packages to Remove ({len(diag['to_remove'])}):[/bold red]")
        preview_lines.append("  " + ", ".join(diag["to_remove"][:15]))
        preview_lines.append("")

    console.print(
        Panel(
            "\n".join(preview_lines),
            title="[bold red]Broken Package States Detected[/bold red]",
            border_style="red",
            box=box.ROUNDED,
        )
    )

    console.print("[bold]Repair Strategy:[/bold]")
    console.print("  1. Finalize unconfigured packages with [cyan]dpkg --configure -a[/cyan]")
    console.print("  2. Satisfy missing dependencies with [cyan]apt-get --fix-broken install[/cyan]\n")

    if not Confirm.ask("Proceed with repairing these package states now?", default=True, console=console):
        console.print("[dim]Repair cancelled. No system packages were changed.[/dim]")
        return

    # Execution Phase
    console.print("\n[dim]Requesting administrator consent to apply repairs...[/dim]")
    ok, log_output, err = elevated_fix_packages(console=console)

    if ok:
        console.print(
            Panel(
                "✨ [bold green]All Package States Successfully Repaired![/bold green]\n\n"
                "• All pending package configurations were completed.\n"
                "• Broken dependencies and interrupted states were cleanly resolved.\n\n"
                "[dim]Your system package manager is healthy and ready for upgrades.[/dim]",
                title="[bold green]Repair Complete[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]Package Repair Encountered Issues:[/bold red]\n\n"
                f"{err or 'Repair process exited with non-zero status.'}\n\n"
                f"[dim]Log details:\n{log_output[-500:] if log_output else 'No log output.'}[/dim]",
                title="[bold red]Repair Failed[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
