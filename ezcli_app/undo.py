"""Undo engine and history log for EasyCLI v0.2."""

import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DATA_DIR = os.path.expanduser("~/.local/share/ezcli")
UNDO_FILE = os.path.join(DATA_DIR, "undo.json")


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_undo_history() -> List[Dict[str, Any]]:
    """Load list of undo operations from JSON."""
    ensure_data_dir()
    if not os.path.isfile(UNDO_FILE):
        return []
    try:
        with open(UNDO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_undo_history(history: List[Dict[str, Any]]) -> None:
    """Save undo history list to JSON."""
    ensure_data_dir()
    try:
        with open(UNDO_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def record_operation(
    action: str,
    items: List[Dict[str, Any]],
    description: str = "",
) -> Dict[str, Any]:
    """
    Record an operation into the undo log.
    items format: list of {"src": ..., "dst": ..., "is_dir": bool, "created_at_dst": bool}
    """
    entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "action": action,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description or f"{action.capitalize()} {len(items)} items",
        "items": items,
    }
    history = load_undo_history()
    history.append(entry)
    # Keep last 50 operations
    save_undo_history(history[-50:])
    return entry


def peek_last_operation() -> Optional[Dict[str, Any]]:
    """Inspect the most recent operation without removing it."""
    history = load_undo_history()
    return history[-1] if history else None


def pop_last_operation() -> Optional[Dict[str, Any]]:
    """Remove and return the most recent operation."""
    history = load_undo_history()
    if not history:
        return None
    last = history.pop()
    save_undo_history(history)
    return last


def execute_undo(entry: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """
    Revert an operation:
    - For 'move': moves items back from dst to src.
    - For 'copy': deletes ONLY files created at dst that did not previously exist.
    Returns (success, message, reverted_items).
    """
    action = entry.get("action")
    items = entry.get("items", [])
    reverted: List[str] = []
    errors: List[str] = []

    if action == "move":
        for item in reversed(items):
            src = item.get("src")
            dst = item.get("dst")
            if not dst or not src:
                continue

            if os.path.exists(dst):
                try:
                    # Ensure parent of src exists
                    os.makedirs(os.path.dirname(os.path.abspath(src)), exist_ok=True)
                    shutil.move(dst, src)
                    reverted.append(f"Moved back: {os.path.basename(dst)} -> {src}")
                except Exception as e:
                    errors.append(f"Failed to move {dst} back to {src}: {e}")
            else:
                errors.append(f"File '{dst}' no longer exists at destination.")

    elif action == "copy":
        for item in reversed(items):
            dst = item.get("dst")
            created = item.get("created_at_dst", True)
            is_dir = item.get("is_dir", False)

            if not dst or not created:
                # Never delete files that pre-existed before copy!
                continue

            if os.path.exists(dst):
                try:
                    if is_dir and os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                    reverted.append(f"Removed copied file: {dst}")
                except Exception as e:
                    errors.append(f"Failed to remove {dst}: {e}")

    else:
        return False, f"Unknown action '{action}' in undo log.", []

    if errors and not reverted:
        return False, "Undo failed:\n" + "\n".join(errors), []

    msg = f"Successfully reverted {len(reverted)} items."
    if errors:
        msg += f" (with {len(errors)} warnings)"
    return True, msg, reverted
