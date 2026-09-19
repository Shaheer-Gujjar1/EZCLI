"""Core scanning and cleaning engine for ez cleanup."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


CRITICAL_PATTERNS = [
    r"^xorg$",
    r"^xserver-xorg",
    r"^x11-common$",
    r"^gdm[3]?$",
    r"^sddm",
    r"^lightdm",
    r"^lxdm",
    r"^gnome-shell",
    r"^gnome-core",
    r"^gnome-session",
    r"^ubuntu-desktop",
    r"^kubuntu-desktop",
    r"^xubuntu-desktop",
    r"^lubuntu-desktop",
    r"^plasma-desktop",
    r"^plasma-workspace",
    r"^xfce4",
    r"^mate-desktop",
    r"^cinnamon",
    r"^budgie-desktop",
    r"^pantheon",
    r"^lxqt",
    r"^dde",  # Deepin Desktop
    r"^wayland",
    r"^mutter",
    r"^kwin",
    r"^systemd-sysv$",
    r"^init$",
    r"^login$",
]


def format_bytes(bytes_count: float) -> str:
    """Format bytes into human-readable string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    size = float(bytes_count)
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_idx]}"


def detect_desktop_critical_packages(packages: List[str]) -> List[str]:
    """Identify any packages that are critical for desktop or display functionality."""
    critical_found: List[str] = []
    compiled = [re.compile(p, re.IGNORECASE) for p in CRITICAL_PATTERNS]
    for pkg in packages:
        name = pkg.strip()
        if not name:
            continue
        for pat in compiled:
            if pat.search(name):
                critical_found.append(name)
                break
    return critical_found


def scan_apt_cache(cache_dir: str = "/var/cache/apt/archives") -> Tuple[int, int]:
    """Scan APT download cache. Returns (file_count, total_bytes)."""
    count = 0
    total_bytes = 0
    path = Path(cache_dir)
    if not path.is_dir():
        return 0, 0
    try:
        for entry in path.iterdir():
            if entry.name == "partial":
                continue
            if entry.is_file() and entry.name.endswith(".deb"):
                try:
                    total_bytes += entry.stat().st_size
                    count += 1
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return count, total_bytes


def scan_orphan_packages() -> Tuple[List[str], int]:
    """
    Run apt-get autoremove dry-run to discover removable orphan packages.
    Returns (package_names, estimated_bytes).
    """
    if not shutil.which("apt-get"):
        return [], 0

    env = os.environ.copy()
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    try:
        proc = subprocess.run(
            ["apt-get", "--dry-run", "autoremove"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        output = proc.stdout or ""
    except Exception:
        return [], 0

    packages: List[str] = []
    in_remove_block = False
    est_bytes = 0

    for line in output.splitlines():
        line_clean = line.strip()
        if "The following packages will be REMOVED:" in line:
            in_remove_block = True
            continue
        if in_remove_block:
            if line.startswith("  "):
                tokens = line.split()
                for token in tokens:
                    pkg = token.strip()
                    if pkg and not pkg.startswith("*"):
                        packages.append(pkg)
            elif line_clean and not line.startswith(" "):
                in_remove_block = False

        m = re.search(r"After this operation,\s+([\d\.]+)\s+([kKmMgGtT]?[bB])\s+disk space will be freed", line)
        if m:
            val = float(m.group(1))
            unit = m.group(2).upper()
            mult = 1
            if "K" in unit:
                mult = 1024
            elif "M" in unit:
                mult = 1024 * 1024
            elif "G" in unit:
                mult = 1024 * 1024 * 1024
            est_bytes = int(val * mult)

    return packages, est_bytes


def scan_trash(trash_dir: Optional[str] = None) -> Tuple[int, int]:
    """Scan user trash. Returns (item_count, total_bytes)."""
    if trash_dir is None:
        trash_dir = os.path.expanduser("~/.local/share/Trash")
    files_dir = Path(trash_dir) / "files"
    if not files_dir.is_dir():
        return 0, 0

    count = 0
    total_bytes = 0
    try:
        for entry in files_dir.iterdir():
            count += 1
            if entry.is_file() or entry.is_symlink():
                try:
                    total_bytes += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
            elif entry.is_dir():
                for root, _, fs in os.walk(entry):
                    for f in fs:
                        try:
                            fp = os.path.join(root, f)
                            total_bytes += os.lstat(fp).st_size
                        except OSError:
                            pass
    except (PermissionError, OSError):
        pass
    return count, total_bytes


def clean_trash(trash_dir: Optional[str] = None) -> int:
    """Empty user trash files and info. Returns bytes freed."""
    if trash_dir is None:
        trash_dir = os.path.expanduser("~/.local/share/Trash")
    base = Path(trash_dir)
    freed = 0
    for subdir in ["files", "info"]:
        d = base / subdir
        if d.is_dir():
            for item in d.iterdir():
                try:
                    if item.is_file() or item.is_symlink():
                        sz = item.stat(follow_symlinks=False).st_size
                        if subdir == "files":
                            freed += sz
                        item.unlink()
                    elif item.is_dir():
                        dir_sz = 0
                        for root, _, fs in os.walk(item):
                            for f in fs:
                                try:
                                    dir_sz += os.lstat(os.path.join(root, f)).st_size
                                except OSError:
                                    pass
                        if subdir == "files":
                            freed += dir_sz
                        shutil.rmtree(item, ignore_errors=True)
                except OSError:
                    pass
    return freed


def scan_old_logs(log_dir: str = "/var/log") -> Tuple[int, int]:
    """Scan rotated and archived logs in /var/log. Returns (file_count, total_bytes)."""
    path = Path(log_dir)
    if not path.is_dir():
        return 0, 0
    count = 0
    total_bytes = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".gz") or f.endswith(".old") or re.search(r"\.\d+$", f):
                    fp = os.path.join(root, f)
                    try:
                        st = os.stat(fp)
                        total_bytes += st.st_size
                        count += 1
                    except OSError:
                        pass
    except (PermissionError, OSError):
        pass
    return count, total_bytes


def scan_thumbnails(thumb_dir: Optional[str] = None) -> Tuple[int, int]:
    """Scan thumbnail cache. Returns (file_count, total_bytes)."""
    if thumb_dir is None:
        thumb_dir = os.path.expanduser("~/.cache/thumbnails")
    path = Path(thumb_dir)
    if not path.is_dir():
        return 0, 0
    count = 0
    total_bytes = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    st = os.stat(os.path.join(root, f))
                    total_bytes += st.st_size
                    count += 1
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return count, total_bytes


def clean_thumbnails(thumb_dir: Optional[str] = None) -> int:
    """Clean thumbnail cache. Returns bytes freed."""
    if thumb_dir is None:
        thumb_dir = os.path.expanduser("~/.cache/thumbnails")
    path = Path(thumb_dir)
    freed = 0
    if not path.is_dir():
        return 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    st = os.stat(fp)
                    freed += st.st_size
                    os.remove(fp)
                except OSError:
                    pass
    except (PermissionError, OSError):
        pass
    return freed
