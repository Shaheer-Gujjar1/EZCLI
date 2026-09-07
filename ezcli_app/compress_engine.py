"""Core Compression Engine for EasyCLI (ez compress).

Supports .zip, .tar.gz, .tar.xz, .7z, and .tar.bz2 formats with direct
current-directory validation, byte-accurate progress tracking, and statistical reporting.
"""

import os
import shutil
import subprocess
import tarfile
import time
import zipfile
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, cast

from .file_engine import normalize_target_args

SUPPORTED_FORMATS = {
    ".zip": {
        "id": "zip",
        "name": "ZIP Archive",
        "icon": "📦",
        "desc": "Fast, universal cross-platform compatibility",
        "mime": "application/zip",
    },
    ".tar.gz": {
        "id": "tar_gz",
        "name": "Gzip Compressed Tarball",
        "icon": "🗜️",
        "desc": "Standard Linux compressed packaging",
        "mime": "application/gzip",
    },
    ".tar.xz": {
        "id": "tar_xz",
        "name": "XZ High-Compression Tarball",
        "icon": "⚡",
        "desc": "Maximum compression ratio, minimal file size",
        "mime": "application/x-xz",
    },
    ".7z": {
        "id": "7z",
        "name": "7-Zip Archive",
        "icon": "🗃️",
        "desc": "Ultra compression ratio with LZMA2 algorithm",
        "mime": "application/x-7z-compressed",
    },
    ".tar.bz2": {
        "id": "tar_bz2",
        "name": "Bzip2 Compressed Tarball",
        "icon": "📦",
        "desc": "High compression for text and logs",
        "mime": "application/x-bzip2",
    },
}


def validate_compress_target(
    raw_target: str,
    cwd: Optional[str] = None,
) -> Tuple[bool, str, str, bool]:
    """Validate a target path for the direct 'ez compress' command.

    Rules:
    - Direct compress is restricted to items in current directory only.
    - No subfolder paths allowed (e.g. 'sub/file.txt' or 'folder/nested/').
    - Trailing slash (e.g. 'my_folder/') indicates folder intent and must be a directory.
    - Non-existent files/folders are reported cleanly.

    Returns:
        (is_valid, error_msg, resolved_abs_path, is_dir)
    """
    cleaned = (raw_target or "").strip()
    if not cleaned:
        return False, "Target name cannot be empty.", "", False

    if cleaned.lower() in ("choose-directory", "choose", "picker", "select"):
        return True, "", "choose-directory", False

    effective_cwd = os.path.abspath(cwd or os.getcwd())

    # Check for internal slashes or parent traversal
    has_internal_slash = ("/" in cleaned.rstrip("/")) or ("\\" in cleaned.rstrip("\\"))
    if has_internal_slash or cleaned in (".", ".."):
        msg = (
            "Direct compress is restricted to items in your current directory.\n\n"
            f"You provided: [bold cyan]{raw_target}[/bold cyan]\n"
            "To select items in subfolders or other locations, please run:\n"
            "  [bold green]ez compress choose-directory[/bold green]"
        )
        return False, msg, "", False

    expects_dir = cleaned.endswith("/") or cleaned.endswith("\\")
    name = cleaned.rstrip("/\\")

    target_path = os.path.join(effective_cwd, name)

    if not os.path.exists(target_path) and not os.path.islink(target_path):
        return (
            False,
            f"Cannot find '[bold cyan]{raw_target}[/bold cyan]': No such file or directory in current directory.",
            "",
            False,
        )

    is_dir = os.path.isdir(target_path) and not os.path.islink(target_path)
    if expects_dir and not is_dir:
        return (
            False,
            f"'[bold cyan]{raw_target}[/bold cyan]' has a trailing slash indicating a folder, but it is a regular file.",
            "",
            False,
        )

    return True, "", target_path, is_dir


def calculate_targets_summary(target_paths: Sequence[str]) -> Dict[str, Any]:
    """Scan targets recursively and gather entry records for compression.

    Returns:
        {
            "total_bytes": int,
            "file_count": int,
            "dir_count": int,
            "entries": List[Tuple[str, str, bool, int]]  # (abs_path, arcname, is_dir, size)
        }
    """
    entries: List[Tuple[str, str, bool, int]] = []
    total_bytes = 0
    file_count = 0
    dir_count = 0

    for path in target_paths:
        abs_p = os.path.abspath(path)
        if not os.path.exists(abs_p) and not os.path.islink(abs_p):
            continue

        parent_dir = os.path.dirname(abs_p)

        if os.path.isdir(abs_p) and not os.path.islink(abs_p):
            # Directory target: include directory itself and all descendants
            base_arc = os.path.basename(abs_p)
            entries.append((abs_p, base_arc, True, 0))
            dir_count += 1

            for root, dirs, files in os.walk(abs_p):
                # Add subdirectories
                for d in dirs:
                    d_path = os.path.join(root, d)
                    arc_name = os.path.relpath(d_path, parent_dir)
                    entries.append((d_path, arc_name, True, 0))
                    dir_count += 1

                # Add files
                for f in files:
                    f_path = os.path.join(root, f)
                    try:
                        f_size = os.path.getsize(f_path)
                    except OSError:
                        f_size = 0
                    arc_name = os.path.relpath(f_path, parent_dir)
                    entries.append((f_path, arc_name, False, f_size))
                    total_bytes += f_size
                    file_count += 1
        else:
            # Regular file or symlink
            try:
                f_size = os.path.getsize(abs_p)
            except OSError:
                f_size = 0
            base_arc = os.path.basename(abs_p)
            entries.append((abs_p, base_arc, False, f_size))
            total_bytes += f_size
            file_count += 1

    return {
        "total_bytes": total_bytes,
        "file_count": file_count,
        "dir_count": dir_count,
        "entries": entries,
    }


def suggest_archive_name(targets: Sequence[str], ext: str = ".zip") -> str:
    """Generate an intelligent default archive name based on targets."""
    if not targets:
        return f"archive{ext}"

    if len(targets) == 1:
        clean = targets[0].rstrip("/\\")
        base = os.path.basename(clean)
        # If single file with extension, strip extension
        name, _ = os.path.splitext(base)
        return f"{name or 'archive'}{ext}"

    return f"archive{ext}"


def compress_targets(
    targets: Sequence[str],
    output_path: str,
    format_type: str,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Compress multiple source targets into an output archive file.

    Args:
        targets: Absolute or relative paths of source files/directories.
        output_path: Destination archive file path.
        format_type: One of ('.zip', '.tar.gz', '.tar.xz', '.7z', '.tar.bz2').
        progress_callback: Optional callback(current_idx, total_items, item_name, current_bytes, total_bytes).

    Returns:
        (success, error_or_success_message, stats_dict)
    """
    fmt = format_type.lower().strip()
    if fmt not in SUPPORTED_FORMATS:
        return False, f"Unsupported compression format '{format_type}'.", {}

    summary = calculate_targets_summary(targets)
    entries = summary["entries"]
    total_bytes = summary["total_bytes"]
    total_items = len(entries)

    if total_items == 0:
        return False, "No valid files or directories found to compress.", {}

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    start_time = time.time()
    processed_bytes = 0

    try:
        if fmt == ".zip":
            _compress_zip(entries, output_path, total_bytes, progress_callback)
        elif fmt in (".tar.gz", ".tar.xz", ".tar.bz2"):
            mode_map = {
                ".tar.gz": "w:gz",
                ".tar.xz": "w:xz",
                ".tar.bz2": "w:bz2",
            }
            _compress_tar(entries, output_path, mode_map[fmt], total_bytes, progress_callback)
        elif fmt == ".7z":
            _compress_7z(targets, output_path, entries, total_bytes, progress_callback)
        else:
            return False, f"Unhandled compression format '{fmt}'.", {}

        elapsed = time.time() - start_time
        compressed_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        saved_bytes = max(0, total_bytes - compressed_size)
        ratio = (saved_bytes / total_bytes * 100.0) if total_bytes > 0 else 0.0

        stats = {
            "output_path": os.path.abspath(output_path),
            "format": SUPPORTED_FORMATS[fmt]["name"],
            "extension": fmt,
            "file_count": summary["file_count"],
            "dir_count": summary["dir_count"],
            "total_items": total_items,
            "uncompressed_bytes": total_bytes,
            "compressed_bytes": compressed_size,
            "saved_bytes": saved_bytes,
            "saved_ratio": ratio,
            "elapsed_seconds": elapsed,
        }
        return True, "Archive created successfully!", stats

    except Exception as e:
        # Clean up partial output file on failure
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        return False, f"Compression failed: {str(e)}", {}


def _compress_zip(
    entries: List[Tuple[str, str, bool, int]],
    output_path: str,
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Create ZIP archive with ZIP_DEFLATED compression."""
    processed_bytes = 0
    total_items = len(entries)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, (path, arcname, is_dir, size) in enumerate(entries, start=1):
            if is_dir:
                zf.write(path, arcname)
            else:
                zf.write(path, arcname)
                processed_bytes += size

            if progress_callback:
                progress_callback(idx, total_items, arcname, processed_bytes, total_bytes)


def _compress_tar(
    entries: List[Tuple[str, str, bool, int]],
    output_path: str,
    tar_mode: str,
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Create tar archive (gzip, xz, or bz2)."""
    processed_bytes = 0
    total_items = len(entries)

    with tarfile.open(output_path, cast(Any, tar_mode)) as tf:
        for idx, (path, arcname, is_dir, size) in enumerate(entries, start=1):
            tf.add(path, arcname=arcname, recursive=False)
            if not is_dir:
                processed_bytes += size

            if progress_callback:
                progress_callback(idx, total_items, arcname, processed_bytes, total_bytes)


def _compress_7z(
    targets: Sequence[str],
    output_path: str,
    entries: List[Tuple[str, str, bool, int]],
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Create 7z archive using system binary (7z or 7za)."""
    bin_7z = shutil.which("7z") or shutil.which("7za")
    if not bin_7z:
        raise RuntimeError(
            "7-Zip is not installed on this system.\n"
            "Please install it with: sudo apt install p7zip-full\n"
            "Or choose .zip, .tar.gz, or .tar.xz instead."
        )

    # Use 7z CLI to create archive
    abs_out = os.path.abspath(output_path)
    # Determine base directory
    first_target = os.path.abspath(targets[0])
    base_dir = os.path.dirname(first_target)

    # Get relative names for targets from base_dir if all share parent, otherwise absolute
    relative_targets: List[str] = []
    all_in_base = True
    for t in targets:
        abs_t = os.path.abspath(t)
        if os.path.dirname(abs_t) != base_dir:
            all_in_base = False
            break
        relative_targets.append(os.path.basename(abs_t))

    cmd = [bin_7z, "a", "-y", "-mx=9", abs_out]
    if all_in_base:
        cmd.extend(relative_targets)
        cwd = base_dir
    else:
        cmd.extend([os.path.abspath(t) for t in targets])
        cwd = None

    if progress_callback:
        progress_callback(0, len(entries), "Starting 7-Zip compression...", 0, total_bytes)

    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"7z command failed with code {proc.returncode}: {err}")

    if progress_callback:
        progress_callback(len(entries), len(entries), "7-Zip completed", total_bytes, total_bytes)
