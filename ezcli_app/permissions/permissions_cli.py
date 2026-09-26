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
    from .permissions_engine import explain_permissions, get_preset_name

    perms = get_file_permissions(resolved_path)
    file_type = "📁 Directory" if perms.is_dir else "📄 File"
    preset_name = get_preset_name(perms.octal, perms.is_dir)
    owner_exp, group_exp, others_exp = explain_permissions(
        perms.is_dir,
        perms.owner_r, perms.owner_w, perms.owner_x,
        perms.group_r, perms.group_w, perms.group_x,
        perms.other_r, perms.other_w, perms.other_x,
        group_name=perms.group_name,
    )

    console.print(
        Panel(
            f"Target: [bold cyan]{perms.path}[/bold cyan] ({file_type})\n"
            f"Configuration: [bold yellow]{preset_name}[/bold yellow]  |  "
            f"Octal: [bold green]{perms.octal}[/bold green]  |  "
            f"Symbolic: [bold]{perms.symbolic}[/bold]\n"
            f"Ownership: [bold]{perms.owner_name}:{perms.group_name}[/bold]\n\n"
            f"• [bold green]👤 You (Owner):[/bold green] {owner_exp}\n"
            f"• [bold cyan]👥 Group ({perms.group_name}):[/bold cyan] {group_exp}\n"
            f"• [bold magenta]🌐 Everyone Else:[/bold magenta] {others_exp}",
            title="🔐 [bold cyan]EasyCLI File Permissions[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
