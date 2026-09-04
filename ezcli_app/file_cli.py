"""Interactive CLI handlers for copy, move, paste, undo, and redo in EasyCLI v0.2."""

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
    run_destination_picker,
    run_source_picker,
)
from .explorer.file_icons import get_file_icon
from .file_engine import (
    execute_file_operation,
    is_destination_protected,
    preview_file_operation,
    scan_source_items,
)
from .undo import (
    clear_clipboard,
    execute_redo,
    execute_undo,
    get_clipboard,
    peek_last_operation,
    peek_redo_operation,
    pop_last_operation,
    pop_redo_operation,
    push_redo_operation,
    record_operation,
    set_clipboard,
)


def prompt_conflict_resolution(console: Console, filename: str) -> str:
    """Prompt user how to handle an individual colliding file."""
    console.print(f"\n[bold yellow]⚠️ Conflict:[/bold yellow] Item '[bold cyan]{filename}[/bold cyan]' already exists at destination.")
    choice = Prompt.ask(
        "Choose resolution: [bold]o[/bold]verwrite, [bold]s[/bold]kip, [bold]r[/bold]ename, [bold]a[/bold]bort",
        choices=["o", "s", "r", "a"],
        default="o",
    )
    mapping = {
        "o": "overwrite",
        "s": "skip",
        "r": "rename",
        "a": "abort",
    }
    return mapping.get(choice.lower(), "skip")


# ==============================================================================
# Copy & Move Staging
# ==============================================================================
def run_cli_stage(action: str, console: Optional[Console] = None, is_admin: bool = False) -> None:
    """Launch the mini explorer to choose files/folders to copy or move."""
    console = console or Console()
    icon = "📋" if action == "copy" else "🚚"
    border_color = "cyan" if action == "copy" else "yellow"

    # Launch mini explorer picker
    selected_items = run_source_picker()
    if not selected_items:
        console.print("[dim]No items selected. Nothing added to clipboard.[/dim]")
        return

    # Stage to clipboard
    set_clipboard(action, selected_items)

    # Scan details for summary card
    items, total_bytes, errors = scan_source_items(selected_items)

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=20)
    table.add_column("Value", style="white")

    action_label = f"{icon} COPY (Ready to Paste)" if action == "copy" else f"{icon} MOVE / CUT (Ready to Paste)"
    table.add_row("Action", action_label)
    table.add_row("Total Items Staged", str(len(items)))
    table.add_row("Combined Size", format_bytes(total_bytes))

    # Format item lines with file-type emojis
    item_lines = []
    for it in items[:6]:
        item_icon = get_file_icon(it["name"], is_dir=it["is_dir"])
        item_lines.append(f"  {item_icon} {it['name']} [dim]({it['size_str']})[/dim]")
    if len(items) > 6:
        item_lines.append(f"  [dim]... and {len(items) - 6} more item(s)[/dim]")

    table.add_row("Staged Items", "\n".join(item_lines))

    hint_box = (
        f"\n[bold green]👉 Next Step:[/bold green]\n"
        f"   Run [bold cyan]ezcli paste[/bold cyan] to choose your destination directory and paste!"
    )

    console.print(
        Panel(
            table,
            title=f"{icon} [bold]EasyCLI Clipboard[/bold]",
            subtitle=hint_box,
            border_style=border_color,
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )


# ==============================================================================
# Paste Flow
# ==============================================================================
def run_cli_paste(console: Optional[Console] = None, is_admin: bool = False) -> None:
    """Launch destination explorer to choose destination and execute paste."""
    console = console or Console()

    # Check clipboard
    clip = get_clipboard()
    if not clip or not clip.get("items"):
        console.print(
            Panel(
                "📋 [bold yellow]Your clipboard is currently empty![/bold yellow]\n\n"
                "💡 [bold]How to use EasyCLI Copy & Paste:[/bold]\n"
                "  1. Run [bold cyan]ezcli copy[/bold cyan] or [bold cyan]ezcli move[/bold cyan] to choose files/folders with the mini explorer.\n"
                "  2. Run [bold cyan]ezcli paste[/bold cyan] to choose the destination folder!",
                title="[bold yellow]Clipboard Empty[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        return

    action = clip.get("action", "copy")
    sources = clip.get("items", [])
    icon = "📋" if action == "copy" else "🚚"

    # Launch mini explorer to choose destination directory
    destination = run_destination_picker()
    if not destination:
        console.print("[dim]Paste cancelled. Staged items remain safely on your clipboard.[/dim]")
        return

    is_protected = is_admin or is_destination_protected(destination)

    # Generate Preview
    preview = preview_file_operation(action, sources, destination)
    if preview.get("errors"):
        for err in preview["errors"]:
            console.print(f"[bold red]Warning:[/bold red] {err}")
        if not preview["items"]:
            console.print(f"[bold red]No valid items found to paste. Aborted.[/bold red]")
            return

    # Preview Summary Card
    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    if is_protected:
        table.add_row(
            "🛡️ Risk Badge",
            "[bold red]HIGH RISK (Protected System Directory — Admin Rights Required)[/bold red]",
        )

    action_title = f"{action.upper()} (Admin Rights Active)" if is_protected else action.upper()
    table.add_row("Operation", f"[bold green]{icon} {action_title}[/bold green]")
    table.add_row("Total Items", str(preview["count"]))
    table.add_row("Total Size", preview["total_size_str"])
    table.add_row("Destination", f"[bold cyan]📁 {preview['destination']}[/bold cyan]")

    items_summary = []
    for it in preview["items"][:5]:
        it_icon = get_file_icon(it["name"], is_dir=it["is_dir"])
        items_summary.append(f"{it_icon} {it['name']} ({it['size_str']})")
    if len(preview["items"]) > 5:
        items_summary.append(f"... (+{len(preview['items']) - 5} more)")
    table.add_row("Items to Paste", "\n".join(items_summary))

    collisions = preview.get("collisions", [])
    if collisions:
        table.add_row(
            "Collisions",
            f"[bold yellow]⚠️ {len(collisions)} item(s) already exist at destination![/bold yellow]",
        )

    card_border = "red" if is_protected else ("cyan" if action == "copy" else "yellow")
    panel = Panel(
        table,
        title=f"{icon} [bold]{action.capitalize()} Summary[/bold]",
        border_style=card_border,
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)

    # Conflict Policy if collisions exist
    conflict_policy = "ask"
    if collisions:
        console.print("\n[yellow]Some items already exist at the destination directory.[/yellow]")
        policy_choice = Prompt.ask(
            "Select resolution policy: [bold]a[/bold]sk per item, [bold]s[/bold]kip, [bold]o[/bold]verwrite, [bold]r[/bold]ename",
            choices=["a", "s", "o", "r"],
            default="a",
        ).lower()
        conflict_policy = {
            "a": "ask",
            "s": "skip",
            "o": "overwrite",
            "r": "rename",
        }.get(policy_choice, "ask")

    # Confirmation Prompt
    prompt_msg = f"Proceed with elevated {action} into protected directory?" if is_protected else f"Proceed with {action}?"
    confirmed = Confirm.ask(prompt_msg, default=True)
    if not confirmed:
        console.print("[dim]Paste cancelled by user. Items remain safely on your clipboard.[/dim]")
        return

    # If protected, show plain English explanation before password entry
    if is_protected:
        from .elevation import explain_elevation
        if not explain_elevation(
            reason=f"Destination directory '{destination}' requires administrator rights to write or modify files.",
            task_description=f"Paste {preview['count']} item(s) into '{destination}'",
            risk_level="high",
            console=console,
        ):
            console.print("[dim]Paste cancelled. Staged items remain safely on your clipboard.[/dim]")
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
        task_id = progress.add_task(f"[cyan]Pasting items...[/cyan]", total=total_items)

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
            is_admin=is_protected,
        )

    if success:
        # If move, clear clipboard so items aren't moved twice
        if action == "move":
            clear_clipboard()

        console.print(
            Panel(
                f"[bold green]✔ {msg}[/bold green]\n\n"
                f"💡 [bold]Need to undo?[/bold]\n"
                f"   Run [bold cyan]ezcli undo[/bold cyan] to safely revert this paste operation at any time.",
                title="[bold green]🎉 Paste Complete[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(f"[bold red]Failed:[/bold red] {msg}")


# ==============================================================================
# Undo & Redo Handlers
# ==============================================================================
def run_cli_undo(console: Optional[Console] = None, is_admin: bool = False) -> None:
    """Revert the most recent paste operation."""
    console = console or Console()
    last_op = peek_last_operation()

    if not last_op:
        console.print(
            Panel(
                "ℹ️ [yellow]No recent paste operations found to undo.[/yellow]",
                box=box.ROUNDED,
                border_style="yellow",
                title="[bold]Undo History[/bold]",
            )
        )
        return

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    action = last_op.get("action", "unknown").upper()
    timestamp = last_op.get("timestamp", "unknown")
    items = last_op.get("items", [])

    is_protected = is_admin or any(
        is_destination_protected(i.get("dst", "")) or is_destination_protected(i.get("src", ""))
        for i in items
    )
    if is_protected:
        table.add_row(
            "🛡️ Risk Badge",
            "[bold red]HIGH RISK (Reverting Protected System Files — Admin Rights Required)[/bold red]",
        )

    action_label = f"{action} (Admin Rights Active)" if is_protected else action
    table.add_row("Operation to Revert", f"[bold yellow]{action_label}[/bold yellow]")
    table.add_row("Timestamp", timestamp)
    table.add_row("Total Items", str(len(items)))

    sample_items = []
    for i in items[:4]:
        name = os.path.basename(i.get("dst", ""))
        sample_items.append(f"  • {name} [dim](from {i.get('src', '')})[/dim]")
    if len(items) > 4:
        sample_items.append(f"  [dim]... and {len(items) - 4} more[/dim]")

    table.add_row("Revert Items", "\n".join(sample_items))

    panel = Panel(
        table,
        title="⏪ [bold]Undo Operation Preview[/bold]",
        border_style="red" if is_protected else "yellow",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)

    prompt_msg = f"Are you sure you want to revert this elevated {action} operation?" if is_protected else f"Are you sure you want to revert this {action} operation?"
    confirmed = Confirm.ask(prompt_msg, default=True)
    if not confirmed:
        console.print("[dim]Undo cancelled.[/dim]")
        return

    if is_protected:
        from .elevation import explain_elevation
        if not explain_elevation(
            reason="Reverting files located in protected system directories requires administrator rights.",
            task_description=f"Revert {action} of {len(items)} item(s)",
            risk_level="high",
            console=console,
        ):
            console.print("[dim]Undo cancelled.[/dim]")
            return

    success, msg, reverted = execute_undo(last_op)
    if success:
        # Move operation from undo stack to redo stack
        pop_last_operation()
        push_redo_operation(last_op)

        console.print(
            Panel(
                f"[bold green]✔ Undo Successful![/bold green]\n\n"
                f"{msg}\n\n"
                f"💡 [bold]Changed your mind?[/bold]\n"
                f"   Run [bold cyan]ezcli redo[/bold cyan] to re-apply this operation.",
                title="[bold green]Reverted[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(f"[bold red]Undo Error:[/bold red] {msg}")


def run_cli_redo(console: Optional[Console] = None, is_admin: bool = False) -> None:
    """Re-apply the most recently undone operation."""
    console = console or Console()
    redo_op = peek_redo_operation()

    if not redo_op:
        console.print(
            Panel(
                "ℹ️ [yellow]No undone operations found to redo.[/yellow]",
                box=box.ROUNDED,
                border_style="magenta",
                title="[bold]Redo History[/bold]",
            )
        )
        return

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold magenta", width=18)
    table.add_column("Value", style="white")

    action = redo_op.get("action", "unknown").upper()
    timestamp = redo_op.get("timestamp", "unknown")
    items = redo_op.get("items", [])

    is_protected = is_admin or any(
        is_destination_protected(i.get("dst", "")) or is_destination_protected(i.get("src", ""))
        for i in items
    )
    if is_protected:
        table.add_row(
            "🛡️ Risk Badge",
            "[bold red]HIGH RISK (Re-applying Protected System Files — Admin Rights Required)[/bold red]",
        )

    action_label = f"{action} (Admin Rights Active)" if is_protected else action
    table.add_row("Operation to Re-apply", f"[bold magenta]{action_label}[/bold magenta]")
    table.add_row("Original Timestamp", timestamp)
    table.add_row("Total Items", str(len(items)))

    sample_items = []
    for i in items[:4]:
        name = os.path.basename(i.get("src", ""))
        sample_items.append(f"  • {name} ➔ [dim]{i.get('dst', '')}[/dim]")
    if len(items) > 4:
        sample_items.append(f"  [dim]... and {len(items) - 4} more[/dim]")

    table.add_row("Re-apply Items", "\n".join(sample_items))

    panel = Panel(
        table,
        title="⏩ [bold]Redo Operation Preview[/bold]",
        border_style="red" if is_protected else "magenta",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)

    prompt_msg = f"Are you sure you want to re-apply this elevated {action} operation?" if is_protected else f"Are you sure you want to re-apply this {action} operation?"
    confirmed = Confirm.ask(prompt_msg, default=True)
    if not confirmed:
        console.print("[dim]Redo cancelled.[/dim]")
        return

    if is_protected:
        from .elevation import explain_elevation
        if not explain_elevation(
            reason="Re-applying files to protected system directories requires administrator rights.",
            task_description=f"Re-apply {action} of {len(items)} item(s)",
            risk_level="high",
            console=console,
        ):
            console.print("[dim]Redo cancelled.[/dim]")
            return

    success, msg, reapplied = execute_redo(redo_op)
    if success:
        # Move operation back from redo stack to undo stack
        pop_redo_operation()
        record_operation(redo_op["action"], redo_op["items"], redo_op.get("description", ""))

        console.print(
            Panel(
                f"[bold green]✔ Redo Successful![/bold green]\n\n"
                f"{msg}\n\n"
                f"💡 [bold]Need to revert again?[/bold]\n"
                f"   Run [bold cyan]ezcli undo[/bold cyan] to undo this operation.",
                title="[bold green]Re-applied[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(f"[bold red]Redo Error:[/bold red] {msg}")
