"""CLI Handlers for 'ez extract-here' and 'ez extract'.

Implements:
- ez extract-here <file1.ext>, <file2.ext>, ... (current directory only)
- ez extract choose-directory (mini explorer archive selection + destination selection)
"""

import os
import sys
import tempfile
import time
from typing import List, Optional, Sequence, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .collectors import format_bytes
from .elevation import elevated_file_move, is_root
from .file_engine import is_destination_protected
from .extract_engine import (
    extract_archive,
    inspect_archive,
    normalize_target_args,
    validate_extract_target,
)


def parse_extract_cli_args(
    raw_args: Sequence[str],
) -> Tuple[List[str], Optional[str], bool]:
    """Parse raw arguments for 'ez extract'.

    Supports:
    - ez extract choose-directory
    - ez extract <file1.ext>,...,<file n.ext> to <destination>
    - ez extract <file1.ext>,...,<file n.ext> to choose-directory
    - ez extract <file1.ext>,...,<file n.ext> to
    - ez extract <file1.ext>,...,<file n.ext>

    Returns:
        (archives, explicit_destination, is_to_syntax)
    """
    expanded: List[str] = []
    for arg in raw_args:
        parts = [p.strip() for p in arg.split(",") if p.strip()]
        expanded.extend(parts)

    to_idx: Optional[int] = None
    for idx, token in enumerate(expanded):
        if token.lower() == "to":
            to_idx = idx
            break

    if to_idx is not None:
        archives = expanded[:to_idx]
        dest_parts = expanded[to_idx + 1 :]
        explicit_dest = " ".join(dest_parts).strip() if dest_parts else None
        return archives, explicit_dest, True

    is_choose = any(a.lower() in ("choose-directory", "choose", "picker", "select") for a in expanded)
    if is_choose:
        archives = [a for a in expanded if a.lower() not in ("choose-directory", "choose", "picker", "select")]
        return archives, "choose-directory", False

    return expanded, None, False


def run_cli_extract_here(
    raw_args: Sequence[str],
    console: Optional[Console] = None,
) -> None:
    """Extract archives directly into the current working directory only."""
    console = console or Console()
    cwd = os.getcwd()

    norm_args = normalize_target_args(raw_args)

    if not norm_args:
        console.print(f"[dim]Extraction location:[/dim] [cyan]{cwd}[/cyan]")
        try:
            prompt_input = Prompt.ask(
                "[bold cyan]Enter archive filename(s) in current directory to extract (separated by commas)[/bold cyan]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

        if not prompt_input:
            console.print("[dim]Cancelled.[/dim]")
            return
        norm_args = normalize_target_args([prompt_input])

    if not norm_args:
        console.print("[bold red]Error:[/bold red] No archive file specified.")
        return

    # 1. Validate all targets strictly in current directory
    resolved_archives: List[str] = []
    for raw in norm_args:
        is_valid, err_msg, abs_path = validate_extract_target(raw, cwd=cwd)
        if not is_valid:
            console.print(
                Panel(
                    err_msg,
                    title="[bold red]Direct Extraction Restricted[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return
        resolved_archives.append(abs_path)

    # 2. Execute extraction into cwd
    _run_extraction_pipeline(
        archive_paths=resolved_archives,
        dest_dir=cwd,
        console=console,
    )


def run_cli_extract(
    raw_args: Sequence[str],
    choose_dest: bool = False,
    console: Optional[Console] = None,
) -> None:
    """Extract archives with custom destination or mini explorer directory and destination selection."""
    console = console or Console()
    cwd = os.getcwd()

    archives_raw, explicit_dest, is_to_syntax = parse_extract_cli_args(raw_args)
    choose_requested = choose_dest or (
        bool(explicit_dest) and explicit_dest.lower() in ("choose-directory", "choose", "picker", "select")
    )

    resolved_archives: List[str] = []

    # 1. Resolve archives
    if not archives_raw:
        # Step 1: Open mini explorer to choose archive(s)
        console.print("[bold cyan]Step 1/2: Opening mini explorer to choose archive(s)...[/bold cyan]")
        from .explorer.explorer_app import run_extract_picker

        picked = run_extract_picker(initial_dir=".")
        if not picked:
            console.print("[dim]Extraction cancelled.[/dim]")
            return
        resolved_archives = [os.path.abspath(p) for p in picked]
    else:
        for raw in archives_raw:
            is_valid, err_msg, abs_p = validate_extract_target(raw, cwd=cwd)
            if not is_valid:
                console.print(
                    Panel(
                        err_msg,
                        title="[bold red]Archive Selection Error[/bold red]",
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
                return
            resolved_archives.append(abs_p)

    if not resolved_archives:
        console.print("[dim]No archives selected.[/dim]")
        return

    # 2. Resolve destination directory
    dest_dir = cwd

    if is_to_syntax:
        if explicit_dest and not choose_requested:
            dest_dir = os.path.abspath(os.path.expanduser(explicit_dest))
        elif choose_requested:
            console.print("[bold cyan]Opening mini explorer to choose destination directory...[/bold cyan]")
            from .explorer.explorer_app import run_destination_picker

            initial = os.path.dirname(resolved_archives[0]) if resolved_archives else "."
            picked_dest = run_destination_picker(initial_dir=initial)
            if not picked_dest or not isinstance(picked_dest, str):
                console.print("[dim]Extraction cancelled.[/dim]")
                return
            dest_dir = picked_dest
        else:
            # User ran 'ez extract <archives> to' without explicit destination argument
            if not sys.stdin.isatty():
                console.print(
                    Panel(
                        "Missing destination directory after '[bold cyan]to[/bold cyan]'.\n\n"
                        "Usage:\n"
                        "  [bold green]ez extract <file1.ext>,... to <destination>[/bold green]\n"
                        "  [bold green]ez extract <file1.ext>,... to choose-directory[/bold green]",
                        title="[bold red]Destination Required[/bold red]",
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
                return

            arc_names = ", ".join(os.path.basename(a) for a in resolved_archives)
            console.print(f"[dim]Archive(s) to extract:[/dim] [cyan]{arc_names}[/cyan]")
            try:
                prompt_dest = Prompt.ask(
                    "[bold cyan]Enter destination directory to extract to (or press Enter for mini explorer)[/bold cyan]"
                ).strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Extraction cancelled.[/dim]")
                return

            if not prompt_dest or prompt_dest.lower() in ("choose-directory", "choose", "picker", "select"):
                from .explorer.explorer_app import run_destination_picker

                initial = os.path.dirname(resolved_archives[0]) if resolved_archives else "."
                picked_dest = run_destination_picker(initial_dir=initial)
                if not picked_dest or not isinstance(picked_dest, str):
                    console.print("[dim]Extraction cancelled.[/dim]")
                    return
                dest_dir = picked_dest
            else:
                dest_dir = os.path.abspath(os.path.expanduser(prompt_dest))
    elif choose_requested or not archives_raw:
        # Step 2: Open mini explorer to choose destination
        console.print("[bold cyan]Step 2/2: Opening mini explorer to choose destination directory...[/bold cyan]")
        from .explorer.explorer_app import run_destination_picker

        initial = os.path.dirname(resolved_archives[0]) if resolved_archives else "."
        picked_dest = run_destination_picker(initial_dir=initial)
        if not picked_dest or not isinstance(picked_dest, str):
            console.print("[dim]Extraction cancelled.[/dim]")
            return
        dest_dir = picked_dest
    else:
        # User ran 'ez extract <archives>' without 'to' and without 'choose-directory'
        if sys.stdin.isatty():
            arc_names = ", ".join(os.path.basename(a) for a in resolved_archives)
            console.print(f"[dim]Archive(s) selected:[/dim] [cyan]{arc_names}[/cyan]")
            try:
                prompt_dest = Prompt.ask(
                    "[bold cyan]Enter destination directory (press Enter for current directory, or 'choose-directory')[/bold cyan]"
                ).strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Extraction cancelled.[/dim]")
                return

            if not prompt_dest:
                dest_dir = cwd
            elif prompt_dest.lower() in ("choose-directory", "choose", "picker", "select"):
                from .explorer.explorer_app import run_destination_picker

                initial = os.path.dirname(resolved_archives[0]) if resolved_archives else "."
                picked_dest = run_destination_picker(initial_dir=initial)
                if not picked_dest or not isinstance(picked_dest, str):
                    console.print("[dim]Extraction cancelled.[/dim]")
                    return
                dest_dir = picked_dest
            else:
                dest_dir = os.path.abspath(os.path.expanduser(prompt_dest))
        else:
            dest_dir = cwd

    # Ensure destination directory exists or is created if not protected
    if not is_destination_protected(dest_dir):
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except OSError as e:
            console.print(f"[bold red]Cannot create destination directory '{dest_dir}':[/bold red] {e}")
            return

    # 3. Execute extraction pipeline
    _run_extraction_pipeline(
        archive_paths=resolved_archives,
        dest_dir=dest_dir,
        console=console,
    )


def _run_extraction_pipeline(
    archive_paths: List[str],
    dest_dir: str,
    console: Console,
) -> None:
    """Internal runner for archive extraction with live progress and completion summary."""
    abs_dest = os.path.abspath(dest_dir)

    # Elevation check
    needs_elevation = is_destination_protected(abs_dest) or (
        os.path.exists(abs_dest) and not os.access(abs_dest, os.W_OK)
    )
    elevated_used = False

    if needs_elevation and not is_root():
        console.print(
            f"[yellow]Access denied:[/yellow] Extracting into '[cyan]{abs_dest}[/cyan]' requires admin rights."
        )
        confirm = Confirm.ask("Extract with admin rights? [Y/n]", default=True)
        if not confirm:
            console.print("[dim]Extraction cancelled.[/dim]")
            return
        elevated_used = True
    elif not needs_elevation:
        os.makedirs(abs_dest, exist_ok=True)

    # Pre-inspect archives to count total items and bytes
    total_expected_files = 0
    total_expected_dirs = 0
    total_expected_bytes = 0

    for arc in archive_paths:
        try:
            info = inspect_archive(arc)
            total_expected_files += info["file_count"]
            total_expected_dirs += info["dir_count"]
            total_expected_bytes += info["total_bytes"]
        except Exception as e:
            console.print(f"[bold red]Cannot read archive '{os.path.basename(arc)}':[/bold red] {e}")
            return

    total_expected_items = total_expected_files + total_expected_dirs
    start_time = time.time()
    extracted_archives_stats = []

    # Extraction target directory (staging dir if elevated)
    actual_extract_dest = abs_dest
    temp_staging: Optional[str] = None
    if elevated_used:
        temp_staging = tempfile.mkdtemp(prefix="ez_extract_")
        actual_extract_dest = temp_staging

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=25),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[detail]}[/dim]"),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            f"[cyan]Extracting {len(archive_paths)} archive(s)...[/cyan]",
            total=max(1, total_expected_items),
            detail="Preparing...",
        )

        overall_items_done = 0
        for arc in archive_paths:
            arc_name = os.path.basename(arc)

            def on_progress(cur: int, tot: int, cur_name: str, cur_bytes: int, tot_bytes: int) -> None:
                disp_name = cur_name if len(cur_name) <= 30 else f"...{cur_name[-27:]}"
                progress.update(
                    task_id,
                    completed=overall_items_done + cur,
                    description=f"[cyan]Extracting:[/cyan] {arc_name}",
                    detail=disp_name,
                )

            success, msg, stats = extract_archive(
                archive_path=arc,
                dest_dir=actual_extract_dest,
                progress_callback=on_progress,
            )

            if not success:
                console.print(
                    Panel(
                        f"[bold red]{msg}[/bold red]",
                        title=f"[bold red]❌ Failed: {arc_name}[/bold red]",
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
                if temp_staging and os.path.exists(temp_staging):
                    import shutil
                    shutil.rmtree(temp_staging, ignore_errors=True)
                return

            extracted_archives_stats.append(stats)
            overall_items_done += stats.get("total_items", 0)

    # If elevated staging was used, move items into actual protected destination
    if elevated_used and temp_staging:
        console.print("[bold cyan]Applying admin permissions to destination...[/bold cyan]")
        for item in os.listdir(temp_staging):
            src_item = os.path.join(temp_staging, item)
            dst_item = os.path.join(abs_dest, item)
            elevated_file_move(src_item, dst_item, console=console)
        try:
            os.rmdir(temp_staging)
        except OSError:
            pass

    elapsed = time.time() - start_time

    # Display completion summary card
    render_extraction_success_card(
        archives=archive_paths,
        dest_dir=abs_dest,
        total_files=total_expected_files,
        total_dirs=total_expected_dirs,
        total_bytes=total_expected_bytes,
        elapsed_seconds=elapsed,
        elevated=elevated_used,
        console=console,
    )


def render_extraction_success_card(
    archives: List[str],
    dest_dir: str,
    total_files: int,
    total_dirs: int,
    total_bytes: int,
    elapsed_seconds: float,
    elevated: bool,
    console: Console,
) -> None:
    """Render a modern Rich summary card upon successful archive extraction."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold white", width=22)
    table.add_column(style="dim white")

    arc_names = ", ".join(os.path.basename(a) for a in archives)
    table.add_row("📦  Archive(s):", f"[bold cyan]{arc_names}[/bold cyan]")
    table.add_row("📂  Extracted To:", f"[cyan]{dest_dir}[/cyan]")
    table.add_row(
        "📄  Items Extracted:",
        f"[bold green]{total_files} file(s)[/bold green], {total_dirs} folder(s)",
    )
    table.add_row("📊  Extracted Size:", f"{format_bytes(total_bytes)}")
    table.add_row("⏱️  Duration:", f"{elapsed_seconds:.2f}s")

    admin_badge = " 🔒 [bold yellow](Admin)[/bold yellow]" if elevated else ""
    title = f"[bold green]✔ Archive(s) Extracted Successfully{admin_badge}[/bold green]"

    console.print()
    console.print(
        Panel(
            table,
            title=title,
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
