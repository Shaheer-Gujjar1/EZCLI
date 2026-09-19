"""
CLI entrypoint and dispatch for 'ez time-machine'.

Supports:
- 'ez time-machine': Launches full interactive Textual Time Machine TUI.
- 'ez time-machine list': Direct pretty snapshot listing in terminal.
- 'ez time-machine create [comment]': Quick command-line snapshot creation with spinner.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .snapshot_engine import (
    format_human_size,
    get_base_dir,
    get_snapshots_dir,
    get_storage_stats,
    list_local_snapshots,
)


def print_snapshots_table(console: Console, snapshots_dir: Optional[Path] = None) -> None:
    """Print formatted snapshots table directly to stdout."""
    snapshots = list_local_snapshots(snapshots_dir)
    stats = get_storage_stats(get_base_dir())

    console.print()
    header_text = (
        f"[bold cyan]🕒 EasyCLI Time Machine[/bold cyan]  "
        f"[dim]({len(snapshots)} restore points · {stats.get('avail_human', '-')} free)[/dim]"
    )
    console.print(header_text)

    if not snapshots:
        console.print()
        console.print(
            Panel(
                "[yellow]No system restore points found.[/yellow]\n\n"
                "Run [bold green]ez time-machine[/bold green] to open the interactive manager,\n"
                "or run [bold green]ez time-machine create \"comment\"[/bold green] to take your first snapshot.",
                title="🕒 [bold cyan]Time Machine[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        return

    table = Table(
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Tag", style="bold")
    table.add_column("Restore Point ID", style="bold white", no_wrap=True)
    table.add_column("Type", style="yellow")
    table.add_column("Description / Reason", style="white")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Created", style="dim")


    for s in snapshots:
        tag = "⚡ Configs" if s.profile == "config" else "🖥️ Full Root"
        table.add_row(
            tag,
            s.id,
            s.profile.upper(),
            escape(s.comment or "Restore point"),
            format_human_size(s.size_bytes),
            s.created_at[:16] if s.created_at else "-",
        )

    console.print()
    console.print(table)


def run_cli_time_machine(
    raw_args: Optional[List[str]] = None,
    console: Optional[Console] = None,
) -> None:
    """Main CLI handler for 'ez time-machine'."""
    console = console or Console()
    args = [a.strip() for a in (raw_args or []) if a.strip()]

    # 1. Direct command: 'ez time-machine list'
    if len(args) == 1 and args[0].lower() in ("list", "ls", "status"):
        print_snapshots_table(console=console)
        return

    # 2. Direct command: 'ez time-machine create [comment]'
    if args and args[0].lower() in ("create", "snapshot", "backup", "save"):
        comment = " ".join(args[1:]) if len(args) > 1 else "Manual restore point"
        from ..elevation import elevated_tm_create
        console.print()
        with console.status(f"[bold cyan]Creating Time Machine restore point ('{escape(comment)}')...[/bold cyan]", spinner="dots"):
            ok, meta, err = elevated_tm_create(comment=comment, profile="config", console=console)
        if ok and meta:
            console.print(f"[bold green]✔ Restore point created successfully:[/bold green] [bold cyan]{meta.get('id', '')}[/bold cyan]")
            console.print(f"  [dim]Size: {format_human_size(meta.get('size_bytes', 0))} · Profile: {meta.get('profile', '').upper()}[/dim]")
        else:
            console.print(f"[bold red]❌ Failed creating restore point:[/bold red] {err}")
            sys.exit(1)
        return

    # 3. Path argument check: Reject raw paths
    if args:
        bad_arg = args[0]
        panel_width = max(45, min(console.width, 85))
        console.print()
        console.print(
            Panel(
                f"[bold red]Error: 'ez time-machine' does not accept path argument '[white]{escape(bad_arg)}[/white]'.[/bold red]\n\n"
                "[bold white]Available options:[/bold white]\n"
                "  • Run [bold green]ez time-machine[/bold green] for the interactive visual manager.\n"
                "  • Run [bold green]ez time-machine list[/bold green] to list existing restore points.\n"
                "  • Run [bold green]ez time-machine create \"comment\"[/bold green] to create a restore point.",
                title="❌ [bold red]Invalid Argument[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
                width=panel_width,
            )
        )
        sys.exit(1)

    # 4. Default: Launch full interactive Textual TUI
    from ..main import check_textual_installed
    if not check_textual_installed(console):
        sys.exit(1)

    from .time_machine_app import run_time_machine_app
    browse_target = run_time_machine_app()

    # If user pressed 'b' (Browse), launch file explorer at snapshot target
    if browse_target and os.path.exists(browse_target):
        from ..explorer.explorer_app import run_explorer
        run_explorer(initial_dir=browse_target, is_admin=True)
