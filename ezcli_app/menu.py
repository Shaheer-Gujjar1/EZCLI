"""Interactive terminal menu for EasyCLI."""

import os
import signal
import sys
from typing import Optional
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

from . import __version__, renderers
from .config import FEATURES, FeatureTemplate
from .distro import detect_distro


class TerminalResizeInterrupt(Exception):
    """Internal exception raised when SIGWINCH interrupts Prompt.ask."""
    pass


_in_menu_prompt = False


def _sigwinch_handler(signum, frame):
    """Handle window resize signal gracefully by interrupting input prompt."""
    global _in_menu_prompt
    if _in_menu_prompt:
        _in_menu_prompt = False
        raise TerminalResizeInterrupt()


def build_header_panel(term_width: int, distro) -> Panel:
    """Build a responsive header panel that adapts cleanly to terminal width."""
    distro_badge = f"{distro.pretty_name}"
    if distro.is_debian_based:
        distro_badge += " (Debian-based)"

    if term_width >= 80:
        header_text = (
            f"[bold cyan]EasyCLI (ez) v{__version__}[/bold cyan] [dim]─ Friendly Linux Terminal Frontend[/dim]\n"
            f"[dim]Detected Distribution:[/dim] [bold green]{distro_badge}[/bold green] | [dim]Mode:[/dim] [bold yellow]Safe & Elevated[/bold yellow]"
        )
    elif term_width >= 55:
        header_text = (
            f"[bold cyan]EasyCLI (ez) v{__version__}[/bold cyan]\n"
            f"[dim]Distro:[/dim] [bold green]{distro_badge}[/bold green]\n"
            f"[dim]Mode:[/dim] [bold yellow]Safe & Elevated[/bold yellow]"
        )
    else:
        header_text = (
            f"[bold cyan]EasyCLI v{__version__}[/bold cyan]\n"
            f"[bold green]{distro.pretty_name}[/bold green]"
        )

    return Panel(header_text, box=box.ROUNDED, border_style="cyan", width=term_width)


def build_features_table(term_width: int) -> Table:
    """Build an adaptive features table styled cleanly for any terminal width."""
    table = Table(
        width=term_width,
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        header_style="bold cyan",
        title="[bold]Available Features[/bold]",
        show_lines=True,
        expand=True,
    )
    if term_width >= 105:
        table.add_column("#", justify="right", style="bold yellow", width=3, no_wrap=True)
        table.add_column("Icon", justify="center", width=4, no_wrap=True)
        table.add_column("Feature", style="bold white", ratio=3)
        table.add_column("Full Command", style="bold cyan", ratio=3, overflow="fold")
        table.add_column("Description", style="white", ratio=5)
        for idx, feat in enumerate(FEATURES, 1):
            table.add_row(
                str(idx),
                feat.icon,
                feat.title,
                f"ez {feat.subcommand}",
                feat.description,
            )
    elif term_width >= 75:
        table.add_column("#", justify="right", style="bold yellow", width=3, no_wrap=True)
        table.add_column("Feature", style="bold white", ratio=3)
        table.add_column("Full Command", style="bold cyan", ratio=3, overflow="fold")
        table.add_column("Description", style="white", ratio=4)
        for idx, feat in enumerate(FEATURES, 1):
            table.add_row(
                str(idx),
                f"{feat.icon} {feat.title}",
                f"ez {feat.subcommand}",
                feat.description,
            )
    elif term_width >= 52:
        table.add_column("#", justify="right", style="bold yellow", width=3, no_wrap=True)
        table.add_column("Feature", style="bold white", ratio=1)
        table.add_column("Full Command", style="bold cyan", ratio=1, overflow="fold")
        for idx, feat in enumerate(FEATURES, 1):
            table.add_row(
                str(idx),
                f"{feat.icon} {feat.title}",
                f"ez {feat.subcommand}",
            )
    else:
        table.add_column("#", justify="right", style="bold yellow", width=3, no_wrap=True)
        table.add_column("Command", style="bold cyan", ratio=1, overflow="fold")
        for idx, feat in enumerate(FEATURES, 1):
            table.add_row(
                str(idx),
                f"{feat.icon} ez {feat.subcommand}",
            )
    return table


def run_feature(console: Console, feature: FeatureTemplate) -> None:
    """Execute a feature in the interactive menu with refresh/back options."""
    args_values = []

    # Gather required or optional arguments interactively
    if feature.arguments:
        console.print()
        for arg in feature.arguments:
            prompt_label = f"Enter {arg.name} ({arg.help})"
            default_val = arg.default
            val = Prompt.ask(f"[bold cyan]{prompt_label}[/bold cyan]", default=default_val or "")
            if not val and arg.required:
                console.print(f"[bold red]Error:[/bold red] Argument '{arg.name}' is required.")
                return
            args_values.append(val)

    while True:
        console.clear()
        console.print(
            Panel(
                f"[bold cyan]{feature.icon} {feature.title}[/bold cyan] [dim](ez {feature.subcommand})[/dim]",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )

        # Dispatch feature
        renderer_fn = getattr(renderers, feature.renderer_name, None)
        try:
            if feature.id == "list":
                from .list_cli import run_cli_list
                run_cli_list(raw_args=args_values, console=console)
                return
            elif feature.id == "choose_directory":
                from .explorer.explorer_app import run_choose_directory
                run_choose_directory("~")
            elif feature.id == "copy":
                from .file_cli import run_cli_stage
                run_cli_stage("copy", console=console)
            elif feature.id == "move":
                from .file_cli import run_cli_stage
                run_cli_stage("move", console=console)
            elif feature.id == "paste":
                from .file_cli import run_cli_paste
                run_cli_paste(console=console)
            elif feature.id == "undo":
                from .file_cli import run_cli_undo
                run_cli_undo(console=console)
            elif feature.id == "redo":
                from .file_cli import run_cli_redo
                run_cli_redo(console=console)
            elif feature.id == "create_folder":
                from .create_cli import run_cli_create_folder
                raw_name = args_values[0] if args_values else ""
                if not raw_name or raw_name.lower() == "choose-directory":
                    run_cli_create_folder(name=None, choose_dest=True, console=console)
                else:
                    run_cli_create_folder(name=raw_name, choose_dest=False, console=console)
                return
            elif feature.id == "create_file":
                from .create_cli import run_cli_create_file
                raw_name = args_values[0] if args_values else ""
                if not raw_name or raw_name.lower() == "choose-directory":
                    run_cli_create_file(name=None, choose_dest=True, console=console)
                else:
                    run_cli_create_file(name=raw_name, choose_dest=False, console=console)
                return
            elif feature.id == "delete":
                from .delete_cli import run_cli_delete
                target = args_values[0] if args_values else "choose-directory"
                if not target or target.strip().lower() == "choose-directory":
                    run_cli_delete(args=["choose-directory"], console=console)
                else:
                    run_cli_delete(args=[target.strip()], console=console)
                return
            elif feature.id == "edit_file":
                from .edit_cli import run_cli_edit_file
                edit_target = args_values[0].strip() if args_values and args_values[0] else "choose-directory"

                class MenuEditArgs:
                    target = ""

                menu_args = MenuEditArgs()
                menu_args.target = edit_target
                run_cli_edit_file(args=menu_args, console=console)
                return
            elif feature.id == "update":
                from .upgrade_cli import run_cli_update
                run_cli_update(console=console)
                return
            elif feature.id == "upgrade":
                from .upgrade_cli import run_cli_upgrade
                run_cli_upgrade(console=console)
                return
            elif feature.id == "uninstall":
                from .uninstall_cli import run_cli_uninstall
                target_app = args_values[0] if args_values else None
                run_cli_uninstall(app_name=target_app, console=console)
                return
            elif feature.id == "task_manager":
                from .task_manager import run_task_manager
                run_task_manager(mode="normal")
                return
            elif feature.id == "task_manager_pro":
                from .task_manager import run_task_manager
                run_task_manager(mode="pro")
                return
            elif feature.id == "time_machine":
                from .time_machine.time_machine_cli import run_cli_time_machine
                run_cli_time_machine(raw_args=args_values, console=console)
                return
            elif feature.id == "check_internet":

                from .internet_checker import render_internet_check
                render_internet_check(console=console)
            elif feature.id == "connect_wifi":
                from .main import check_textual_installed
                if not check_textual_installed(console):
                    return
                from .wifi import run_wifi_app
                run_wifi_app()
                return
            elif feature.id == "search_file":
                from .search_file import run_search_file_cli
                term_val = args_values[0] if args_values else None
                run_search_file_cli(term=term_val, console=console)
                return
            elif feature.id == "compress":
                from .compress_cli import run_cli_compress
                run_cli_compress(targets=args_values, console=console)
                return
            elif feature.id == "extract":
                from .extract_cli import run_cli_extract
                choose_dest = any(a.lower() == "choose-directory" for a in args_values)
                run_cli_extract(raw_args=args_values, choose_dest=choose_dest, console=console)
                return
            elif feature.id == "run":
                from .run_cli import run_cli_run
                run_cli_run(raw_args=args_values, console=console)
                return
            elif feature.id == "cleanup":
                from .cleanup import run_cleanup_cli
                run_cleanup_cli(console=console)
                return
            elif feature.id == "profile":
                from .profile_cli import run_profile_cli
                run_profile_cli(console=console)
                return
            elif feature.id == "fix_packages":
                from .fix_packages_cli import run_fix_packages_cli
                run_fix_packages_cli(console=console)
                return
            elif feature.id == "startup_apps":
                from .startup_apps import run_startup_apps_cli
                target_val = args_values[0] if (args_values and args_values[0]) else None
                run_startup_apps_cli(target=target_val, console=console)
                return
            elif renderer_fn is not None:
                if feature.subcommand == "big_files" or feature.id == "big_files":
                    raw_folder = args_values[0] if args_values else "~"
                    if raw_folder.lower() == "choose-directory":
                        from .explorer.explorer_app import ExplorerApp
                        app = ExplorerApp(mode="pick_dest", initial_dir="~")
                        chosen_dir = app.run()
                        if not chosen_dir or not isinstance(chosen_dir, str):
                            console.print("[dim]Directory selection cancelled.[/dim]")
                            return
                        folder = chosen_dir
                    else:
                        folder = raw_folder
                    renderer_fn(console, folder)
                elif feature.subcommand == "package-info" or feature.id == "package_info":
                    pkg_name = args_values[0] if (args_values and args_values[0]) else None
                    renderer_fn(console, pkg_name)
                elif feature.subcommand == "service_status" or feature.id == "service_status":
                    svc_name = args_values[0] if args_values else ""
                    renderer_fn(console, svc_name)
                elif feature.subcommand == "logs" or feature.id == "logs":
                    lines = int(args_values[0]) if (args_values and args_values[0].isdigit()) else 50
                    renderer_fn(console, lines)
                elif feature.subcommand in ("list-installed-packages", "installed-packages") or feature.id in ("list_installed_packages", "installed_packages"):
                    renderer_fn(console)
                elif feature.subcommand == "installed-package-search" or feature.id == "installed_package_search":
                    term = args_values[0] if args_values else ""
                    renderer_fn(console, term)
                elif feature.subcommand == "stats" or feature.id == "stats":
                    try:
                        from .main import check_textual_installed
                        if check_textual_installed(console):
                            from .stats import run_live_stats
                            run_live_stats()
                        else:
                            renderer_fn(console)
                    except Exception:
                        renderer_fn(console)
                else:
                    renderer_fn(console)
            else:
                console.print(f"[bold red]No renderer found for {feature.renderer_name}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Unexpected error executing feature:[/bold red] {e}")

        console.print()
        console.print(Rule(style="dim"))
        try:
            global _in_menu_prompt
            _in_menu_prompt = True
            action = Prompt.ask(
                "[bold cyan]Actions[/bold cyan]: [bold][b][/bold] Back to Menu | [bold][r][/bold] Refresh | [bold][q][/bold] Quit",
                choices=["b", "r", "q", ""],
                default="b",
                show_choices=False,
                console=console,
            )
        except TerminalResizeInterrupt:
            continue
        finally:
            _in_menu_prompt = False

        if action.lower() == "r":
            continue
        elif action.lower() == "q":
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)
        else:
            # Back to menu
            break


def interactive_menu(console: Console) -> None:
    """Main interactive menu loop with adaptive layout and dynamic resize handling."""
    distro = detect_distro()

    old_handler = None
    sigwinch_available = hasattr(signal, "SIGWINCH") and sys.stdin.isatty()
    if sigwinch_available:
        try:
            old_handler = signal.signal(signal.SIGWINCH, _sigwinch_handler)
        except (ValueError, OSError):
            sigwinch_available = False

    try:
        while True:
            # Dynamically fetch current terminal dimensions
            term_width = console.size.width or 80
            console.clear()

            # Responsive header panel
            console.print(build_header_panel(term_width, distro))

            # Responsive features table
            table = build_features_table(term_width)
            console.print(table)
            console.print()

            global _in_menu_prompt
            try:
                _in_menu_prompt = True
                choice = Prompt.ask(
                    f"[bold cyan]Select a feature [1-{len(FEATURES)}][/bold cyan] (or [bold]r[/bold]efresh, [bold]q[/bold]uit)",
                    default="1",
                    console=console,
                ).strip().lower()
            except TerminalResizeInterrupt:
                # Terminal was resized while waiting for prompt input.
                # Redraw immediately with new dimensions.
                continue
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Good bye![/dim]")
                sys.exit(0)
            finally:
                _in_menu_prompt = False

            if choice == "q":
                console.print("\n[dim]Good bye![/dim]")
                sys.exit(0)
            elif choice == "r":
                continue
            elif choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(FEATURES):
                    run_feature(console, FEATURES[idx - 1])
                else:
                    console.print(f"[bold red]Please enter a number between 1 and {len(FEATURES)}[/bold red]")
                    try:
                        _in_menu_prompt = True
                        Prompt.ask("[dim]Press Enter to continue...[/dim]", default="", console=console)
                    except TerminalResizeInterrupt:
                        continue
                    finally:
                        _in_menu_prompt = False
            else:
                # Check if subcommand was typed directly
                matched = next((f for f in FEATURES if f.subcommand == choice), None)
                if matched:
                    run_feature(console, matched)
                else:
                    console.print(f"[bold red]Invalid option. Please choose 1-{len(FEATURES)}, r, or q.[/bold red]")
                    try:
                        _in_menu_prompt = True
                        Prompt.ask("[dim]Press Enter to continue...[/dim]", default="", console=console)
                    except TerminalResizeInterrupt:
                        continue
                    finally:
                        _in_menu_prompt = False
    finally:
        if sigwinch_available and old_handler is not None:
            try:
                signal.signal(signal.SIGWINCH, old_handler)
            except (ValueError, OSError):
                pass
