"""Places and bookmarks management for EasyCLI file explorer."""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


PRIMARY_DATA_DIR = os.path.expanduser("~/.local/share/ez")
LEGACY_DATA_DIR = os.path.expanduser("~/.local/share/ezcli")
DATA_DIR = PRIMARY_DATA_DIR
BOOKMARKS_FILE = os.path.join(DATA_DIR, "bookmarks.json")
RECENT_FILE = os.path.join(DATA_DIR, "recent.json")


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(LEGACY_DATA_DIR):
        for fname in ("bookmarks.json", "recent.json"):
            old_f = os.path.join(LEGACY_DATA_DIR, fname)
            new_f = os.path.join(DATA_DIR, fname)
            if os.path.exists(old_f) and not os.path.exists(new_f):
                try:
                    import shutil
                    shutil.copy2(old_f, new_f)
                except Exception:
                    pass


def get_standard_places() -> List[Tuple[str, str, str]]:
    """Return standard places: (icon, name, path)."""
    home = str(Path.home())
    places = [
        ("🏠", "Home", home),
        ("📥", "Downloads", os.path.join(home, "Downloads")),
        ("📄", "Documents", os.path.join(home, "Documents")),
        ("🖥️", "Desktop", os.path.join(home, "Desktop")),
    ]
    # Filter to only existing directories
    return [(icon, name, p) for icon, name, p in places if os.path.isdir(p)]


def load_bookmarks() -> List[str]:
    """Load user bookmarks from JSON."""
    ensure_data_dir()
    if not os.path.isfile(BOOKMARKS_FILE):
        return []
    try:
        with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [p for p in data if os.path.isdir(p)]
    except Exception:
        pass
    return []


def save_bookmarks(bookmarks: List[str]) -> None:
    """Save user bookmarks to JSON."""
    ensure_data_dir()
    try:
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2)
    except Exception:
        pass


def toggle_bookmark(path: str) -> bool:
    """Toggle bookmark for a directory. Returns True if added, False if removed."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    bms = load_bookmarks()
    if abs_path in bms:
        bms.remove(abs_path)
        save_bookmarks(bms)
        return False
    else:
        bms.append(abs_path)
        save_bookmarks(bms)
        return True


def load_recent() -> List[str]:
    """Load recently visited folders."""
    ensure_data_dir()
    if not os.path.isfile(RECENT_FILE):
        return []
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [p for p in data if os.path.isdir(p)]
    except Exception:
        pass
    return []


def add_recent(path: str) -> None:
    """Add path to recent folders list (keeps last 10)."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    recent = load_recent()
    if abs_path in recent:
        recent.remove(abs_path)
    recent.insert(0, abs_path)
    ensure_data_dir()
    try:
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(recent[:10], f, indent=2)
    except Exception:
        pass
