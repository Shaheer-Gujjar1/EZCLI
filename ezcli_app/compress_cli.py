"""Command-line interface handler for ez compress."""

import os
import sys
from typing import Optional, Sequence

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
from rich.prompt import Prompt
from rich.table import Table

from .collectors import format_bytes
from .compress_engine import (
    calculate_targets_summary,
    compress_targets,
    validate_compress_target,
)
from .compress_tui import run_format_selector
from .file_engine import get_unique_destination_name, normalize_target_args


def run_cli_compress(
    targets: Optional[Sequence[str]] = None,
    console: Optional[Console] = None,
) -> None:
    """Main CLI entrypoint for 'ez compress'.

    Supports:
    - ez compress -> opens mini explorer to choose files/folders visually
    - ez compress choose-directory -> opens mini explorer visually
    - ez compress <folder1/> <folder2/> ... -> compresses folders in current directory only
    - ez compress <file1.ext> <file2.ext> ... -> compresses files in current directory only
    - ez compress f1.txt, f2.txt, folder1/ -> comma-separated syntax supported
    """
    console = console or Console()
    raw_args = list(targets or [])
    norm_args = normalize_target_args(raw_args)

    resolved_targets = []
    base_dir = os.getcwd()

    # 1. Determine targets (Visual mode vs Direct mode)
    if not norm_args or norm_args == ["choose-directory"]:
        from .explorer.explorer_app import run_compress_picker

        console.print("[bold cyan]Opening mini explorer to choose file(s) or folder(s) to compress...[/bold cyan]")
        chosen_paths = run_compress_picker(initial_dir=".")
        if not chosen_paths:
            console.print("[dim]Compression cancelled (no items selected).[/dim]")
            return

        resolved_targets = chosen_paths
        if resolved_targets:
            first_parent = os.path.dirname(os.path.abspath(resolved_targets[0]))
            # If all items share same parent, output in that parent directory; otherwise current directory
            if all(os.path.dirname(os.path.abspath(p)) == first_parent for p in resolved_targets):
                base_dir = first_parent
            else:
                base_dir = os.getcwd()
    else:
        # User provided direct arguments (must be in current directory)
        if any(a.lower() in ("choose-directory", "choose", "picker") for a in norm_args):
            console.print(
                "[bold red]Error:[/bold red] 'choose-directory' cannot be mixed with direct file or folder arguments."
            )
            return

        for raw in norm_args:
            is_valid, err_msg, abs_path, is_dir = validate_compress_target(raw, cwd=base_dir)
            if not is_valid:
                console.print(
                    Panel(
                        err_msg,
                        title="[bold red]Direct Compress Restricted[/bold red]",
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
                return
            resolved_targets.append(abs_path)

    if not resolved_targets:
        console.print("[dim]No valid items selected to compress.[/dim]")
        return

    # 2. Interactive TUI Format & Name Selection
    selection = run_format_selector(targets=resolved_targets, console=console)
    if not selection:
        console.print("[dim]Compression cancelled.[/dim]")
        return

    selected_format = selection["format"]
    archive_name = selection["archive_name"]

    # 3. Output Path Resolution & Conflict Handling
    output_path = os.path.join(base_dir, archive_name)

    if os.path.exists(output_path):
        console.print(
            f"\n[bold yellow]⚠️ File already exists:[/bold yellow] [cyan]{output_path}[/cyan]"
        )
        choice = Prompt.ask(
            "Conflict resolution: [bold cyan]O[/bold cyan]verwrite, [bold green]R[/bold green]ename, or [bold red]C[/bold red]ancel?",
            choices=["o", "O", "r", "R", "c", "C"],
            default="r",
            console=console,
        ).lower()

        if choice == "c":
            console.print("[dim]Compression cancelled.[/dim]")
            return
        elif choice == "r":
            output_path = get_unique_destination_name(output_path)
            console.print(f"[dim]Archive will be saved as:[/dim] [cyan]{os.path.basename(output_path)}[/cyan]")

    # 4. Summary & Live Progress Execution
    summary = calculate_targets_summary(resolved_targets)
    total_items = len(summary["entries"])
    total_bytes = summary["total_bytes"]

    if total_items == 0:
        console.print("[bold red]Error:[/bold red] Selected items contain no files or directories to compress.")
        return

    console.print(
        f"\n[bold cyan]🗜️ Compressing {total_items} items into {os.path.basename(output_path)}...[/bold cyan]\n"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Starting compression...[/cyan]", total=total_items)

        def on_progress(cur_idx: int, tot_items: int, cur_name: str, cur_bytes: int, tot_bytes: int) -> None:
            disp_name = cur_name if len(cur_name) <= 32 else f"...{cur_name[-29:]}"
            progress.update(
                task_id,
                completed=cur_idx,
                description=f"[cyan]Compressing:[/cyan] {disp_name}",
            )

        success, msg, stats = compress_targets(
            targets=resolved_targets,
            output_path=output_path,
            format_type=selected_format,
            progress_callback=on_progress,
        )

    # 5. Success / Error Feedback Card
    if success:
        render_compression_success_card(stats, console)
    else:
        console.print(
            Panel(
                f"[bold red]{msg}[/bold red]",
                title="[bold red]❌ Compression Failed[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


def render_compression_success_card(stats: dict, console: Console) -> None:
    """Render a modern EasyCLI summary card upon successful archive creation."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white", width=22)
    table.add_column(style="dim white")

    table.add_row("🗜️  Archive Path:", f"[bold cyan]{stats['output_path']}[/bold cyan]")
    table.add_row("📦  Archive Format:", f"{stats['format']} ({stats['extension']})")
    table.add_row(
        "📁  Items Included:",
        f"{stats['total_items']} items ({stats['file_count']} files, {stats['dir_count']} folders)",
    )
    table.add_row("📊  Original Size:", f"{format_bytes(stats['uncompressed_bytes'])}")
    table.add_row("💾  Compressed Size:", f"[bold green]{format_bytes(stats['compressed_bytes'])}[/bold green]")

    if stats["uncompressed_bytes"] > 0:
        table.add_row(
            "⚡  Space Saved:",
            f"[bold green]{stats['saved_ratio']:.1f}% reduced[/bold green] ({format_bytes(stats['saved_bytes'])} saved)",
        )
    table.add_row("⏱️  Elapsed Time:", f"{stats['elapsed_seconds']:.2f} seconds")

    console.print(
        Panel(
            table,
            title="[bold green]🎉 Archive Created Successfully![/bold green]",
            subtitle="[dim]Tip: Extract anytime using standard tools or inspect with EasyCLI[/dim]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
