"""Command-line interface orchestrator for 'ez run'.

Provides universal application and script execution with:
- Strict resolution hierarchy (file path -> PATH binary -> Snap -> Flatpak -> desktop entry)
- GUI classification and detached background execution with task manager tips
- Foreground CLI execution with mandatory '▶ Running ...' summary
- Safe, flag-free Guided Mode with static/dynamic option extraction and preview confirmation
- Automatic elevation prompt on permission errors
- FUSE dependency troubleshooting for AppImages
"""

import os
import shlex
import stat
import subprocess
from typing import List, Optional, Sequence

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .run_detector import ResolvedTarget, resolve_target
from .run_guide import (
    HelpOption,
    parse_help_text,
    run_guided_form,
    safe_probe_help,
    static_parse_python_script,
    static_parse_shell_script,
)


def _handle_chmod(target: ResolvedTarget, console: Console) -> bool:
    """Prompt user for consent to make target file executable (chmod +x).

    Returns True if file is executable or can proceed, False if user declined and file cannot run.
    """
    if not target.file_path or not os.path.exists(target.file_path):
        return True

    console.print()
    should_chmod = Confirm.ask(
        f"The file '[bold cyan]{target.name}[/bold cyan]' is not marked as executable.\n"
        f"Make it executable ([bold green]chmod +x[/bold green])?",
        default=True,
    )
    if should_chmod:
        try:
            st = os.stat(target.file_path)
            os.chmod(target.file_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            console.print(f"[bold green]✔[/bold green] Granted executable permission to [bold cyan]{target.name}[/bold cyan].")
            target.is_executable = True
            target.needs_chmod = False
            return True
        except PermissionError:
            elevate = Confirm.ask(
                "Permission denied. Grant executable permission using administrator privileges?",
                default=True,
            )
            if elevate:
                from .elevation import elevated_run_command

                ok, _, err = elevated_run_command(
                    ["chmod", "+x", target.file_path],
                    reason=f"Make {target.name} executable",
                    task_description=f"chmod +x {target.file_path}",
                    console=console,
                )
                if ok:
                    console.print("[bold green]✔[/bold green] Granted executable permission with administrator privileges.")
                    target.is_executable = True
                    target.needs_chmod = False
                    return True
                else:
                    console.print(f"[bold red]Failed to set permissions:[/bold red] {err}")

            if target.interpreter:
                console.print(f"[dim]Running non-executable script via interpreter: {target.interpreter}[/dim]")
                return True
            console.print("[dim]Cannot execute file without execution permissions.[/dim]")
            return False
        except Exception as e:
            console.print(f"[bold red]Failed to modify file permissions:[/bold red] {e}")
            if target.interpreter:
                return True
            return False
    else:
        if target.interpreter:
            console.print(f"[dim]Running non-executable script via interpreter: {target.interpreter}[/dim]")
            return True
        console.print("[dim]Execution cancelled (file is not executable).[/dim]")
        return False


def _launch_gui(target: ResolvedTarget, extra_args: List[str], console: Console) -> None:
    """Launch a GUI target detached in the background."""
    full_cmd = list(target.exec_cmd) + extra_args
    target_cwd = (
        os.path.dirname(target.file_path)
        if target.file_path and os.path.exists(target.file_path)
        else os.getcwd()
    )

    try:
        proc = subprocess.Popen(
            full_cmd,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=target_cwd,
        )

        # Wait briefly (0.3s) to see if it immediately crashes with a library/FUSE/permission error
        try:
            stdout, stderr = proc.communicate(timeout=0.3)
            # If it terminated already
            if proc.returncode != 0:
                err_text = ((stderr or b"") + (stdout or b"")).decode("utf-8", errors="replace").strip()
                if "fuse" in err_text.lower() or "libfuse" in err_text.lower():
                    console.print()
                    console.print(
                        Panel(
                            f"[bold red]AppImage failed to start:[/bold red] {err_text}\n\n"
                            "[bold yellow]FUSE (Filesystem in Userspace) library is required to run AppImages.[/bold yellow]\n"
                            "To resolve this, install libfuse for your distribution:\n"
                            "  • [bold cyan]Ubuntu / Debian:[/bold cyan] sudo apt install libfuse2\n"
                            "  • [bold cyan]Fedora:[/bold cyan] sudo dnf install fuse-libs\n"
                            "  • [bold cyan]Arch Linux:[/bold cyan] sudo pacman -S fuse2\n\n"
                            f"💡 Alternatively, you can run the AppImage with extraction:\n"
                            f"  [bold white]{full_cmd[0]} --appimage-extract-and-run[/bold white]",
                            title="⚠️ [bold red]AppImage FUSE Dependency Missing[/bold red]",
                            border_style="red",
                            box=box.ROUNDED,
                            padding=(1, 2),
                        )
                    )
                    return
                elif "permission denied" in err_text.lower() or proc.returncode in (126, 13):
                    console.print(f"[bold red]Launch failed (Permission Denied):[/bold red] {err_text}")
                    return
                else:
                    console.print(
                        f"[bold red]Application exited immediately with error code {proc.returncode}:[/bold red]\n{err_text}"
                    )
                    return
        except subprocess.TimeoutExpired:
            # Process is still running, which is expected for GUI applications!
            pass

        console.print()
        console.print(
            Panel(
                f"[bold green]🚀 Launched {target.name} in the background.[/bold green]\n"
                f"[dim]Process PID: {proc.pid}. Your terminal remains free.[/dim]\n\n"
                f"[bold yellow]💡 Tip:[/bold yellow] To inspect or stop running applications, run: [bold cyan]ez task-manager[/bold cyan]",
                title="[bold green]Application Launched[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
    except FileNotFoundError as e:
        console.print(f"[bold red]Command not found:[/bold red] {e}")
    except PermissionError as e:
        console.print(f"[bold red]Permission denied:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Failed to launch GUI application:[/bold red] {e}")


def _extract_options_for_cli(target: ResolvedTarget) -> List[HelpOption]:
    """Extract configurable options using static analysis first, then safe probe."""
    options: List[HelpOption] = []

    # 1. Static parse for scripts (Fix 3: avoids executing scripts for help)
    if target.target_type == "script" and target.file_path and os.path.isfile(target.file_path):
        ext = os.path.splitext(target.file_path)[1].lower()
        if ext == ".py":
            options = static_parse_python_script(target.file_path)
        elif ext in (".sh", ".bash", ".zsh"):
            options = static_parse_shell_script(target.file_path)

    # 2. If no static options, safely probe help
    if not options:
        help_text = safe_probe_help(target.exec_cmd)
        if help_text:
            options = parse_help_text(help_text)

    return options


def _run_cli_foreground(
    target: ResolvedTarget,
    extra_args: List[str],
    console: Console,
) -> None:
    """Execute a CLI target in the foreground with guided mode when no args given."""
    final_cmd: List[str]

    if extra_args:
        # Passthrough arguments given: skip guided mode completely
        final_cmd = list(target.exec_cmd) + extra_args
    else:
        # No arguments given: attempt Guided Mode
        options = _extract_options_for_cli(target)
        if options:
            guided_cmd = run_guided_form(options, target.exec_cmd, target.name, console)
            if guided_cmd is None:
                # User cancelled during guided setup
                return
            final_cmd = guided_cmd
        else:
            # No configurable options detected, run directly
            final_cmd = list(target.exec_cmd)

    target_cwd = (
        os.path.dirname(target.file_path)
        if target.file_path and os.path.exists(target.file_path)
        else os.getcwd()
    )

    # Mandatory summary line before execution
    cmd_display = " ".join(f'"{c}"' if " " in c else c for c in final_cmd)
    console.print(f"[bold green]▶ Running:[/bold green] [bold white]{cmd_display}[/bold white]\n")

    exit_code = 0
    try:
        res = subprocess.run(final_cmd, cwd=target_cwd)
        exit_code = res.returncode
    except PermissionError:
        exit_code = 126
    except KeyboardInterrupt:
        console.print("\n[dim]Process interrupted by user.[/dim]")
        return
    except Exception as e:
        console.print(f"[bold red]Execution error:[/bold red] {e}")
        return

    # Handle Permission Denied (exit code 126 or 13 or PermissionError)
    if exit_code in (126, 13):
        console.print()
        elevate = Confirm.ask(
            "This command requires administrator privileges. Run with admin elevation?",
            default=True,
        )
        if elevate:
            from .elevation import elevated_run_command

            console.print()
            ok, out, err = elevated_run_command(
                cmd=final_cmd,
                reason=f"Run '{target.name}' with administrator privileges",
                task_description=f"Run {target.name}",
                console=console,
            )
            if ok:
                if out:
                    console.print(out, end="")
                if err:
                    console.print(err, style="red", end="")
            else:
                console.print(f"[bold red]Elevated execution failed:[/bold red] {err}")
        return

    # Handle Non-Zero Exit Code with Usage Error Fallback (only when run without extra args)
    if exit_code != 0 and not extra_args:
        help_text = safe_probe_help(target.exec_cmd)
        if help_text:
            retry_options = parse_help_text(help_text)
            if retry_options:
                console.print()
                console.print(
                    Panel(
                        f"The command '[bold cyan]{target.name}[/bold cyan]' exited with code [bold red]{exit_code}[/bold red].\n"
                        "It appears to require flags or options.",
                        title="⚠️ [bold yellow]Command Notice[/bold yellow]",
                        border_style="yellow",
                        box=box.ROUNDED,
                    )
                )
                retry = Confirm.ask("Would you like to retry in guided mode?", default=True)
                if retry:
                    retry_cmd = run_guided_form(retry_options, target.exec_cmd, target.name, console)
                    if retry_cmd:
                        retry_display = " ".join(f'"{c}"' if " " in c else c for c in retry_cmd)
                        console.print(f"[bold green]▶ Running:[/bold green] [bold white]{retry_display}[/bold white]\n")
                        try:
                            subprocess.run(retry_cmd, cwd=target_cwd)
                        except Exception as e:
                            console.print(f"[bold red]Execution error:[/bold red] {e}")


def run_cli_run(
    raw_args: Optional[Sequence[str]] = None,
    console: Optional[Console] = None,
) -> None:
    """Main CLI entry point for 'ez run'.

    Usage:
        ez run <target> [args...]
        ez run choose-directory
        ez run
    """
    console = console or Console()
    args_list = list(raw_args or [])

    # If no target provided on CLI, prompt the user
    if not args_list:
        try:
            user_input = Prompt.ask(
                "[bold cyan]Enter application name or script/binary path to run[/bold cyan] (or [bold green]choose-directory[/bold green] to pick file)",
                default="",
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Run cancelled.[/dim]")
            return

        if not user_input:
            console.print("[dim]Run cancelled.[/dim]")
            return

        try:
            args_list = shlex.split(user_input)
        except ValueError:
            args_list = user_input.split()

    if not args_list:
        console.print("[dim]Run cancelled.[/dim]")
        return

    target_raw = args_list[0]
    extra_args = args_list[1:]

    # Mini explorer file picker support
    if target_raw.lower() in ("choose-directory", "choose", "picker"):
        from .explorer.explorer_app import run_file_picker

        console.print("[bold cyan]Opening file picker to choose an executable, script, or AppImage...[/bold cyan]")
        picked = run_file_picker(initial_dir=".")
        if not picked:
            console.print("[dim]Run cancelled (no file chosen).[/dim]")
            return
        target_raw = picked

    # Resolve target
    target, flatpak_candidates, err_msg = resolve_target(target_raw, cwd=os.getcwd())

    # Ambiguous Flatpak candidates menu (Fix 4)
    if target is None and flatpak_candidates:
        console.print()
        console.print(
            f"[bold cyan]Multiple Flatpak applications found matching '[bold white]{target_raw}[/bold white]':[/bold cyan]\n"
        )
        table = Table(box=box.ROUNDED, header_style="bold cyan")
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Application Name", style="bold white")
        table.add_column("Application ID", style="dim")
        table.add_column("Description", style="dim")

        for idx, (disp, app_id, desc) in enumerate(flatpak_candidates, 1):
            table.add_row(str(idx), disp, app_id, desc)
        console.print(table)

        try:
            choice_str = Prompt.ask(
                f"Select an application (1-{len(flatpak_candidates)}) or 'c' to cancel",
                default="1",
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Run cancelled.[/dim]")
            return

        if choice_str.lower() in ("c", "cancel", "q", "quit"):
            console.print("[dim]Run cancelled.[/dim]")
            return

        try:
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(flatpak_candidates):
                disp, app_id, desc = flatpak_candidates[choice_idx]
                target = ResolvedTarget(
                    name=disp,
                    target_type="flatpak",
                    exec_cmd=["flatpak", "run", app_id],
                    is_gui=True,
                    is_executable=True,
                    description=desc or f"Flatpak application ({app_id})",
                )
            else:
                console.print("[bold red]Invalid selection.[/bold red]")
                return
        except ValueError:
            console.print("[bold red]Invalid selection.[/bold red]")
            return

    # If target is still None: not found
    if target is None:
        console.print()
        console.print(
            Panel(
                f"[bold red]Target '{target_raw}' was not found.[/bold red]\n\n"
                f"{err_msg}\n\n"
                f"[bold yellow]💡 Looking to install it?[/bold yellow] Search available packages across APT, Snap, and Flatpak with:\n"
                f"  [bold cyan]ez package-search {target_raw}[/bold cyan]",
                title="❌ [bold red]Application Not Found[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        return

    # Check executable permission / chmod
    if target.needs_chmod:
        ok = _handle_chmod(target, console)
        if not ok:
            return

    # Execute target (GUI vs CLI)
    if target.is_gui:
        _launch_gui(target, extra_args, console)
    else:
        _run_cli_foreground(target, extra_args, console)
