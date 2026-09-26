"""CLI orchestrator for the Permissions & Ownership command."""

import os
import sys
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel

from .permissions_engine import get_file_permissions


def run_permissions_cli(targets: Optional[List[str]] = None, console: Optional[Console] = None) -> None:
    """Entry point for `ez permissions`."""
    if console is None:
        console = Console()

    target_raw = targets[0] if targets else ""

    # Dual-mode: visual picker if requested or no target provided in interactive session
    if not target_raw or target_raw.lower() == "choose-directory":
        if sys.stdout.isatty():
            from ..main import check_textual_installed

            if check_textual_installed(console):
                from ..explorer.explorer_app import ExplorerApp

                app = ExplorerApp(mode="pick_dest", initial_dir=".")
                chosen = app.run()
                if not chosen or not isinstance(chosen, str):
                    console.print("[dim]Permission editor cancelled.[/dim]")
                    return
                target_raw = chosen
            else:
                target_raw = "."
        else:
            target_raw = "."

    resolved_path = os.path.abspath(os.path.expanduser(target_raw))
    if not os.path.exists(resolved_path):
        console.print(
            Panel(
                f"File or directory [bold red]'{target_raw}'[/bold red] does not exist.\n\n"
                "Please specify a valid file or folder in your current directory,\n"
                "or run [bold cyan]ez permissions choose-directory[/bold cyan] to select visually.",
                title="[bold red]Target Not Found[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        return

    # Interactive TUI mode
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .permissions_tui import PermissionsApp

            app = PermissionsApp(target_path=resolved_path)
            app.run()
            return

    # Fallback Rich console display
    perms = get_file_permissions(resolved_path)
    file_type = "Directory" if perms.is_dir else "File"
    console.print(
        Panel(
            f"Target: [bold cyan]{perms.path}[/bold cyan] ({file_type})\n"
            f"Octal Mode: [bold green]{perms.octal}[/bold green]  |  Symbolic: [bold]{perms.symbolic}[/bold]\n"
            f"Ownership: [bold]{perms.owner_name}:{perms.group_name}[/bold]\n\n"
            f"Owner:   Read={'✓' if perms.owner_r else '✗'}, Write={'✓' if perms.owner_w else '✗'}, Exec={'✓' if perms.owner_x else '✗'}\n"
            f"Group:   Read={'✓' if perms.group_r else '✗'}, Write={'✓' if perms.group_w else '✗'}, Exec={'✓' if perms.group_x else '✗'}\n"
            f"Others:  Read={'✓' if perms.other_r else '✗'}, Write={'✓' if perms.other_w else '✗'}, Exec={'✓' if perms.other_x else '✗'}",
            title="🔐 [bold cyan]EasyCLI File Permissions[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
