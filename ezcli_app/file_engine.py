"""Safe File Operations Engine (Copy, Move, Verification, Conflict Policy) for EasyCLI v0.2."""

import hashlib
import os
import shutil
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .collectors import format_bytes
from .undo import record_operation


def compute_sha256(filepath: str) -> str:
    """Calculate SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_unique_destination_name(dst_path: str) -> str:
    """Generate a non-colliding filename like 'file (1).txt'."""
    if not os.path.exists(dst_path):
        return dst_path

    parent = os.path.dirname(dst_path)
    base = os.path.basename(dst_path)
    name, ext = os.path.splitext(base)

    counter = 1
    while True:
        candidate = os.path.join(parent, f"{name} ({counter}){ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def scan_source_items(sources: List[str]) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """
    Scan list of source paths.
    Returns (item_records, total_bytes, errors).
    """
    records: List[Dict[str, Any]] = []
    total_bytes = 0
    errors: List[str] = []

    for s in sources:
        abs_s = os.path.abspath(os.path.expanduser(s))
        if not os.path.exists(abs_s):
            errors.append(f"Source does not exist: {s}")
            continue

        try:
            is_dir = os.path.isdir(abs_s)
            size = 0
            if is_dir:
                for root, _, files in os.walk(abs_s):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            size += os.path.getsize(fp)
                        except Exception:
                            pass
            else:
                size = os.path.getsize(abs_s)

            total_bytes += size
            records.append({
                "src": abs_s,
                "name": os.path.basename(abs_s),
                "is_dir": is_dir,
                "size_bytes": size,
                "size_str": format_bytes(size),
            })
        except Exception as e:
            errors.append(f"Error reading {s}: {e}")

    return records, total_bytes, errors


def preview_file_operation(
    action: str,
    sources: List[str],
    destination: str,
) -> Dict[str, Any]:
    """Generate preview of a copy or move operation before execution."""
    raw_dst = os.path.abspath(os.path.expanduser(destination))
    items, total_bytes, errors = scan_source_items(sources)

    is_single_rename = (
        len(items) == 1
        and not items[0]["is_dir"]
        and not destination.endswith(os.sep)
        and not os.path.isdir(raw_dst)
    )

    collisions: List[Dict[str, str]] = []
    for item in items:
        target = raw_dst if is_single_rename else os.path.join(raw_dst, item["name"])
        if os.path.exists(target):
            collisions.append({
                "src": item["src"],
                "target": target,
                "name": os.path.basename(target),
            })

    return {
        "action": action,
        "items": items,
        "count": len(items),
        "total_bytes": total_bytes,
        "total_size_str": format_bytes(total_bytes),
        "destination": raw_dst,
        "is_single_rename": is_single_rename,
        "collisions": collisions,
        "errors": errors,
    }


def is_destination_protected(destination: str) -> bool:
    """Return True if destination path (or closest existing parent) is not writable by current user."""
    from .elevation import is_root
    if is_root():
        return False
    abs_dst = os.path.abspath(os.path.expanduser(destination))
    curr = abs_dst
    while not os.path.exists(curr):
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return not os.access(curr, os.W_OK)


def execute_file_operation(
    action: str,  # "copy" or "move"
    sources: List[str],
    destination: str,
    conflict_policy: str = "ask",  # "ask", "skip", "overwrite", "rename"
    prompt_callback: Optional[Callable[[str], str]] = None,
    progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None,
    is_admin: bool = False,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Execute copy or move with conflict resolution, integrity checks, and undo logging.
    Supports elevated execution via privileged helper when is_admin=True or protected destination.
    Returns (success, message, executed_items).
    """
    from .elevation import elevated_file_copy, elevated_file_move, elevated_make_dir

    raw_dst = os.path.abspath(os.path.expanduser(destination))
    items, total_bytes, errors = scan_source_items(sources)
    if not items:
        return False, "No valid source items to process.", []

    needs_elevation = is_admin or is_destination_protected(raw_dst)

    is_single_rename = (
        len(items) == 1
        and not items[0]["is_dir"]
        and not destination.endswith(os.sep)
        and not os.path.isdir(raw_dst)
    )

    if is_single_rename:
        parent_dir = os.path.dirname(raw_dst)
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except PermissionError:
            if needs_elevation:
                elevated_make_dir(parent_dir)
            else:
                return False, f"Permission denied creating directory '{parent_dir}'. Admin rights required.", []
        except Exception as e:
            return False, f"Cannot create directory '{parent_dir}': {e}", []
    else:
        if not os.path.isdir(raw_dst):
            try:
                os.makedirs(raw_dst, exist_ok=True)
            except PermissionError:
                if needs_elevation:
                    elevated_make_dir(raw_dst)
                else:
                    return False, f"Permission denied creating destination directory '{raw_dst}'. Admin rights required.", []
            except Exception as e:
                return False, f"Cannot create destination directory '{raw_dst}': {e}", []

    executed: List[Dict[str, Any]] = []
    processed_bytes = 0
    total_items = len(items)

    try:
        check_dir = os.path.dirname(raw_dst) if is_single_rename else raw_dst
        dst_dev = os.stat(check_dir).st_dev
    except Exception:
        dst_dev = None

    for idx, item in enumerate(items, 1):
        src = item["src"]
        name = item["name"]
        is_dir = item["is_dir"]
        target = raw_dst if is_single_rename else os.path.join(raw_dst, name)
        existed_before = os.path.exists(target)

        # Handle conflict
        if existed_before:
            decision = conflict_policy.lower()
            if decision == "ask" and prompt_callback:
                decision = prompt_callback(name)

            if decision in ("abort", "q"):
                return False, "Operation cancelled by user.", executed
            elif decision == "skip":
                continue
            elif decision == "rename":
                target = get_unique_destination_name(target)
                existed_before = False
            elif decision == "overwrite":
                pass
            else:
                # Default fallback is skip
                continue

        if progress_callback:
            progress_callback(idx, total_items, name, processed_bytes, total_bytes)

        # Perform Action
        try:
            if action == "copy":
                if needs_elevation:
                    success, err = elevated_file_copy(src, target, is_dir=is_dir, skip_explanation=True)
                    if not success:
                        return False, f"Elevated copy failed: {err}", executed
                else:
                    if is_dir:
                        shutil.copytree(src, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, target)

                executed.append({
                    "src": src,
                    "dst": target,
                    "is_dir": is_dir,
                    "created_at_dst": not existed_before,
                })

            elif action == "move":
                if needs_elevation:
                    success, err = elevated_file_move(src, target, skip_explanation=True)
                    if not success:
                        return False, f"Elevated move failed: {err}", executed
                else:
                    src_dev = os.stat(src).st_dev if os.path.exists(src) else None
                    is_cross_fs = (src_dev is not None and dst_dev is not None and src_dev != dst_dev)

                    if is_cross_fs:
                        # Cross-filesystem move: copy first, verify checksum, then delete source
                        if is_dir:
                            shutil.copytree(src, target, dirs_exist_ok=True)
                            shutil.rmtree(src)
                        else:
                            shutil.copy2(src, target)
                            # Verify integrity
                            src_chk = compute_sha256(src)
                            dst_chk = compute_sha256(target)
                            if src_chk != dst_chk:
                                # Integrity verification failed! Abort deleting source
                                if os.path.exists(target):
                                    os.remove(target)
                                return False, f"Integrity check failed moving '{name}'. Source preserved.", executed
                            os.remove(src)
                    else:
                        # Same-filesystem move: atomic move/rename
                        shutil.move(src, target)

                executed.append({
                    "src": src,
                    "dst": target,
                    "is_dir": is_dir,
                    "created_at_dst": not existed_before,
                })

            processed_bytes += item["size_bytes"]

        except Exception as e:
            return False, f"Error processing '{name}': {e}", executed

    if progress_callback:
        progress_callback(total_items, total_items, "Done", total_bytes, total_bytes)

    # Record in undo log
    if executed:
        record_operation(action, executed, f"{action.capitalize()} {len(executed)} item(s) to {raw_dst}")

    msg = f"Successfully {action}d {len(executed)} item(s) to '{raw_dst}'."
    return True, msg, executed
