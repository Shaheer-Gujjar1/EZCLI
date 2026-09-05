"""CLI handler and direct argument validation for 'ez edit-file'."""

import os
import sys
from typing import Any, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .elevation import elevated_file_read
from .explorer.explorer_app import run_file_picker
from .editor.editor_app import run_mini_editor


BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svgz", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".xz", ".bz2", ".7z", ".iso",
    ".exe", ".bin", ".deb", ".rpm", ".so", ".dylib", ".class", ".pyc", ".o",
    ".mp3", ".mp4", ".wav", ".mkv", ".avi", ".mov", ".flac",
    ".sqlite", ".sqlite3", ".db",
}


def is_binary_file(path: str) -> bool:
    """Return True if path appears to be a binary non-text file."""
    _, ext = os.path.splitext(path.lower())
    if ext in BINARY_EXTENSIONS:
        return True

    if not os.path.exists(path) or os.path.isdir(path):
        return False

    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
            if b"\x00" in chunk:
                return True
            # Attempt decode
            try:
                chunk.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    chunk.decode("latin-1")
                except UnicodeDecodeError:
                    return True
        return False
    except Exception:
        return False


def validate_direct_edit_target(raw_target: str, cwd: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
    """
    Validate direct edit target.
    Enforces that direct editing is strictly scoped to the current working directory.
    Subfolder paths (e.g. 'sub/file.txt' or '../file.txt') are rejected with guidance.
    """
    base_dir = os.path.abspath(cwd or os.getcwd())
    target = (raw_target or "").strip()

    if not target or target == "choose-directory":
        return True, "choose-directory", None

    # Check for subfolder paths or parent traversal
    dirname = os.path.dirname(target)
    if dirname not in ("", "."):
        msg = (
            f"Direct file editing is restricted to files in your current directory.\n\n"
            f"You provided: [bold cyan]{raw_target}[/bold cyan]\n"
            f"To navigate folders and edit files anywhere, please run:\n"
            f"  [bold green]ez edit-file choose-directory[/bold green]"
        )
        return False, "", msg

    filename = os.path.basename(target)
    full_path = os.path.abspath(os.path.join(base_dir, filename))

    # Reject directories
    if os.path.isdir(full_path):
        msg = (
            f"Cannot edit '[bold cyan]{filename}[/bold cyan]': it is a directory.\n"
            f"Please specify a text or code file, or run [bold green]ez edit-file choose-directory[/bold green]."
        )
        return False, "", msg

    # Reject binary files
    if os.path.exists(full_path) and is_binary_file(full_path):
        msg = (
            f"Cannot edit binary file '[bold cyan]{filename}[/bold cyan]'.\n"
            f"EasyCLI Mini Editor is designed for text and code files only."
        )
        return False, "", msg

    return True, full_path, None


def run_cli_edit_file(args: Any, console: Optional[Console] = None) -> None:
    """Execute 'ez edit-file' subcommand."""
    c = console or Console()

    # Determine target parameter
    raw_target = ""
    if hasattr(args, "target") and args.target:
        raw_target = args.target
    elif hasattr(args, "folder") and args.folder:
        raw_target = args.folder
    elif hasattr(args, "name") and args.name:
        raw_target = args.name

    raw_target = raw_target.strip()

    # 1. Visual picker mode
    if not raw_target or raw_target == "choose-directory":
        c.print("[dim]Opening visual file picker to choose a text/code file to edit...[/dim]\n")
        selected_file = run_file_picker(initial_dir=".")
        if not selected_file:
            c.print("\n[yellow]File selection cancelled. No file was opened.[/yellow]")
            return

        target_path = os.path.abspath(selected_file)
        if os.path.isdir(target_path):
            c.print(Panel(
                f"Selected item '[bold cyan]{os.path.basename(target_path)}[/bold cyan]' is a directory.\n"
                f"Please choose a text or code file.",
                title="[bold yellow]Invalid Selection[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            ))
            return

        if is_binary_file(target_path):
            c.print(Panel(
                f"Cannot edit binary file '[bold cyan]{os.path.basename(target_path)}[/bold cyan]'.\n"
                f"EasyCLI Mini Editor is designed for text and code files only.",
                title="[bold yellow]Binary File Detected[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            ))
            return
    else:
        # 2. Direct edit in current directory
        is_valid, resolved_path, err_msg = validate_direct_edit_target(raw_target)
        if not is_valid:
            c.print(Panel(
                err_msg or "Invalid file target.",
                title="[bold red]Editing Restricted[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            ))
            return
        target_path = resolved_path

    # 3. Read content and handle permissions / new file state
    initial_content = ""
    is_new_file = False
    is_admin = False

    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                initial_content = f.read()
        except PermissionError:
            # File exists but cannot be read by normal user (e.g. root-only read)
            c.print(f"\n[bold yellow]🔒 Admin rights are required to open '[white]{target_path}[/white]'.[/bold yellow]")
            if not Confirm.ask("   [bold cyan]Read with administrator rights?[/bold cyan]", default=True, console=c):
                c.print("[yellow]Elevation cancelled. File was not opened.[/yellow]")
                return

            success, content, err = elevated_file_read(
                path=target_path,
                reason=f"Read protected file '{target_path}'",
                console=c,
            )
            if not success or content is None:
                c.print(f"[bold red]Failed to read file with admin rights: {err}[/bold red]")
                return
            initial_content = content
            is_admin = True
    else:
        is_new_file = True

    # 4. Launch the Mini Editor
    run_mini_editor(
        file_path=target_path,
        initial_content=initial_content,
        is_new_file=is_new_file,
        is_admin=is_admin,
    )
