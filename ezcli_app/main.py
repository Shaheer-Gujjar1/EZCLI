import importlib
import os
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


def check_textual_installed(console: Console) -> bool:
    """Check if modern textual (>=0.2.0) is installed, showing a friendly setup panel if missing or outdated."""
    try:
        importlib.import_module("textual.containers")
        importlib.import_module("textual.widgets")
        return True
    except (ImportError, AttributeError):
        pass

    console.print(
        Panel(
            "📁 [bold cyan]EasyCLI Terminal File Explorer[/bold cyan]\n\n"
            "[bold yellow]Modern Textual (v0.2.0+) is required[/bold yellow] to run the interactive file explorer.\n\n"
            "Your system currently has an ancient release (such as 0.1.18 from [dim]sudo apt install python3-textual[/dim]).\n\n"
            "To fix this, upgrade to modern Textual on your system by running:\n"
            "   [bold green]sudo apt remove -y python3-textual && pip3 install textual[/bold green]\n"
            "or (if using pip with PEP 668):\n"
            "   [bold green]pip3 install --upgrade --break-system-packages textual[/bold green]\n"
            "or re-run the automated installer:\n"
            "   [bold green]./install.sh[/bold green]",
            title="[bold yellow]Textual Upgrade Required[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )
    return False


def print_custom_help(console: Console) -> None:
    """Print formatted help listing all subcommands, icons, and descriptions."""
    distro = detect_distro()
    header_text = (
        f"[bold cyan]EasyCLI (ezcli) v{__version__}[/bold cyan] ─ Friendly Linux Command Frontend\n"
        f"[dim]Platform:[/dim] [green]{distro.pretty_name}[/green] | [dim]Admin Mode:[/dim] [bold yellow]Automatic & Safe[/bold yellow]"
    )
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))

    console.print("[bold]Usage:[/bold]")
    console.print("  [cyan]ezcli[/cyan]                      [dim]Open interactive TUI menu[/dim]")
    console.print("  [cyan]ezcli <subcommand> [args][/cyan]  [dim]Run subcommand directly and print output[/dim]")
    console.print("  [cyan]ezcli help[/cyan]                 [dim]Show this help message[/dim]\n")

    console.print("[bold]Options:[/bold]")
    console.print("  [green]-h, --help[/green]                 [dim]Show this help message[/dim]")
    console.print("  [green]-v, --version[/green]              [dim]Show EasyCLI version[/dim]\n")

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
    console.print("[dim]💡 Tip: Never run 'sudo ezcli'. EasyCLI always runs safely as your normal user\n   and elevates only the specific underlying action through a small privileged helper.[/dim]\n")


def main() -> None:
    """Main CLI execution routine."""
    # Ensure stdout & terminal can render emoji and check emoji font capability
    ensure_emoji_capability()

    console = Console()
    args = sys.argv[1:]

    # Check if user invoked 'sudo ezcli' directly
    if os.geteuid() == 0 and "SUDO_USER" in os.environ:
        console.print(
            "[bold yellow]Notice:[/bold yellow] You started EasyCLI with 'sudo ezcli'.\n"
            "Running the entire app as root is not needed or recommended.\n"
            "EasyCLI automatically and safely elevates only specific tasks when required.\n"
        )

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
        console.print(f"EasyCLI (ezcli) v{__version__} [dim](Safe Automatic Elevation)[/dim]")
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
            raw_folder = sub_args[0] if sub_args else "~"
            if raw_folder.lower() in ("choose-directory", "choose", "picker", "select"):
                if not check_textual_installed(console):
                    sys.exit(1)
                from .explorer.explorer_app import ExplorerApp
                app = ExplorerApp(mode="pick_dest", initial_dir="~")
                chosen_dir = app.run()
                if not chosen_dir or not isinstance(chosen_dir, str):
                    console.print("[dim]Directory selection cancelled.[/dim]")
                    return
                folder = chosen_dir
            else:
                folder = raw_folder
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
        elif feature.id == "installed_packages":
            renderers.render_installed_packages(console)
        elif feature.id == "installed_package_search":
            term = " ".join(sub_args)
            renderers.render_installed_package_search(console, term)
        elif feature.id == "choose_directory":
            if not check_textual_installed(console):
                sys.exit(1)
            from .explorer.explorer_app import run_choose_directory
            print_only = False
            clean_sub = []
            for a in sub_args:
                if a in ("-p", "--print-path"):
                    print_only = True
                else:
                    clean_sub.append(a)
            initial_dir = clean_sub[0] if clean_sub else "~"
            run_choose_directory(initial_dir, print_path_only=print_only)
        elif feature.id == "copy":
            if not check_textual_installed(console):
                sys.exit(1)
            from .file_cli import run_cli_stage
            run_cli_stage("copy", console=console)
        elif feature.id == "move":
            if not check_textual_installed(console):
                sys.exit(1)
            from .file_cli import run_cli_stage
            run_cli_stage("move", console=console)
        elif feature.id == "paste":
            if not check_textual_installed(console):
                sys.exit(1)
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
            choose_dest = any(a.lower() in ("choose-directory", "choose", "picker", "select") for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() not in ("choose-directory", "choose", "picker", "select")]
            folder_name = clean_sub[0] if clean_sub else None
            run_cli_create_folder(folder_name=folder_name, choose_dest=choose_dest, console=console)
        elif feature.id == "create_file":
            from .create_cli import run_cli_create_file
            choose_dest = any(a.lower() in ("choose-directory", "choose", "picker", "select") for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() not in ("choose-directory", "choose", "picker", "select")]
            file_name = clean_sub[0] if clean_sub else None
            run_cli_create_file(file_name=file_name, choose_dest=choose_dest, console=console)
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except Exception:
            pass
        sys.exit(0)
    except PermissionError as e:
        console.print(
            Panel(
                "🔒 [bold red]Admin rights are required for this task.[/bold red]\n\n"
                f"Permission denied: {e}",
                title="[bold yellow]Admin Rights Required[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Command interrupted.[/dim]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]Error executing {feature.subcommand}:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
