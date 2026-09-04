"""Interactive terminal menu for EasyCLI."""

import sys
from typing import Optional
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .config import FEATURES, FeatureTemplate
from .distro import detect_distro
from . import renderers


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
                f"[bold cyan]{feature.icon} {feature.title}[/bold cyan] [dim](ezcli {feature.subcommand})[/dim]",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )

        # Dispatch feature
        renderer_fn = getattr(renderers, feature.renderer_name, None)
        try:
            if feature.id == "choose_directory":
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
                if not raw_name or raw_name.lower() in ("choose-directory", "choose", "picker", "select", "c"):
                    run_cli_create_folder(name=None, choose_dest=True, console=console)
                else:
                    run_cli_create_folder(name=raw_name, choose_dest=False, console=console)
                return
            elif feature.id == "create_file":
                from .create_cli import run_cli_create_file
                raw_name = args_values[0] if args_values else ""
                if not raw_name or raw_name.lower() in ("choose-directory", "choose", "picker", "select", "c"):
                    run_cli_create_file(name=None, choose_dest=True, console=console)
                else:
                    run_cli_create_file(name=raw_name, choose_dest=False, console=console)
                return
            elif feature.id == "delete":
                from .delete_cli import run_cli_delete
                target = args_values[0] if args_values else "choose-directory"
                if not target or target.strip().lower() in ("choose-directory", "choose", "picker", "c"):
                    run_cli_delete(args=["choose-directory"], console=console)
                else:
                    run_cli_delete(args=[target.strip()], console=console)
                return
            elif renderer_fn is not None:
                if feature.subcommand == "big_files" or feature.id == "big_files":
                    raw_folder = args_values[0] if args_values else "~"
                    if raw_folder.lower() in ("choose-directory", "choose", "picker", "select", "c"):
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
                elif feature.subcommand == "package_search" or feature.id == "package_search":
                    term = args_values[0] if args_values else ""
                    renderer_fn(console, term)
                elif feature.subcommand == "package" or feature.id == "package":
                    pkg_name = args_values[0] if args_values else ""
                    renderer_fn(console, pkg_name)
                elif feature.subcommand == "service_status" or feature.id == "service_status":
                    svc_name = args_values[0] if args_values else ""
                    renderer_fn(console, svc_name)
                elif feature.subcommand == "logs" or feature.id == "logs":
                    lines = int(args_values[0]) if (args_values and args_values[0].isdigit()) else 50
                    renderer_fn(console, lines)
                elif feature.subcommand in ("installed", "installed-packages") or feature.id == "installed_packages":
                    renderer_fn(console)
                elif feature.subcommand == "installed-package-search" or feature.id == "installed_package_search":
                    term = args_values[0] if args_values else ""
                    renderer_fn(console, term)
                else:
                    renderer_fn(console)
            else:
                console.print(f"[bold red]No renderer found for {feature.renderer_name}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]Unexpected error executing feature:[/bold red] {e}")

        console.print()
        console.print("[dim]─[/dim]" * 60)
        action = Prompt.ask(
            "[bold cyan]Actions[/bold cyan]: [bold][b][/bold] Back to Menu | [bold][r][/bold] Refresh | [bold][q][/bold] Quit",
            choices=["b", "r", "q", ""],
            default="b",
            show_choices=False,
        )

        if action.lower() == "r":
            continue
        elif action.lower() == "q":
            console.print("\n[dim]Goodbye![/dim]")
            sys.exit(0)
        else:
            # Back to menu
            break


def interactive_menu(console: Console) -> None:
    """Main interactive menu loop."""
    distro = detect_distro()

    while True:
        console.clear()

        # Header
        distro_badge = f"{distro.pretty_name}"
        if distro.is_debian_based:
            distro_badge += " (Debian-based)"
        header_text = (
            f"[bold cyan]EasyCLI (ezcli) v0.1[/bold cyan] [dim]─ Read-Only Terminal Frontend[/dim]\n"
            f"[dim]Detected Distribution:[/dim] [bold green]{distro_badge}[/bold green] | [dim]Mode:[/dim] [bold yellow]100% Read-Only[/bold yellow]"
        )
        console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))

        # Features Table
        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            header_style="bold cyan",
            title="[bold]Available Features[/bold]",
        )
        table.add_column("#", justify="right", style="bold yellow", width=3)
        table.add_column("Icon", justify="center", width=4)
        table.add_column("Feature", style="bold white", width=24)
        table.add_column("Subcommand", style="dim cyan", width=19)
        table.add_column("Description", style="white")

        for idx, feat in enumerate(FEATURES, 1):
            table.add_row(
                str(idx),
                feat.icon,
                feat.title,
                feat.subcommand,
                feat.description,
            )

        console.print(table)
        console.print()

        try:
            choice = Prompt.ask(
                f"[bold cyan]Select a feature [1-{len(FEATURES)}][/bold cyan] (or [bold]r[/bold]efresh, [bold]q[/bold]uit)",
                default="1",
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting EasyCLI.[/dim]")
            sys.exit(0)

        if choice == "q":
            console.print("\n[dim]Exiting EasyCLI.[/dim]")
            sys.exit(0)
        elif choice == "r":
            continue
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(FEATURES):
                run_feature(console, FEATURES[idx - 1])
            else:
                console.print(f"[bold red]Please enter a number between 1 and {len(FEATURES)}[/bold red]")
                Prompt.ask("[dim]Press Enter to continue...[/dim]", default="")
        else:
            # Check if subcommand was typed directly
            matched = next((f for f in FEATURES if f.subcommand == choice), None)
            if matched:
                run_feature(console, matched)
            else:
                console.print("[bold red]Invalid option. Please choose 1-10, r, or q.[/bold red]")
                Prompt.ask("[dim]Press Enter to continue...[/dim]", default="")
