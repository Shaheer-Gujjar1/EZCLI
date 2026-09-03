"""Main entry point and CLI dispatcher for EasyCLI (ezcli)."""

import argparse
import sys
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import FEATURES, FEATURES_BY_SUBCOMMAND
from .distro import detect_distro
from .emoji import ensure_emoji_capability
from .menu import interactive_menu
from . import renderers


def print_custom_help(console: Console) -> None:
    """Print formatted help listing all subcommands, icons, and descriptions."""
    distro = detect_distro()
    header_text = (
        f"[bold cyan]EasyCLI (ezcli) v{__version__}[/bold cyan] ─ Friendly Linux Command Frontend\n"
        f"[dim]Platform:[/dim] [green]{distro.pretty_name}[/green] | [dim]Mode:[/dim] [bold yellow]100% Read-Only[/bold yellow]"
    )
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))

    console.print("[bold]Usage:[/bold]")
    console.print("  [cyan]ezcli[/cyan]                      [dim]Open interactive TUI menu[/dim]")
    console.print("  [cyan]ezcli <subcommand> [args][/cyan]  [dim]Run subcommand directly and print output[/dim]")
    console.print("  [cyan]ezcli help[/cyan]                 [dim]Show this help message[/dim]\n")

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        title="[bold]Available Subcommands[/bold]",
        padding=(0, 1),
    )
    table.add_column("Icon", justify="center", width=4)
    table.add_column("Subcommand & Syntax", style="bold green", width=28)
    table.add_column("Wrapped Tools", style="dim", width=26)
    table.add_column("Description", style="white")

    for f in FEATURES:
        # Format syntax
        syntax = f.subcommand
        for arg in f.arguments:
            if arg.required:
                syntax += f" <{arg.name}>"
            else:
                syntax += f" [{arg.name}]"

        wrapped_str = ", ".join(f.wrapped_commands)
        table.add_row(
            f.icon,
            syntax,
            wrapped_str,
            f.description,
        )

    console.print(table)
    console.print()


def main() -> None:
    """Main CLI execution routine."""
    # Ensure stdout & terminal can render emoji and check emoji font capability
    ensure_emoji_capability()

    console = Console()
    args = sys.argv[1:]

    # 1. No arguments -> Interactive TUI Menu
    if not args:
        try:
            interactive_menu(console)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting EasyCLI.[/dim]")
            sys.exit(0)
        return

    first_arg = args[0].strip().lower()

    # 2. Help flags or subcommand 'help'
    if first_arg in ("help", "--help", "-h"):
        print_custom_help(console)
        sys.exit(0)

    # 3. Version flag
    if first_arg in ("--version", "-v", "version"):
        console.print(f"EasyCLI (ezcli) v{__version__} [dim](Read-Only)[/dim]")
        sys.exit(0)

    # 4. Check if subcommand matches a registered feature
    if first_arg not in FEATURES_BY_SUBCOMMAND:
        console.print(f"[bold red]Unknown subcommand:[/bold red] '{first_arg}'\n")
        console.print("Run [cyan]ezcli help[/cyan] to view available subcommands, or launch [cyan]ezcli[/cyan] for the menu.")
        sys.exit(1)

    feature = FEATURES_BY_SUBCOMMAND[first_arg]
    sub_args = args[1:]

    # Validate required arguments
    required_args = [a for a in feature.arguments if a.required]
    if len(sub_args) < len(required_args):
        missing = [a.name for a in required_args[len(sub_args):]]
        console.print(
            f"[bold red]Error:[/bold red] Subcommand '[cyan]{feature.subcommand}[/cyan]' requires argument(s): "
            + ", ".join(f"<{m}>" for m in missing)
        )
        sys.exit(1)

    # Dispatch to appropriate renderer
    try:
        if feature.id == "system_info":
            renderers.render_system_info(console)
        elif feature.id == "stats":
            renderers.render_stats(console)
        elif feature.id == "disk_info":
            renderers.render_disk_info(console)
        elif feature.id == "big_files":
            folder = sub_args[0] if sub_args else "~"
            renderers.render_big_files(console, folder)
        elif feature.id == "package_search":
            term = " ".join(sub_args)
            renderers.render_package_search(console, term)
        elif feature.id == "package":
            pkg_name = sub_args[0]
            renderers.render_package(console, pkg_name)
        elif feature.id == "available_updates":
            renderers.render_available_updates(console)
        elif feature.id == "service_status":
            svc_name = sub_args[0]
            renderers.render_service_status(console, svc_name)
        elif feature.id == "network_info":
            renderers.render_network_info(console)
        elif feature.id == "logs":
            lines = 50
            if sub_args:
                try:
                    lines = int(sub_args[0])
                except ValueError:
                    console.print(f"[bold red]Error:[/bold red] Invalid line count '{sub_args[0]}'. Must be an integer.")
                    sys.exit(1)
            renderers.render_logs(console, lines)
    except KeyboardInterrupt:
        console.print("\n[dim]Command interrupted.[/dim]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]Error executing {feature.subcommand}:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
