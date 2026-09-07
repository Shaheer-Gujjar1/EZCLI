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
    import glob
    venv_site = (
        glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
        + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
    )
    if venv_site and venv_site[0] not in sys.path:
        sys.path.insert(0, venv_site[0])

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
        f"[bold cyan]EasyCLI (ez) v{__version__}[/bold cyan] ─ Friendly Linux Command Frontend\n"
        f"[dim]Platform:[/dim] [green]{distro.pretty_name}[/green] | [dim]Admin Mode:[/dim] [bold yellow]Automatic & Safe[/bold yellow]"
    )
    console.print(Panel(header_text, box=box.ROUNDED, border_style="cyan"))

    console.print("[bold]Usage (Flagless Command-Only Frontend):[/bold]")
    console.print("  [cyan]ez[/cyan]                         [dim]Open interactive TUI menu[/dim]")
    console.print("  [cyan]ez <subcommand> [args][/cyan]     [dim]Run subcommand directly and print output[/dim]")
    console.print("  [cyan]ez help[/cyan]                    [dim]Show this help message[/dim]")
    console.print("  [cyan]ez version[/cyan]                 [dim]Show EasyCLI version[/dim]\n")

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
    console.print("[dim]💡 Tip: Never run 'sudo ez'. EasyCLI always runs safely as your normal user\n   and elevates only the specific underlying action through a small privileged helper.[/dim]\n")


def main() -> None:
    """Main CLI execution routine."""
    # Ensure stdout & terminal can render emoji and check emoji font capability
    ensure_emoji_capability()

    console = Console()
    args = sys.argv[1:]

    # Check if user invoked 'sudo ez' directly
    if os.geteuid() == 0 and "SUDO_USER" in os.environ:
        console.print(
            "[bold yellow]Notice:[/bold yellow] You started EasyCLI with 'sudo ez'.\n"
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

    # 2. EasyCLI is strictly flagless — reject any flags starting with '-'
    for a in args:
        if a.startswith("-"):
            console.print(
                f"[bold red]Error:[/bold red] EasyCLI is completely flagless — flags like '[cyan]{a}[/cyan]' are not supported."
            )
            if a in ("-h", "--help"):
                console.print("Use the [bold green]ez help[/bold green] command to view all available commands.")
            elif a in ("-v", "--version"):
                console.print("Use the [bold green]ez version[/bold green] command to check the application version.")
            else:
                console.print("Run [bold green]ez help[/bold green] to view all available commands.")
            sys.exit(1)

    first_arg = args[0].strip().lower()

    # 3. Subcommand 'help'
    if first_arg == "help":
        print_custom_help(console)
        sys.exit(0)

    # 4. Subcommand 'version'
    if first_arg == "version":
        sub_args = args[1:]
        if not sub_args:
            console.print(f"EasyCLI (ez) v{__version__} [dim](Safe Automatic Elevation)[/dim]")
            console.print("[dim]💡 Tip: Check the version of any app, package, or library with '[bold cyan]ez version <name>[/bold cyan]'[/dim]")
            sys.exit(0)
        else:
            from .version_checker import run_version_command
            run_version_command(name=sub_args[0], console=console)
            sys.exit(0)

    # 4. Check if subcommand matches a registered feature
    if first_arg not in FEATURES_BY_SUBCOMMAND:
        console.print(f"[bold red]Unknown subcommand:[/bold red] '{first_arg}'\n")
        console.print("Run [cyan]ez help[/cyan] to view available subcommands, or launch [cyan]ez[/cyan] for the menu.")
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
            if not sys.stdout.isatty():
                renderers.render_stats(console)
            else:
                if not check_textual_installed(console):
                    renderers.render_stats(console)
                else:
                    from .stats import run_live_stats
                    run_live_stats()
        elif feature.id == "task_manager":
            if not check_textual_installed(console):
                sys.exit(1)
            from .task_manager import run_task_manager
            run_task_manager(mode="normal")
        elif feature.id == "task_manager_pro":
            if not check_textual_installed(console):
                sys.exit(1)
            from .task_manager import run_task_manager
            run_task_manager(mode="pro")
        elif feature.id == "disk_info":
            renderers.render_disk_info(console)
        elif feature.id == "big_files":
            raw_folder = sub_args[0] if sub_args else "~"
            if raw_folder.lower() == "choose-directory":
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
        elif feature.id == "update":
            from .upgrade_cli import run_cli_update
            run_cli_update(console=console)
        elif feature.id == "upgrade":
            from .upgrade_cli import run_cli_upgrade
            run_cli_upgrade(console=console)
        elif feature.id == "uninstall":
            from .uninstall_cli import run_cli_uninstall
            target_app = sub_args[0] if sub_args else None
            run_cli_uninstall(app_name=target_app, console=console)
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
            initial_dir = sub_args[0] if sub_args else "~"
            run_choose_directory(initial_dir)
        elif feature.id == "copy":
            from .file_cli import run_cli_stage
            choose_dir = any(a.lower() == "choose-directory" for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() != "choose-directory"]
            if choose_dir or not sub_args:
                if not check_textual_installed(console):
                    sys.exit(1)
                run_cli_stage("copy", targets=None, console=console)
            else:
                run_cli_stage("copy", targets=clean_sub, console=console)
        elif feature.id == "move":
            from .file_cli import run_cli_stage
            choose_dir = any(a.lower() == "choose-directory" for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() != "choose-directory"]
            if choose_dir or not sub_args:
                if not check_textual_installed(console):
                    sys.exit(1)
                run_cli_stage("move", targets=None, console=console)
            else:
                run_cli_stage("move", targets=clean_sub, console=console)
        elif feature.id == "paste":
            from .file_cli import run_cli_paste
            choose_dir = any(a.lower() == "choose-directory" for a in sub_args)
            if choose_dir:
                if not check_textual_installed(console):
                    sys.exit(1)
                run_cli_paste(choose_dest=True, console=console)
            else:
                run_cli_paste(choose_dest=False, console=console)
        elif feature.id == "undo":
            from .file_cli import run_cli_undo
            run_cli_undo(console=console)
        elif feature.id == "redo":
            from .file_cli import run_cli_redo
            run_cli_redo(console=console)
        elif feature.id == "create_folder":
            from .create_cli import run_cli_create_folder
            choose_dest = any(a.lower() == "choose-directory" for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() != "choose-directory"]
            run_cli_create_folder(raw_args=clean_sub, choose_dest=choose_dest, console=console)
        elif feature.id == "create_file":
            from .create_cli import run_cli_create_file
            choose_dest = any(a.lower() == "choose-directory" for a in sub_args)
            clean_sub = [a for a in sub_args if a.lower() != "choose-directory"]
            run_cli_create_file(raw_args=clean_sub, choose_dest=choose_dest, console=console)
        elif feature.id == "delete":
            from .delete_cli import run_cli_delete
            run_cli_delete(args=sub_args, console=console)
        elif feature.id == "edit_file":
            if not check_textual_installed(console):
                sys.exit(1)
            from .edit_cli import run_cli_edit_file
            target_arg = sub_args[0] if sub_args else ""

            class EditArgs:
                target = target_arg

            run_cli_edit_file(args=EditArgs(), console=console)
        elif feature.id == "version":
            from .version_checker import run_version_command
            target_arg = sub_args[0] if sub_args else None
            run_version_command(name=target_arg, console=console)
        elif feature.id == "check_internet":
            renderers.render_internet_check(console)
        elif feature.id == "connect_wifi":
            if not check_textual_installed(console):
                sys.exit(1)
            from .wifi import run_wifi_app
            run_wifi_app()
        elif feature.id == "search_file":
            from .search_file import run_search_file_cli
            search_term = " ".join(sub_args).strip() if sub_args else None
            run_search_file_cli(term=search_term, console=console)
        elif feature.id == "compress":
            from .compress_cli import run_cli_compress
            run_cli_compress(targets=sub_args, console=console)
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
