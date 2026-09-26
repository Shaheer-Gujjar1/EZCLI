"""CLI orchestrator for the Command Shortcuts feature."""

import os
import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .shortcuts_engine import get_shell_rc_path, parse_shortcuts


def run_shortcuts_cli(console: Optional[Console] = None) -> None:
    """Entry point for `ez shortcuts`."""
    if console is None:
        console = Console()

    # Interactive TUI mode
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .shortcuts_tui import ShortcutsApp

            app = ShortcutsApp()
            app.run()
            return

    # Fallback Rich console display
    rc_path = get_shell_rc_path()
    shortcuts = parse_shortcuts(rc_path)
    short_name = os.path.basename(rc_path)

    console.print(
        Panel(
            f"Config File: [bold cyan]~/{short_name}[/bold cyan]  |  "
            f"Active Shortcuts: [bold yellow]{len(shortcuts)}[/bold yellow]\n"
            "[dim]Run in an interactive terminal to add, edit, or delete shortcuts visually.[/dim]",
            title="⚡ [bold cyan]EasyCLI Command Shortcuts[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if shortcuts:
        table = Table(
            title="Configured Shortcuts",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("Shortcut Name", width=22)
        table.add_column("Runs Terminal Command", width=42)
        table.add_column("Source", width=22)

        for s in shortcuts:
            table.add_row(
                f"[bold green]{s.name}[/bold green]",
                f"[cyan]{s.command}[/cyan]",
                s.source,
            )
        console.print(table)
    else:
        console.print("[dim]No custom command shortcuts configured.[/dim]")
