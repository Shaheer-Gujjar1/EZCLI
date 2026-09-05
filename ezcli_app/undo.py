"""Clipboard, Undo, and Redo history engine for EasyCLI v0.2."""

import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PRIMARY_DATA_DIR = os.path.expanduser("~/.local/share/ez")
LEGACY_DATA_DIR = os.path.expanduser("~/.local/share/ezcli")
DATA_DIR = PRIMARY_DATA_DIR
CLIPBOARD_FILE = os.path.join(DATA_DIR, "clipboard.json")
UNDO_FILE = os.path.join(DATA_DIR, "undo.json")
REDO_FILE = os.path.join(DATA_DIR, "redo.json")


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(LEGACY_DATA_DIR):
        for fname in ("clipboard.json", "undo.json", "redo.json"):
            old_f = os.path.join(LEGACY_DATA_DIR, fname)
            new_f = os.path.join(DATA_DIR, fname)
            if os.path.exists(old_f) and not os.path.exists(new_f):
                try:
                    shutil.copy2(old_f, new_f)
                except Exception:
                    pass


# ==============================================================================
# Clipboard Management
# ==============================================================================
def set_clipboard(action: str, items: List[str]) -> Dict[str, Any]:
    """Store staged items and action ('copy' or 'move') in the clipboard."""
    ensure_data_dir()
    entry = {
        "action": action,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": [os.path.abspath(os.path.expanduser(p)) for p in items],
    }
    try:
        with open(CLIPBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
    except Exception:
        pass
    return entry


def get_clipboard() -> Optional[Dict[str, Any]]:
    """Retrieve currently staged items from the clipboard."""
    ensure_data_dir()
    if not os.path.isfile(CLIPBOARD_FILE):
        return None
    try:
        with open(CLIPBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data.get("items"):
                return data
    except Exception:
        pass
    return None


def clear_clipboard() -> None:
    """Clear the clipboard."""
    ensure_data_dir()
    if os.path.isfile(CLIPBOARD_FILE):
        try:
            os.remove(CLIPBOARD_FILE)
        except Exception:
            pass


# ==============================================================================
# Undo & Redo Stacks
# ==============================================================================
def _load_stack(filepath: str) -> List[Dict[str, Any]]:
    ensure_data_dir()
    if not os.path.isfile(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_stack(filepath: str, stack: List[Dict[str, Any]]) -> None:
    ensure_data_dir()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(stack, f, indent=2)
    except Exception:
        pass


def load_undo_history() -> List[Dict[str, Any]]:
    return _load_stack(UNDO_FILE)


def save_undo_history(history: List[Dict[str, Any]]) -> None:
    _save_stack(UNDO_FILE, history)


def load_redo_history() -> List[Dict[str, Any]]:
    return _load_stack(REDO_FILE)


def save_redo_history(history: List[Dict[str, Any]]) -> None:
    _save_stack(REDO_FILE, history)


def record_operation(
    action: str,
    items: List[Dict[str, Any]],
    description: str = "",
) -> Dict[str, Any]:
    """Record an executed operation into the undo log and clear the redo stack."""
    entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
        "action": action,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description or f"{action.capitalize()} {len(items)} items",
        "items": items,
    }
    history = load_undo_history()
    history.append(entry)
    save_undo_history(history[-50:])
    # Performing a new operation resets the redo stack
    save_redo_history([])
    return entry


def peek_last_operation() -> Optional[Dict[str, Any]]:
    history = load_undo_history()
    return history[-1] if history else None


def pop_last_operation() -> Optional[Dict[str, Any]]:
    history = load_undo_history()
    if not history:
        return None
    last = history.pop()
    save_undo_history(history)
    return last


def peek_redo_operation() -> Optional[Dict[str, Any]]:
    history = load_redo_history()
    return history[-1] if history else None


def pop_redo_operation() -> Optional[Dict[str, Any]]:
    history = load_redo_history()
    if not history:
        return None
    last = history.pop()
    save_redo_history(history)
    return last


def push_redo_operation(entry: Dict[str, Any]) -> None:
    history = load_redo_history()
    history.append(entry)
    save_redo_history(history[-50:])


# ==============================================================================
# Execution of Undo and Redo
# ==============================================================================
def execute_undo(entry: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """
    Revert an operation:
    - For 'move': moves items back from dst to src.
    - For 'copy': deletes ONLY files created at dst that did not previously exist.
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
                    os.makedirs(os.path.dirname(os.path.abspath(src)), exist_ok=True)
                    shutil.move(dst, src)
                    reverted.append(f"Moved back: {os.path.basename(dst)} ➔ {src}")
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
                # Never delete pre-existing files!
                continue

            if os.path.exists(dst):
                try:
                    if is_dir and os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                    reverted.append(f"Removed copied item: {os.path.basename(dst)}")
                except Exception as e:
                    errors.append(f"Failed to remove {dst}: {e}")

    else:
        return False, f"Unknown action '{action}' in undo log.", []

    if errors and not reverted:
        return False, "Undo failed:\n" + "\n".join(errors), []

    msg = f"Successfully reverted {len(reverted)} item(s)."
    return True, msg, reverted


def execute_redo(entry: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    """
    Re-apply an undone operation:
    - For 'move': moves items from src to dst.
    - For 'copy': copies items from src to dst.
    """
    action = entry.get("action")
    items = entry.get("items", [])
    reapplied: List[str] = []
    errors: List[str] = []

    for item in items:
        src = item.get("src")
        dst = item.get("dst")
        is_dir = item.get("is_dir", False)
        if not src or not dst:
            continue

        if not os.path.exists(src):
            errors.append(f"Source item '{src}' no longer exists.")
            continue

        try:
            os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
            if action == "move":
                shutil.move(src, dst)
                reapplied.append(f"Moved: {os.path.basename(src)} ➔ {dst}")
            elif action == "copy":
                if is_dir:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
                reapplied.append(f"Copied: {os.path.basename(src)} ➔ {dst}")
        except Exception as e:
            errors.append(f"Failed to re-apply '{src}': {e}")

    if errors and not reapplied:
        return False, "Redo failed:\n" + "\n".join(errors), []

    msg = f"Successfully re-applied {len(reapplied)} item(s)."
    return True, msg, reapplied
