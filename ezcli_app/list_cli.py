"""
Subcommand 'ez list' - Unified replacement for ls, tree, du, and stat.

Form 1: 'ez list' (no arguments)
- Instant pretty listing of the current directory.
- Emoji icon by file type, name, human-readable size, modified date.
- Hidden files shown by default with subtle visual distinction.
- Folder sizes computed progressively in the background and streamed into output.
- Non-interactive, prints and returns to shell.

Form 2: 'ez list choose-directory'
- Reuses directory picker from choose-directory explorer in pick mode.
- Launches full interactive TUI viewer with flat list vs tree toggle ('t'),
  cycle sorting ('s'), toggle hidden ('h'), and Enter for details card (stat replacement).
"""

import concurrent.futures
import datetime
import grp
import os
import pwd
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .explorer.file_icons import get_file_icon


def format_human_size(size_bytes: int) -> str:
    """Format byte size into clean human-readable string (B, KB, MB, GB)."""
    if size_bytes < 0:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def format_timestamp(ts: Optional[float]) -> str:
    """Format Unix timestamp into friendly YYYY-MM-DD HH:MM string."""
    if not ts or ts < 86400:
        return "-"
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def format_permissions_english(st: Any) -> str:
    """
    Format POSIX permissions into plain English.
    Example: 'You: read+write · Others: read-only'
    """
    if isinstance(st, int):
        mode = st
    elif hasattr(st, "st_mode"):
        mode = st.st_mode
    else:
        try:
            mode = int(st)
        except Exception:
            return "Unknown"

    u_r = bool(mode & stat.S_IRUSR)
    u_w = bool(mode & stat.S_IWUSR)
    u_x = bool(mode & stat.S_IXUSR)

    g_r = bool(mode & stat.S_IRGRP)
    g_w = bool(mode & stat.S_IWGRP)
    g_x = bool(mode & stat.S_IXGRP)

    o_r = bool(mode & stat.S_IROTH)
    o_w = bool(mode & stat.S_IWOTH)
    o_x = bool(mode & stat.S_IXOTH)

    def describe(r: bool, w: bool, x: bool) -> str:
        if r and not w and not x:
            return "read-only"
        if not r and w and not x:
            return "write-only"
        if not r and not w and x:
            return "exec-only"
        parts = []
        if r:
            parts.append("read")
        if w:
            parts.append("write")
        if x:
            parts.append("exec")
        if not parts:
            return "none"
        return "+".join(parts)

    u_desc = describe(u_r, u_w, u_x)
    g_desc = describe(g_r, g_w, g_x)
    o_desc = describe(o_r, o_w, o_x)

    if g_desc == o_desc:
        return f"You: {u_desc} · Others: {o_desc}"
    return f"You: {u_desc} · Group: {g_desc} · Others: {o_desc}"



def calculate_dir_size(dir_path: str, max_items: int = 50000) -> int:
    """Calculate recursive total directory size in bytes, handling errors safely."""
    total = 0
    items_scanned = 0
    try:
        for root, dirs, files in os.walk(dir_path, followlinks=False):
            for f in files:
                items_scanned += 1
                if items_scanned > max_items:
                    return total
                fp = os.path.join(root, f)
                try:
                    total += os.lstat(fp).st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def scan_directory_entries(
    target_dir: str,
    show_hidden: bool = True,
    console: Optional[Console] = None,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    Scan directory entries. If permission is denied, trigger elevated_read_dir flow.
    Returns (success, entries, error_message).
    """
    console = console or Console()
    entries: List[Dict[str, Any]] = []

    try:
        with os.scandir(target_dir) as it:
            for item in it:
                name = item.name
                if not show_hidden and name.startswith("."):
                    continue

                is_hidden = name.startswith(".")
                try:
                    st = item.stat(follow_symlinks=False)
                    is_dir = stat.S_ISDIR(st.st_mode)
                    is_symlink = stat.S_ISLNK(st.st_mode)
                    size = st.st_size if not is_dir else None
                    mtime = st.st_mtime
                except (OSError, PermissionError):
                    is_dir = False
                    is_symlink = False
                    size = None
                    mtime = None

                icon = get_file_icon(name, is_dir=is_dir)
                entries.append({
                    "name": name,
                    "path": os.path.join(target_dir, name),
                    "is_dir": is_dir,
                    "is_symlink": is_symlink,
                    "is_hidden": is_hidden,
                    "size": size,
                    "mtime": mtime,
                    "icon": icon,
                })
        return True, entries, ""
    except PermissionError:
        # Protected folder -> elevation consent flow
        from .elevation import elevated_read_dir
        success, elev_entries, err = elevated_read_dir(
            path=target_dir,
            show_hidden=show_hidden,
            reason=f"Read contents of protected directory '{target_dir}'",
            console=console,
        )
        if success:
            formatted = []
            for e in elev_entries:
                name = e.get("name", "")
                is_dir = e.get("is_dir", False)
                icon = get_file_icon(name, is_dir=is_dir)
                formatted.append({
                    "name": name,
                    "path": os.path.join(target_dir, name),
                    "is_dir": is_dir,
                    "is_symlink": False,
                    "is_hidden": name.startswith("."),
                    "size": e.get("size") if not is_dir else None,
                    "mtime": None,
                    "icon": icon,
                })
            return True, formatted, ""
        return False, [], err or "Permission denied"
    except Exception as e:
        return False, [], str(e)


def build_listing_table(
    target_dir: str,
    entries: List[Dict[str, Any]],
    folder_sizes: Dict[str, str],
    term_width: int,
) -> Table:
    """Build Rich Table for Form 1 CLI listing."""
    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        width=min(term_width, 100),
        padding=(0, 1),
        show_lines=False,
    )
    table.add_column("Type", justify="center", width=4, no_wrap=True)
    table.add_column("Name", style="bold white", ratio=4, overflow="ellipsis")
    table.add_column("Size", justify="right", style="green", width=12, no_wrap=True)
    table.add_column("Modified", justify="center", style="cyan", width=18, no_wrap=True)

    for item in entries:
        icon = item["icon"]
        name = item["name"]
        is_hidden = item["is_hidden"]
        is_dir = item["is_dir"]

        # Hidden files visual distinction: subtle dimmed styling
        if is_hidden:
            name_display = f"[dim]{escape(name)}[/dim]"
            icon_display = f"[dim]{icon}[/dim]"
        elif is_dir:
            name_display = f"[bold blue]{escape(name)}/[/bold blue]"
            icon_display = icon
        else:
            name_display = escape(name)
            icon_display = icon

        # Size formatting
        if is_dir:
            size_display = folder_sizes.get(item["path"], "[dim]calculating...[/dim]")
        else:
            size_bytes = item["size"]
            size_display = format_human_size(size_bytes) if size_bytes is not None else "-"
            if is_hidden:
                size_display = f"[dim]{size_display}[/dim]"

        # Date formatting
        date_display = format_timestamp(item["mtime"])
        if is_hidden:
            date_display = f"[dim]{date_display}[/dim]"

        table.add_row(icon_display, name_display, size_display, date_display)

    return table


def run_form1_instant_listing(console: Console, target_dir: Optional[str] = None) -> None:
    """
    Form 1: 'ez list' with no arguments.
    Instant pretty listing of the current directory, with progressive background folder sizing.
    """
    target = os.path.abspath(target_dir or os.getcwd())
    term_width = console.width or 80

    success, entries, err = scan_directory_entries(target, show_hidden=True, console=console)
    if not success:
        console.print()
        console.print(
            Panel(
                f"[bold red]Cannot read directory '{escape(target)}':[/bold red] {err}",
                title="❌ [bold red]Access Denied[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        sys.exit(1)

    # Empty folder handling
    if not entries:
        console.print()
        console.print(
            Panel(
                f"[bold yellow]📁 Folder is empty:[/bold yellow] [cyan]{escape(target)}[/cyan]\n\n"
                "[dim]No files or hidden items found in this directory.[/dim]",
                title="📁 [bold cyan]Empty Directory[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        return

    # Sort entries: directories first, then files, alphabetical case-insensitive
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

    # Track folder sizes
    folder_sizes: Dict[str, str] = {}
    dir_paths = [e["path"] for e in entries if e["is_dir"]]

    # Header stats
    file_count = sum(1 for e in entries if not e["is_dir"])
    dir_count = sum(1 for e in entries if e["is_dir"])
    hidden_count = sum(1 for e in entries if e["is_hidden"])

    stats_parts = [
        f"[bold white]{len(entries)} items[/bold white]",
        f"[blue]{dir_count} folder{'s' if dir_count != 1 else ''}[/blue]",
        f"[green]{file_count} file{'s' if file_count != 1 else ''}[/green]",
    ]
    if hidden_count:
        stats_parts.append(f"[dim]{hidden_count} hidden[/dim]")

    console.print()
    console.print(f"[bold cyan]📁 {escape(target)}[/bold cyan]  [dim]({ ' · '.join(stats_parts) })[/dim]")

    # If no directories or non-interactive/redirected stdout: print table immediately
    is_interactive_tty = sys.stdout.isatty()

    if not dir_paths or not is_interactive_tty:
        # Compute sizes synchronously or show '-' if non-interactive
        for dp in dir_paths:
            folder_sizes[dp] = format_human_size(calculate_dir_size(dp))
        table = build_listing_table(target, entries, folder_sizes, term_width)
        console.print(table)
        return

    # Interactive TTY: Background calculation streamed progressively via Rich Live
    initial_table = build_listing_table(target, entries, folder_sizes, term_width)

    with Live(initial_table, console=console, refresh_per_second=10) as live:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, max(1, len(dir_paths)))) as executor:
            future_to_path = {executor.submit(calculate_dir_size, dp): dp for dp in dir_paths}
            for future in concurrent.futures.as_completed(future_to_path):
                dp = future_to_path[future]
                try:
                    sz = future.result()
                    folder_sizes[dp] = format_human_size(sz)
                except Exception:
                    folder_sizes[dp] = "-"
                live.update(build_listing_table(target, entries, folder_sizes, term_width))


def run_form2_choose_directory_tui(console: Console) -> None:
    """
    Form 2: 'ez list choose-directory'.
    Opens visual directory picker to pick any folder, prints its pretty listing directly
    to the terminal (like Form 1), and provides an option to open the full interactive TUI inspector.
    """
    from .main import check_textual_installed
    if not check_textual_installed(console):
        sys.exit(1)

    from .explorer.explorer_app import run_destination_picker
    chosen_dir = run_destination_picker(initial_dir=os.getcwd(), is_admin=False)
    if not chosen_dir:
        console.print("[dim]Directory selection cancelled.[/dim]")
        return

    chosen_dir = os.path.abspath(chosen_dir)

    # 1. Print pretty listing of the chosen directory directly to the shell
    run_form1_instant_listing(target_dir=chosen_dir, console=console)

    # 2. Offer to launch full interactive TUI inspector if running interactively
    if sys.stdout.isatty() and sys.stdin.isatty():
        try:
            from rich.prompt import Prompt
            choice = Prompt.ask(
                "\n[dim]Press[/dim] [bold cyan]i[/bold cyan] [dim]to open interactive TUI inspector (tree view, sort, stat details), or press[/dim] [bold]Enter[/bold] [dim]to return to shell[/dim]",
                default="",
                show_default=False,
                console=console,
            ).strip().lower()
            if choice in ("i", "inspector", "tui", "tree"):
                from .list_tui import run_list_tui_app
                run_list_tui_app(chosen_dir)
        except (KeyboardInterrupt, EOFError):
            console.print()



def run_cli_list(raw_args: Optional[List[str]] = None, console: Optional[Console] = None) -> None:
    """
    Main entrypoint for 'ez list'.
    Validates arguments: strictly NO path arguments or flags allowed anywhere.
    Only allows no argument (Form 1) or 'choose-directory' (Form 2).
    """
    console = console or Console()
    args = raw_args or []

    # Filter out empty strings
    clean_args = [a.strip() for a in args if a.strip()]

    # Form 1: No arguments -> instant pretty listing of current directory
    if not clean_args:
        run_form1_instant_listing(console=console)
        return

    # Form 2: choose-directory -> visual picker + interactive TUI viewer
    if len(clean_args) == 1 and clean_args[0].lower() in ("choose-directory", "choose", "picker"):
        run_form2_choose_directory_tui(console=console)
        return

    # Any other arguments (path or flags) -> Reject with informative error panel
    bad_arg = clean_args[0]
    panel_width = max(45, min(console.width, 85))
    console.print()
    console.print(
        Panel(
            f"[bold red]Error: 'ez list' does not accept path arguments like '[white]{escape(bad_arg)}[/white]'.[/bold red]\n\n"
            "[bold white]In EasyCLI, directories are always selected visually without typing raw paths:[/bold white]\n"
            "  • Run [bold green]ez list[/bold green] for an instant listing of the current directory.\n"
            "  • Run [bold green]ez list choose-directory[/bold green] to visually pick any folder and explore.",
            title="❌ [bold red]Path Arguments Not Allowed[/bold red]",
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2),
            width=panel_width,
        )
    )
    sys.exit(1)
