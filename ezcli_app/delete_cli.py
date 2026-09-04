"""Interactive CLI handlers for ezcli delete command."""

import errno
import os
import stat
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .collectors import format_bytes
from .elevation import elevated_file_delete, is_root
from .explorer.file_icons import get_file_icon
from .file_engine import is_destination_protected


def validate_direct_delete_target(
    raw_target: str,
    cwd: Optional[str] = None,
) -> Tuple[bool, str, str, bool]:
    """
    Validate a target path for direct delete command.
    
    Rules:
    - Direct deletion is restricted to items in current directory only.
    - No subfolder paths allowed (e.g. 'folder/sub/' or 'sub/file.txt' rejected).
    - Trailing slash (e.g. 'my_folder/') is allowed and indicates folder deletion.
    
    Returns:
        (is_valid, error_msg, resolved_abs_path, is_dir)
    """
    cleaned = raw_target.strip()
    if not cleaned:
        return False, "Target name cannot be empty.", "", False

    effective_cwd = cwd or os.getcwd()

    # If user provided a path with '/' that is not just a single trailing slash
    # e.g., 'a/b', 'a/b/', '../file', '/tmp/file'
    has_internal_slash = ("/" in cleaned.rstrip("/")) or ("\\" in cleaned.rstrip("\\"))
    if has_internal_slash or cleaned in (".", ".."):
        return (
            False,
            "Direct deletion is only supported for items in the current directory.\n"
            "To delete items in subfolders or other locations, use 'ezcli delete choose-directory' "
            "to navigate and select items visually.",
            "",
            False,
        )

    # Check trailing slash intent
    expects_dir = cleaned.endswith("/") or cleaned.endswith("\\")
    name = cleaned.rstrip("/\\")

    target_path = os.path.join(effective_cwd, name)

    if not os.path.exists(target_path) and not os.path.islink(target_path):
        return (
            False,
            f"Item '[yellow]{name}[/yellow]' does not exist in the current directory.",
            "",
            False,
        )

    is_dir = os.path.isdir(target_path) and not os.path.islink(target_path)

    if expects_dir and not is_dir:
        return (
            False,
            f"'[yellow]{cleaned}[/yellow]' specifies a folder (trailing slash), but an ordinary file was found.",
            "",
            False,
        )

    return True, "", target_path, is_dir


def get_item_size(path: str) -> int:
    """Calculate total size of file or directory tree."""
    if os.path.islink(path) or not os.path.isdir(path):
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except Exception:
                    pass
    except Exception:
        pass
    return total


def delete_single_item(
    path: str,
    is_dir: bool,
    console: Console,
) -> Tuple[bool, str]:
    """
    Delete a single file or directory honoring non-force first and automatic elevation.
    
    1. Always runs without force first.
    2. If directory is non-empty, prompts user for forced removal.
    3. If permission error / protected, prompts user for automatic elevation.
    
    Returns:
        (success, message)
    """
    item_name = os.path.basename(path) or path
    protected = is_destination_protected(path)
    force = False

    # Non-forced attempt
    if not protected and not is_root():
        try:
            if is_dir:
                os.rmdir(path)
            else:
                os.remove(path)
            return True, "Deleted successfully"
        except OSError as e:
            # Check if directory is not empty
            if is_dir and e.errno in (errno.ENOTEMPTY, errno.EEXIST):
                console.print(
                    f"\n[yellow]⚠️ Folder '[bold cyan]{item_name}[/bold cyan]' is not empty "
                    f"and cannot be deleted without force.[/yellow]"
                )
                confirm_force = Confirm.ask(
                    "Delete folder and all its contents forcefully? [y/N]",
                    default=False,
                )
                if not confirm_force:
                    return False, "Skipped (non-empty directory, force refused)"
                force = True
                try:
                    import shutil
                    shutil.rmtree(path)
                    return True, "Deleted forcefully"
                except PermissionError:
                    # Proceed to elevation prompt below
                    pass
                except Exception as ex:
                    return False, f"Error during forced deletion: {ex}"
            elif isinstance(e, PermissionError):
                # Will handle elevation prompt below
                pass
            else:
                return False, f"Cannot delete item: {e}"

    # If we reached here, elevation is needed (either protected, or PermissionError encountered)
    console.print(
        f"\n[yellow]🔒 Admin rights are required to delete '[bold cyan]{item_name}[/bold cyan]'.[/yellow]"
    )
    confirm_admin = Confirm.ask("Delete with admin rights? [Y/n]", default=True)
    if not confirm_admin:
        return False, "Skipped (admin rights declined)"

    # If it was a non-empty directory and force hasn't been confirmed yet
    if is_dir and not force:
        # Check if empty or not
        try:
            entries = os.listdir(path)
            if entries:
                console.print(
                    f"[yellow]⚠️ Folder '[bold cyan]{item_name}[/bold cyan]' is not empty.[/yellow]"
                )
                confirm_force = Confirm.ask(
                    "Delete folder and all contents forcefully with admin rights? [y/N]",
                    default=False,
                )
                if not confirm_force:
                    return False, "Skipped (non-empty directory, force refused)"
                force = True
        except Exception:
            force = True

    ok, err = elevated_file_delete(
        path=path,
        is_dir=is_dir,
        force=force,
        reason=f"Delete '{item_name}'" + (" forcefully" if force else ""),
        console=console,
    )
    if ok:
        badge = "forcefully with admin rights" if force else "with admin rights"
        return True, f"Deleted {badge}"
    else:
        return False, f"Elevated deletion failed: {err}"


def run_cli_delete(
    args: Optional[List[str]] = None,
    console: Optional[Console] = None,
) -> None:
    """
    Main CLI entrypoint for 'ezcli delete'.
    
    Supports:
    - ezcli delete choose-directory -> opens visual picker in mini explorer
    - ezcli delete <folder/> -> deletes folder in current directory only
    - ezcli delete <file.ext> -> deletes file in current directory only
    """
    console = console or Console()
    args = args or []

    # 1. Determine target paths
    target_items: List[Tuple[str, bool]] = []  # List of (abs_path, is_dir)

    if not args or args == ["choose-directory"]:
        from .explorer.explorer_app import run_source_picker
        console.print("[bold cyan]Opening mini explorer to choose file(s) or folder(s) to delete...[/bold cyan]")
        chosen_paths = run_source_picker(initial_dir=".")
        if not chosen_paths:
            console.print("[dim]Deletion cancelled (no items selected).[/dim]")
            return
        for p in chosen_paths:
            is_d = os.path.isdir(p) and not os.path.islink(p)
            target_items.append((p, is_d))
    else:
        # User provided direct arguments (must be in current directory)
        for raw in args:
            if raw == "choose-directory":
                console.print(
                    "[bold red]Error:[/bold red] 'choose-directory' cannot be mixed with direct file or folder arguments."
                )
                return
            is_valid, err_msg, abs_path, is_dir = validate_direct_delete_target(raw)
            if not is_valid:
                console.print(f"[bold red]Error:[/bold red] {err_msg}")
                return
            target_items.append((abs_path, is_dir))

    if not target_items:
        console.print("[dim]No items to delete.[/dim]")
        return

    # 2. Preview Card & Explicit Consent
    table = Table(
        box=box.ROUNDED,
        border_style="red",
        show_header=True,
        header_style="bold red",
        padding=(0, 1),
    )
    table.add_column("Type", justify="center", width=6)
    table.add_column("Item Name", style="bold cyan")
    table.add_column("Size", justify="right")
    table.add_column("Location", style="dim")

    total_bytes = 0
    for path, is_dir in target_items:
        name = os.path.basename(path) or path
        icon = "📁" if is_dir else get_file_icon(name, is_dir=False)
        sz = get_item_size(path)
        total_bytes += sz
        loc = os.path.dirname(path)
        table.add_row(icon, name, format_bytes(sz), loc)

    danger_body = (
        "[bold red]⚠️  DANGER: Permanent Deletion[/bold red]\n"
        "The following item(s) will be permanently deleted from your system.\n"
        "[bold yellow]This action CANNOT be undone.[/bold yellow]\n\n"
        f"Total items: [bold]{len(target_items)}[/bold] | Total size: [bold]{format_bytes(total_bytes)}[/bold]"
    )

    console.print()
    console.print(
        Panel(
            danger_body,
            title="[bold red]Confirm Deletion[/bold red]",
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print(table)
    console.print()

    # Consent Prompt (default No for safety)
    confirmed = Confirm.ask(
        "[bold red]Are you sure you want to permanently delete these items? [y/N][/bold red]",
        default=False,
    )
    if not confirmed:
        console.print("[dim]Deletion cancelled by user. No files were changed.[/dim]")
        return

    # 3. Execute Deletion
    deleted_count = 0
    failed_count = 0
    results: List[Tuple[str, bool, str]] = []

    for path, is_dir in target_items:
        name = os.path.basename(path) or path
        success, msg = delete_single_item(path, is_dir=is_dir, console=console)
        if success:
            deleted_count += 1
            results.append((name, True, msg))
        else:
            failed_count += 1
            results.append((name, False, msg))

    # 4. Final Summary Card
    console.print()
    res_table = Table(box=box.SIMPLE, show_header=False)
    res_table.add_column("Status", width=4)
    res_table.add_column("Name", style="bold")
    res_table.add_column("Result")

    for name, success, msg in results:
        status_icon = "✔" if success else "✖"
        status_color = "green" if success else "red"
        res_table.add_row(
            f"[{status_color}]{status_icon}[/{status_color}]",
            name,
            f"[{status_color}]{msg}[/{status_color}]",
        )

    summary_panel = Panel(
        res_table,
        title=f"[bold green]Deleted {deleted_count} of {len(target_items)} Item(s)[/bold green]"
        if failed_count == 0
        else f"[bold yellow]Deleted {deleted_count}, Skipped/Failed {failed_count}[/bold yellow]",
        border_style="green" if failed_count == 0 else "yellow",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(summary_panel)
