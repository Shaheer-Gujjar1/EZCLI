"""Core Extraction Engine for EasyCLI (ez extract-here and ez extract).

Supports .zip, .tar.gz, .tar.xz, .tar.bz2, .tar, and .7z formats with
safe path extraction safeguards (Zip Slip prevention), byte-accurate progress tracking,
and multi-archive inspection.
"""

import os
import shutil
import subprocess
import tarfile
import time
import zipfile
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .file_engine import normalize_target_args

SUPPORTED_EXTRACT_EXTENSIONS = (
    ".zip",
    ".tar.gz",
    ".tgz",
    ".tar.xz",
    ".txz",
    ".tar.bz2",
    ".tbz2",
    ".tar",
    ".7z",
)


def get_archive_format(filepath: str) -> Optional[str]:
    """Identify the archive format extension from filepath."""
    lower = filepath.lower()
    for ext in (
        ".tar.gz",
        ".tar.xz",
        ".tar.bz2",
        ".tgz",
        ".txz",
        ".tbz2",
        ".zip",
        ".tar",
        ".7z",
    ):
        if lower.endswith(ext):
            return ext
    return None


def validate_extract_target(
    raw_target: str,
    cwd: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Validate a target archive file for the direct 'ez extract-here' command.

    Rules:
    - Direct extraction is strictly restricted to archive files in the current working directory.
    - No subfolder paths allowed (e.g. 'sub/archive.zip' or '../archive.tar.gz').
    - Target must exist and be an archive file.

    Returns:
        (is_valid, error_msg, resolved_abs_path)
    """
    cleaned = (raw_target or "").strip()
    if not cleaned:
        return False, "Archive name cannot be empty.", ""

    effective_cwd = os.path.abspath(cwd or os.getcwd())

    # Check for internal slashes or parent traversal
    has_internal_slash = ("/" in cleaned.rstrip("/")) or ("\\" in cleaned.rstrip("\\"))
    if has_internal_slash or cleaned in (".", ".."):
        msg = (
            "Direct extraction ('ez extract-here') is restricted to archives in your current directory.\n\n"
            f"You provided: [bold cyan]{raw_target}[/bold cyan]\n"
            "To extract archives in subfolders or choose a custom destination, please run:\n"
            "  [bold green]ez extract choose-directory[/bold green]"
        )
        return False, msg, ""

    name = cleaned.rstrip("/\\")
    target_path = os.path.join(effective_cwd, name)

    if not os.path.exists(target_path):
        return (
            False,
            f"Cannot find '[bold cyan]{raw_target}[/bold cyan]': No such file in current directory.",
            "",
        )

    if os.path.isdir(target_path):
        return (
            False,
            f"'[bold cyan]{raw_target}[/bold cyan]' is a directory, not an archive file.",
            "",
        )

    fmt = get_archive_format(target_path)
    if not fmt:
        exts_str = ", ".join(SUPPORTED_EXTRACT_EXTENSIONS)
        return (
            False,
            f"Unsupported archive format for '[bold cyan]{raw_target}[/bold cyan]'.\n"
            f"Supported formats: {exts_str}",
            "",
        )

    return True, "", target_path


def sanitize_member_path(dest_dir: str, member_name: str) -> str:
    """Ensure member path does not escape destination directory (Zip Slip protection)."""
    dest_abs = os.path.abspath(dest_dir)

    # Disallow absolute paths
    if os.path.isabs(member_name) or member_name.startswith(("/", "\\")):
        raise ValueError(
            f"Security hazard: Archive contains absolute path '{member_name}' escaping destination directory."
        )

    target_path = os.path.abspath(os.path.join(dest_abs, member_name))

    # Must be inside dest_abs or equal to dest_abs
    if not (target_path == dest_abs or target_path.startswith(dest_abs + os.sep)):
        raise ValueError(
            f"Security hazard: Archive contains traversal path '{member_name}' escaping destination directory."
        )
    return target_path


def inspect_archive(archive_path: str) -> Dict[str, Any]:
    """Inspect archive contents without full extraction.

    Returns:
        {
            "format": str,
            "file_count": int,
            "dir_count": int,
            "total_bytes": int,
            "members": List[Dict[str, Any]],
        }
    """
    abs_path = os.path.abspath(archive_path)
    fmt = get_archive_format(abs_path)
    if not fmt:
        raise ValueError(f"Unknown archive format for '{archive_path}'")

    file_count = 0
    dir_count = 0
    total_bytes = 0
    members: List[Dict[str, Any]] = []

    if fmt == ".zip":
        with zipfile.ZipFile(abs_path, "r") as zf:
            for info in zf.infolist():
                is_dir = info.is_dir()
                if is_dir:
                    dir_count += 1
                else:
                    file_count += 1
                    total_bytes += info.file_size
                members.append({
                    "name": info.filename,
                    "is_dir": is_dir,
                    "size": info.file_size,
                })
    elif fmt in (".tar.gz", ".tar.xz", ".tar.bz2", ".tgz", ".txz", ".tbz2", ".tar"):
        with tarfile.open(abs_path, "r:*") as tf:
            for member in tf.getmembers():
                is_dir = member.isdir()
                if is_dir:
                    dir_count += 1
                else:
                    file_count += 1
                    total_bytes += member.size
                members.append({
                    "name": member.name,
                    "is_dir": is_dir,
                    "size": member.size,
                })
    elif fmt == ".7z":
        bin_7z = shutil.which("7z") or shutil.which("7za")
        if bin_7z:
            proc = subprocess.run(
                [bin_7z, "l", "-ba", abs_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    parts = line.split(maxsplit=5)
                    if len(parts) >= 6:
                        # parts: Date, Time, Attr, Size, Compressed, Name
                        attr = parts[2]
                        try:
                            sz = int(parts[3])
                        except ValueError:
                            sz = 0
                        name = parts[5]
                        is_dir = "D" in attr
                        if is_dir:
                            dir_count += 1
                        else:
                            file_count += 1
                            total_bytes += sz
                        members.append({
                            "name": name,
                            "is_dir": is_dir,
                            "size": sz,
                        })
    return {
        "format": fmt,
        "file_count": file_count,
        "dir_count": dir_count,
        "total_bytes": total_bytes,
        "members": members,
    }


def extract_archive(
    archive_path: str,
    dest_dir: str,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Extract an archive file safely into dest_dir with progress tracking.

    Args:
        archive_path: Path to archive file (.zip, .tar.*, .7z).
        dest_dir: Destination directory path.
        progress_callback: Optional callback(current_item, total_items, item_name, current_bytes, total_bytes).

    Returns:
        (success, error_or_success_message, stats_dict)
    """
    abs_archive = os.path.abspath(archive_path)
    abs_dest = os.path.abspath(dest_dir)

    if not os.path.exists(abs_archive):
        return False, f"Archive file '{archive_path}' does not exist.", {}

    fmt = get_archive_format(abs_archive)
    if not fmt:
        return False, f"Unsupported archive format for '{archive_path}'.", {}

    os.makedirs(abs_dest, exist_ok=True)
    start_time = time.time()

    try:
        summary = inspect_archive(abs_archive)
    except Exception as e:
        return False, f"Cannot read archive '{os.path.basename(archive_path)}': {str(e)}", {}

    members = summary["members"]
    total_items = len(members)
    total_bytes = summary["total_bytes"]
    processed_bytes = 0

    try:
        if fmt == ".zip":
            _extract_zip(abs_archive, abs_dest, members, total_bytes, progress_callback)
        elif fmt in (".tar.gz", ".tar.xz", ".tar.bz2", ".tgz", ".txz", ".tbz2", ".tar"):
            _extract_tar(abs_archive, abs_dest, members, total_bytes, progress_callback)
        elif fmt == ".7z":
            _extract_7z(abs_archive, abs_dest, members, total_bytes, progress_callback)
        else:
            return False, f"Unhandled archive format '{fmt}'.", {}

        elapsed = time.time() - start_time
        stats = {
            "archive_path": abs_archive,
            "archive_name": os.path.basename(abs_archive),
            "dest_dir": abs_dest,
            "format": fmt,
            "file_count": summary["file_count"],
            "dir_count": summary["dir_count"],
            "total_items": total_items,
            "extracted_bytes": total_bytes,
            "elapsed_seconds": elapsed,
        }
        return True, "Archive extracted successfully!", stats

    except Exception as e:
        return False, f"Extraction failed: {str(e)}", {}


def _extract_zip(
    archive_path: str,
    dest_dir: str,
    members: List[Dict[str, Any]],
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Extract ZIP archive safely with member sanitization."""
    processed_bytes = 0
    total_items = len(members)

    with zipfile.ZipFile(archive_path, "r") as zf:
        for idx, info in enumerate(zf.infolist(), start=1):
            target_path = sanitize_member_path(dest_dir, info.filename)

            if info.is_dir():
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(info) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                processed_bytes += info.file_size

            if progress_callback:
                progress_callback(idx, total_items, info.filename, processed_bytes, total_bytes)


def _extract_tar(
    archive_path: str,
    dest_dir: str,
    members: List[Dict[str, Any]],
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Extract TAR archive safely with member sanitization."""
    processed_bytes = 0
    total_items = len(members)

    with tarfile.open(archive_path, "r:*") as tf:
        for idx, member in enumerate(tf.getmembers(), start=1):
            target_path = sanitize_member_path(dest_dir, member.name)

            if member.isdir():
                os.makedirs(target_path, exist_ok=True)
            elif member.isfile():
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                f = tf.extractfile(member)
                if f:
                    with f, open(target_path, "wb") as dst:
                        shutil.copyfileobj(f, dst)
                processed_bytes += member.size
            elif member.issym() or member.islnk():
                # Safe link extraction
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                if os.path.lexists(target_path):
                    try:
                        os.remove(target_path)
                    except OSError:
                        pass
                if member.issym():
                    try:
                        os.symlink(member.linkname, target_path)
                    except OSError:
                        pass
                elif member.islnk():
                    link_target = sanitize_member_path(dest_dir, member.linkname)
                    try:
                        os.link(link_target, target_path)
                    except OSError:
                        pass

            if progress_callback:
                progress_callback(idx, total_items, member.name, processed_bytes, total_bytes)


def _extract_7z(
    archive_path: str,
    dest_dir: str,
    members: List[Dict[str, Any]],
    total_bytes: int,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]],
) -> None:
    """Extract 7-Zip archive using system binary."""
    bin_7z = shutil.which("7z") or shutil.which("7za")
    if not bin_7z:
        raise RuntimeError(
            "7-Zip is not installed on this system.\n"
            "Please install it with: sudo apt install p7zip-full"
        )

    if progress_callback:
        progress_callback(0, len(members), "Starting 7-Zip extraction...", 0, total_bytes)

    cmd = [bin_7z, "x", "-y", f"-o{dest_dir}", archive_path]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(f"7z extract failed with code {proc.returncode}: {err}")

    if progress_callback:
        progress_callback(len(members), len(members), "7-Zip extraction completed", total_bytes, total_bytes)
