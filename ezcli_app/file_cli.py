"""Interactive CLI handlers for copy, move, and undo operations in EasyCLI v0.2."""

import os
import sys
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .collectors import format_bytes
from .explorer.explorer_app import (
    run_choose_directory,
    run_destination_picker,
    run_source_picker,
)
from .file_engine import execute_file_operation, preview_file_operation
from .undo import execute_undo, peek_last_operation, pop_last_operation


def prompt_conflict_resolution(console: Console, filename: str) -> str:
    """Prompt user how to handle an individual colliding file."""
    console.print(f"\n[bold yellow]Conflict:[/bold yellow] File '[bold cyan]{filename}[/bold cyan]' already exists at destination.")
    choice = Prompt.ask(
        "Choose action",
        choices=["o", "s", "r", "a"],
        default="o",
        show_choices=False,
    )
    # o=overwrite, s=skip, r=rename, a=abort
    mapping = {
        "o": "overwrite",
        "s": "skip",
        "r": "rename",
        "a": "abort",
    }
    return mapping.get(choice.lower(), "skip")


def run_cli_file_op(action: str, args: List[str], console: Optional[Console] = None) -> None:
    """Run copy or move flow with picker or CLI arguments."""
    console = console or Console()

    # Parse --yes / -y flag
    auto_yes = False
    clean_args: List[str] = []
    for a in args:
        if a in ("-y", "--yes"):
            auto_yes = True
        else:
            clean_args.append(a)

    sources: List[str] = []
    destination: str = ""

    # Flow A: No arguments -> Two-stage Picker Flow
    if len(clean_args) < 2:
        console.print(
            Panel(
                f"[bold cyan]Interactive {action.capitalize()} Picker[/bold cyan]\n"
                f"1. Select files or folders using [bold yellow][Space][/bold yellow]\n"
                f"2. Confirm with [bold yellow][c][/bold yellow] or [bold yellow][Enter][/bold yellow]\n"
                f"3. Select destination directory in the second step",
                box=box.ROUNDED,
                border_style="cyan",
            )
        )
        sources = run_source_picker()
        if not sources:
            console.print("[yellow]No source items selected. Operation cancelled.[/yellow]")
            return

        destination = run_destination_picker()
        if not destination:
            console.print("[yellow]No destination directory selected. Operation cancelled.[/yellow]")
            return

    # Flow B: Arguments provided -> Direct CLI mode
    else:
        sources = clean_args[:-1]
        destination = clean_args[-1]

    # Generate Preview
    preview = preview_file_operation(action, sources, destination)
    if preview.get("errors"):
        for err in preview["errors"]:
            console.print(f"[bold red]Warning:[/bold red] {err}")
        if not preview["items"]:
            console.print(f"[bold red]No valid items found to {action}. Aborted.[/bold red]")
            return

    # Display Preview Card
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    table.add_row("Operation", f"[bold green]{action.upper()}[/bold green]")
    table.add_row("Total Items", str(preview["count"]))
    table.add_row("Total Size", preview["total_size_str"])
    table.add_row("Destination", f"[bold cyan]{preview['destination']}[/bold cyan]")

    items_summary = ", ".join([item["name"] for item in preview["items"][:5]])
    if len(preview["items"]) > 5:
        items_summary += f" ... (+{len(preview['items']) - 5} more)"
    table.add_row("Selected Items", items_summary)

    collisions = preview.get("collisions", [])
    if collisions:
        table.add_row(
            "Collisions",
            f"[bold yellow]{len(collisions)} file(s) already exist at destination![/bold yellow]",
        )

    panel = Panel(
        table,
        title=f"📋 [bold]{action.capitalize()} Preview[/bold]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)

    # Conflict Policy
    conflict_policy = "ask"
    if collisions:
        if not auto_yes:
            console.print("[yellow]Some items already exist at the destination.[/yellow]")
            policy_choice = Prompt.ask(
                "Select conflict policy: [bold]a[/bold]sk per file, [bold]s[/bold]kip, [bold]o[/bold]verwrite, [bold]r[/bold]ename",
                choices=["a", "s", "o", "r"],
                default="a",
            ).lower()
            conflict_policy = {
                "a": "ask",
                "s": "skip",
                "o": "overwrite",
                "r": "rename",
            }.get(policy_choice, "ask")
        else:
            conflict_policy = "skip"

    # Confirmation
    if not auto_yes:
        confirmed = Confirm.ask(f"Proceed with {action}?", default=True)
        if not confirmed:
            console.print("[dim]Operation cancelled by user.[/dim]")
            return

    # Execute with Live Progress Bar
    total_items = preview["count"]
    total_bytes = preview["total_bytes"]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(f"[cyan]{action.capitalize()}ing items...[/cyan]", total=total_items)

        def on_progress(cur_idx, tot_items, name, cur_bytes, tot_bytes):
            progress.update(
                task_id,
                completed=cur_idx,
                description=f"[cyan]{action.capitalize()}ing:[/cyan] {name[:24]}",
            )

        success, msg, executed = execute_file_operation(
            action=action,
            sources=sources,
            destination=destination,
            conflict_policy=conflict_policy,
            prompt_callback=lambda fname: prompt_conflict_resolution(console, fname),
            progress_callback=on_progress,
        )

    if success:
        console.print(
            Panel(
                f"[bold green]✔ {msg}[/bold green]\n\n"
                f"[dim]💡 Operation logged to undo history. To revert, run:[/dim]\n"
                f"   [bold cyan]ezcli undo[/bold cyan]",
                title="[bold green]Success[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(f"[bold red]Failed:[/bold red] {msg}")


def run_cli_undo(console: Optional[Console] = None) -> None:
    """Inspect and revert the most recent file operation."""
    console = console or Console()
    last_op = peek_last_operation()

    if not last_op:
        console.print(
            Panel(
                "[yellow]No recent copy or move operations found in the undo log.[/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
                title="Undo History",
            )
        )
        return

    # Show preview of operation to undo
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold cyan", width=16)
    table.add_column("Value", style="white")

    action = last_op.get("action", "unknown").upper()
    timestamp = last_op.get("timestamp", "unknown")
    items = last_op.get("items", [])

    table.add_row("Operation", f"[bold yellow]{action}[/bold yellow]")
    table.add_row("Timestamp", timestamp)
    table.add_row("Total Items", str(len(items)))

    sample_items = [f"{os.path.basename(i.get('dst', ''))} (from {i.get('src', '')})" for i in items[:4]]
    table.add_row("Revert Details", "\n".join(sample_items))

    panel = Panel(
        table,
        title="⏪ [bold]Undo Operation Preview[/bold]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)

    confirmed = Confirm.ask(f"Are you sure you want to revert this {action} operation?", default=True)
    if not confirmed:
        console.print("[dim]Undo cancelled.[/dim]")
        return

    # Execute undo
    success, msg, reverted = execute_undo(last_op)
    if success:
        pop_last_operation()
        console.print(
            Panel(
                f"[bold green]✔ Undo Successful![/bold green]\n\n{msg}",
                title="[bold green]Reverted[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(f"[bold red]Undo Error:[/bold red] {msg}")
