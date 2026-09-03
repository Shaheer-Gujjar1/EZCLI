"""Defensive, 100% read-only system collectors for EasyCLI."""

import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from .distro import detect_distro, DistroInfo


def run_command_safe(
    cmd: List[str],
    timeout: int = 10,
    check_exit: bool = False,
    env_override: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """
    Safely execute a system command without shell=True.
    Returns (returncode, stdout, stderr).
    Never raises an uncaught exception.
    """
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    if env_override:
        env.update(env_override)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError:
        return -2, "", f"Tool '{cmd[0]}' not found on this system"
    except PermissionError:
        return -3, "", f"Permission denied executing '{cmd[0]}'"
    except Exception as e:
        return -4, "", f"Execution error: {str(e)}"


# ==============================================================================
# 1. System Info
# ==============================================================================
def collect_system_info() -> Dict[str, Any]:
    """Collect OS, hostname, kernel, architecture, and uptime."""
    distro = detect_distro()
    info: Dict[str, Any] = {
        "os_name": distro.pretty_name or distro.name,
        "distro_id": distro.id,
        "distro_version": distro.version,
        "codename": distro.codename,
        "is_debian_based": distro.is_debian_based,
        "hostname": "Unknown",
        "kernel": "Unknown",
        "arch": "Unknown",
        "uptime": "Unknown",
        "hardware_model": "",
        "chassis": "",
    }

    # Query hostnamectl
    rc, out, _ = run_command_safe(["hostnamectl"], timeout=5)
    if rc == 0 and out:
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if "hostname" in k:
                    info["hostname"] = v
                elif "kernel" in k:
                    info["kernel"] = v
                elif "architecture" in k:
                    info["arch"] = v
                elif "hardware model" in k:
                    info["hardware_model"] = v
                elif "chassis" in k:
                    info["chassis"] = v
                elif "operating system" in k and not info["os_name"]:
                    info["os_name"] = v

    # Fallbacks for hostname / kernel if hostnamectl was empty
    if info["hostname"] == "Unknown":
        try:
            import socket
            info["hostname"] = socket.gethostname()
        except Exception:
            pass

    if info["kernel"] == "Unknown":
        rc_u, out_u, _ = run_command_safe(["uname", "-sr"], timeout=3)
        if rc_u == 0 and out_u:
            info["kernel"] = out_u

    if info["arch"] == "Unknown":
        rc_m, out_m, _ = run_command_safe(["uname", "-m"], timeout=3)
        if rc_m == 0 and out_m:
            info["arch"] = out_m

    # Query uptime -p
    rc_up, out_up, _ = run_command_safe(["uptime", "-p"], timeout=3)
    if rc_up == 0 and out_up:
        info["uptime"] = out_up.replace("up ", "")
    else:
        # Fallback reading /proc/uptime
        try:
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.readline().split()[0])
            mins, secs = divmod(int(uptime_seconds), 60)
            hours, mins = divmod(mins, 60)
            days, hours = divmod(hours, 24)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            if mins:
                parts.append(f"{mins}m")
            info["uptime"] = " ".join(parts) or "< 1m"
        except Exception:
            info["uptime"] = "Unknown"

    return info


# ==============================================================================
# 2. Resource Stats (CPU Load & RAM)
# ==============================================================================
def collect_stats() -> Dict[str, Any]:
    """Collect CPU load line, core count, and RAM/Swap usage."""
    data: Dict[str, Any] = {
        "cpu_cores": 1,
        "load_1m": 0.0,
        "load_5m": 0.0,
        "load_15m": 0.0,
        "load_percent": 0.0,
        "ram_total_str": "0B",
        "ram_used_str": "0B",
        "ram_free_str": "0B",
        "ram_avail_str": "0B",
        "ram_percent": 0.0,
        "swap_total_str": "0B",
        "swap_used_str": "0B",
        "swap_percent": 0.0,
    }

    # CPU cores
    rc_np, out_np, _ = run_command_safe(["nproc"], timeout=3)
    if rc_np == 0 and out_np.isdigit():
        data["cpu_cores"] = int(out_np)
    else:
        data["cpu_cores"] = os.cpu_count() or 1

    # Load average
    try:
        load1, load5, load15 = os.getloadavg()
        data["load_1m"] = round(load1, 2)
        data["load_5m"] = round(load5, 2)
        data["load_15m"] = round(load15, 2)
        # Load percentage relative to cores
        data["load_percent"] = min(100.0, round((load1 / max(1, data["cpu_cores"])) * 100.0, 1))
    except Exception:
        # Fallback reading /proc/loadavg
        try:
            with open("/proc/loadavg", "r") as f:
                parts = f.read().split()
                data["load_1m"] = float(parts[0])
                data["load_5m"] = float(parts[1])
                data["load_15m"] = float(parts[2])
                data["load_percent"] = min(100.0, round((data["load_1m"] / max(1, data["cpu_cores"])) * 100.0, 1))
        except Exception:
            pass

    # RAM & Swap via free -b and free -h
    rc_fb, out_fb, _ = run_command_safe(["free", "-b"], timeout=3)
    rc_fh, out_fh, _ = run_command_safe(["free", "-h"], timeout=3)

    if rc_fb == 0 and out_fb:
        lines = out_fb.splitlines()
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if parts[0].lower().startswith("mem"):
                try:
                    total = int(parts[1])
                    used = int(parts[2])
                    avail = int(parts[6]) if len(parts) > 6 else int(parts[3])
                    # Real used RAM = total - available
                    actual_used = max(0, total - avail) if avail else used
                    data["ram_percent"] = round((actual_used / max(1, total)) * 100.0, 1)
                except Exception:
                    pass
            elif parts[0].lower().startswith("swap"):
                try:
                    total_s = int(parts[1])
                    used_s = int(parts[2])
                    if total_s > 0:
                        data["swap_percent"] = round((used_s / total_s) * 100.0, 1)
                except Exception:
                    pass

    # Extract human-readable strings from free -h
    if rc_fh == 0 and out_fh:
        for line in out_fh.splitlines():
            parts = line.split()
            if not parts:
                continue
            if parts[0].lower().startswith("mem") and len(parts) >= 7:
                data["ram_total_str"] = parts[1]
                data["ram_used_str"] = parts[2]
                data["ram_free_str"] = parts[3]
                data["ram_avail_str"] = parts[6]
            elif parts[0].lower().startswith("swap") and len(parts) >= 4:
                data["swap_total_str"] = parts[1]
                data["swap_used_str"] = parts[2]

    return data


# ==============================================================================
# 3. Disk Space Usage
# ==============================================================================
IGNORED_FS_TYPES = {
    "tmpfs",
    "devtmpfs",
    "udev",
    "squashfs",
    "overlay",
    "overlayfs",
    "efivarfs",
    "shm",
    "none",
    "run",
}


def collect_disk_info() -> List[Dict[str, Any]]:
    """
    Collect disk space usage table via df -h.
    Filters out pseudo filesystems like tmpfs, devtmpfs, squashfs.
    """
    rc, out, _ = run_command_safe(["df", "-h", "-P"], timeout=5)
    disks: List[Dict[str, Any]] = []

    if rc != 0 or not out:
        return disks

    lines = out.splitlines()
    if len(lines) < 2:
        return disks

    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        fs = parts[0]
        size = parts[1]
        used = parts[2]
        avail = parts[3]
        pct_str = parts[4].rstrip("%")
        mount = parts[5]

        # Ignore pseudo filesystems
        if any(fs.startswith(prefix) for prefix in ["tmpfs", "devtmpfs", "udev", "overlay", "shm"]):
            continue
        if any(ign in fs.lower() for ign in IGNORED_FS_TYPES):
            continue
        if mount.startswith("/sys") or mount.startswith("/proc") or mount.startswith("/dev"):
            continue

        try:
            percent = int(pct_str)
        except ValueError:
            percent = 0

        disks.append({
            "filesystem": fs,
            "mount": mount,
            "size": size,
            "used": used,
            "available": avail,
            "percent": percent,
        })

    # Sort by mount point
    disks.sort(key=lambda x: x["mount"])
    return disks


# ==============================================================================
# 4. Big Files & Folders
# ==============================================================================
def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0 or unit == "TB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{num_bytes} B"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def collect_big_files(folder_path: str = "~", limit: int = 15) -> Dict[str, Any]:
    """
    Scan directory for largest items with depth limit, skipping unreadable paths.
    Wraps du -h --max-depth=1 and find defensively.
    """
    target = os.path.abspath(os.path.expanduser(folder_path))
    result: Dict[str, Any] = {
        "folder": target,
        "exists": False,
        "error": "",
        "items": [],
    }

    if not os.path.exists(target):
        result["error"] = f"Directory '{target}' does not exist."
        return result

    if not os.path.isdir(target):
        result["error"] = f"Path '{target}' is a file, not a directory."
        return result

    result["exists"] = True

    # 1. First run du -k --max-depth=1 with a defensive timeout
    items_map: Dict[str, Dict[str, Any]] = {}
    rc, out, err = run_command_safe(
        ["du", "-k", "--max-depth=1", target],
        timeout=6,
    )

    if rc == 0 and out:
        for line in out.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                try:
                    kb = int(parts[0])
                    p = parts[1].strip()
                    if p == target:
                        continue  # Skip root target itself
                    name = os.path.basename(p)
                    is_dir = os.path.isdir(p)
                    items_map[p] = {
                        "name": name,
                        "path": p,
                        "size_bytes": kb * 1024,
                        "size_str": format_bytes(kb * 1024),
                        "is_dir": is_dir,
                    }
                except ValueError:
                    continue

    # 2. Fast scan immediate files & direct children in case du timed out or for top files
    try:
        with os.scandir(target) as it:
            for entry in it:
                try:
                    p = entry.path
                    if p not in items_map:
                        st = entry.stat(follow_symlinks=False)
                        items_map[p] = {
                            "name": entry.name,
                            "path": p,
                            "size_bytes": st.st_size,
                            "size_str": format_bytes(st.st_size),
                            "is_dir": entry.is_dir(follow_symlinks=False),
                        }
                except (PermissionError, FileNotFoundError):
                    continue
    except PermissionError:
        result["error"] = f"Permission denied reading directory contents of '{target}'"
        return result

    # Sort descending by size
    sorted_items = sorted(items_map.values(), key=lambda x: x["size_bytes"], reverse=True)
    result["items"] = sorted_items[:limit]
    return result


# ==============================================================================
# 5. Package Search
# ==============================================================================
def query_flathub(term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Query Flathub API for matching Flatpak packages (timeout 2.5s)."""
    items = []
    try:
        import urllib.request
        payload = json.dumps({"query": term}).encode("utf-8")
        req = urllib.request.Request(
            "https://flathub.org/api/v2/search",
            data=payload,
            headers={"User-Agent": "ezcli/0.1", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            for h in data.get("hits", [])[:limit]:
                app_id = h.get("app_id", "")
                name = h.get("name") or app_id
                summary = h.get("summary", "") or ""
                items.append({
                    "name": name,
                    "app_id": app_id,
                    "version_info": "",
                    "description": summary,
                    "platform": "flatpak",
                    "platform_name": "Flatpak",
                    "platform_icon": "🟣",
                    "installed": False,
                })
    except Exception:
        pass
    return items


def query_snapcraft(term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Query Snapcraft Store API for matching Snap packages (timeout 2.5s)."""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api.snapcraft.io/v2/snaps/find?q={term}&fields=title,summary,version",
            headers={"User-Agent": "ezcli/0.1", "Snap-Device-Series": "16"},
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            for r in data.get("results", [])[:limit]:
                snap_info = r.get("snap", {})
                name = r.get("name", "")
                title = snap_info.get("title") or name
                summary = snap_info.get("summary", "") or ""
                items.append({
                    "name": title,
                    "app_id": name,
                    "version_info": snap_info.get("version", ""),
                    "description": summary,
                    "platform": "snap",
                    "platform_name": "Snap",
                    "platform_icon": "🟢",
                    "installed": False,
                })
    except Exception:
        pass
    return items


def collect_package_search(term: str, limit: int = 25) -> Dict[str, Any]:
    """
    Search packages across APT (📦), Flatpak (🟣), and Snap (🟢).
    Intelligently ranks results and checks local runtime availability.
    """
    result: Dict[str, Any] = {
        "term": term,
        "packages": [],
        "has_apt": shutil.which("apt") is not None,
        "has_flatpak": shutil.which("flatpak") is not None,
        "has_snap": shutil.which("snap") is not None,
        "error": "",
    }

    if not term or not term.strip():
        result["error"] = "No search term provided."
        return result

    term_clean = term.strip()
    term_lower = term_clean.lower()
    apt_packages_map: Dict[str, Dict[str, Any]] = {}

    # 1. Primary: Run apt search
    rc, out, err = run_command_safe(["apt", "search", term_clean], timeout=15)
    if rc == 0 and out:
        current_pkg: Optional[Dict[str, Any]] = None
        for line in out.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            if line_clean.startswith(("Sorting...", "Full Text Search...", "WARNING:")):
                continue

            # Check if this line is a package header (e.g., 'curl/jammy,now 7.81.0-1ubuntu1.16 amd64 [installed]')
            if "/" in line and not line.startswith(" "):
                if current_pkg and current_pkg["name"] not in apt_packages_map:
                    apt_packages_map[current_pkg["name"]] = current_pkg
                parts = line.split("/", 1)
                name = parts[0].strip()
                rest = parts[1].strip() if len(parts) > 1 else ""
                installed = "[installed" in line.lower()
                current_pkg = {
                    "name": name,
                    "app_id": name,
                    "version_info": rest,
                    "description": "",
                    "platform": "apt",
                    "platform_name": "APT",
                    "platform_icon": "📦",
                    "installed": installed,
                }
            elif current_pkg and not current_pkg["description"]:
                current_pkg["description"] = line_clean

        if current_pkg and current_pkg["name"] not in apt_packages_map:
            apt_packages_map[current_pkg["name"]] = current_pkg

    # Fallback to apt-cache search if apt search was empty
    if not apt_packages_map:
        rc_ac, out_ac, _ = run_command_safe(["apt-cache", "search", term_clean], timeout=10)
        if rc_ac == 0 and out_ac:
            for line in out_ac.splitlines():
                line_clean = line.strip()
                if " - " in line_clean:
                    pkg_name, desc = line_clean.split(" - ", 1)
                    pkg_name = pkg_name.strip()
                    if pkg_name not in apt_packages_map:
                        rc_dpkg, _, _ = run_command_safe(["dpkg", "-s", pkg_name], timeout=2)
                        installed = (rc_dpkg == 0)
                        apt_packages_map[pkg_name] = {
                            "name": pkg_name,
                            "app_id": pkg_name,
                            "version_info": "",
                            "description": desc.strip(),
                            "platform": "apt",
                            "platform_name": "APT",
                            "platform_icon": "📦",
                            "installed": installed,
                        }

    # Rank APT packages
    def rank_key(item: Dict[str, Any]) -> Tuple[int, str]:
        n = item["name"].lower()
        if n == term_lower:
            return (0, n)
        elif n.startswith(term_lower):
            return (1, n)
        elif term_lower in n:
            return (2, n)
        else:
            return (3, n)

    ranked_apt = sorted(apt_packages_map.values(), key=rank_key)

    # 2. Query Flatpak (Flathub)
    flatpak_items = query_flathub(term_clean, limit=4)
    # Check if installed locally if flatpak binary exists
    if result["has_flatpak"] and flatpak_items:
        rc_fl, out_fl, _ = run_command_safe(["flatpak", "list", "--app", "--columns=application"], timeout=3)
        if rc_fl == 0 and out_fl:
            installed_apps = set(out_fl.splitlines())
            for item in flatpak_items:
                if item["app_id"] in installed_apps:
                    item["installed"] = True

    # 3. Query Snap (Snapcraft)
    snap_items = query_snapcraft(term_clean, limit=4)
    # Check if installed locally if snap binary exists
    if result["has_snap"] and snap_items:
        rc_sn, out_sn, _ = run_command_safe(["snap", "list"], timeout=3)
        if rc_sn == 0 and out_sn:
            installed_snaps = set(line.split()[0] for line in out_sn.splitlines() if line.split())
            for item in snap_items:
                if item["app_id"] in installed_snaps:
                    item["installed"] = True

    # Combine results: prioritized APT matches, followed by Flatpak, Snap, and additional APT
    combined: List[Dict[str, Any]] = []

    # Add top APT matches (up to 5)
    top_apt = ranked_apt[:5]
    remaining_apt = ranked_apt[5:]

    # Interleave / organize
    combined.extend(top_apt)
    combined.extend(flatpak_items)
    combined.extend(snap_items)
    combined.extend(remaining_apt)

    # Attach install & setup command metadata
    for pkg in combined:
        plat = pkg["platform"]
        app_id = pkg.get("app_id", pkg["name"])
        name = pkg["name"]
        if plat == "apt":
            pkg["install_cmd"] = f"sudo apt install -y {app_id}"
            pkg["setup_cmd"] = ""
            pkg["platform_supported"] = result["has_apt"]
        elif plat == "flatpak":
            pkg["install_cmd"] = f"flatpak install flathub {app_id}"
            pkg["setup_cmd"] = "sudo apt install -y flatpak && flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo"
            pkg["platform_supported"] = result["has_flatpak"]
        elif plat == "snap":
            pkg["install_cmd"] = f"sudo snap install {app_id}"
            pkg["setup_cmd"] = "sudo apt install -y snapd"
            pkg["platform_supported"] = result["has_snap"]

    result["packages"] = combined[:limit]
    return result


# ==============================================================================
# 6. Package Details
# ==============================================================================
def collect_package_info(name: str) -> Dict[str, Any]:
    """
    Query package info wrapping apt show + dpkg -s.
    """
    result: Dict[str, Any] = {
        "name": name,
        "found": False,
        "is_installed": False,
        "installed_version": "",
        "repo_version": "",
        "section": "",
        "size": "",
        "installed_size": "",
        "maintainer": "",
        "homepage": "",
        "description": "",
        "error": "",
    }

    # 1. Check dpkg -s for installation state
    rc_dpkg, out_dpkg, _ = run_command_safe(["dpkg", "-s", name], timeout=5)
    if rc_dpkg == 0 and out_dpkg:
        result["found"] = True
        desc_lines = []
        is_desc = False
        for line in out_dpkg.splitlines():
            if line.startswith("Status:") and "installed" in line.lower() and "not-installed" not in line.lower():
                result["is_installed"] = True
            elif line.startswith("Version:"):
                result["installed_version"] = line.split(":", 1)[1].strip()
            elif line.startswith("Installed-Size:"):
                try:
                    kb = int(line.split(":", 1)[1].strip())
                    result["installed_size"] = format_bytes(kb * 1024)
                except ValueError:
                    result["installed_size"] = line.split(":", 1)[1].strip() + " KB"
            elif line.startswith("Section:"):
                result["section"] = line.split(":", 1)[1].strip()
            elif line.startswith("Maintainer:"):
                result["maintainer"] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                is_desc = True
                desc_lines.append(line.split(":", 1)[1].strip())
            elif is_desc:
                if line.startswith(" ") or line.startswith("\t"):
                    desc_lines.append(line.strip())
                else:
                    is_desc = False
        if desc_lines:
            result["description"] = " ".join(desc_lines)

    # 2. Query apt show for repository info
    rc_apt, out_apt, _ = run_command_safe(["apt", "show", name], timeout=8)
    if rc_apt == 0 and out_apt:
        result["found"] = True
        desc_lines = []
        is_desc = False
        for line in out_apt.splitlines():
            if line.startswith("Version:") and not result["repo_version"]:
                result["repo_version"] = line.split(":", 1)[1].strip()
            elif line.startswith("Download-Size:") or line.startswith("Size:"):
                if not result["size"]:
                    result["size"] = line.split(":", 1)[1].strip()
            elif line.startswith("Homepage:") and not result["homepage"]:
                result["homepage"] = line.split(":", 1)[1].strip()
            elif line.startswith("Section:") and not result["section"]:
                result["section"] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:") and not result["description"]:
                is_desc = True
                desc_lines.append(line.split(":", 1)[1].strip())
            elif is_desc:
                if line.startswith(" ") or line.startswith("\t"):
                    desc_lines.append(line.strip())
                else:
                    is_desc = False
        if desc_lines and not result["description"]:
            result["description"] = " ".join(desc_lines)

    if not result["found"]:
        result["error"] = f"Package '{name}' was not found in apt cache or installed packages."

    return result


# ==============================================================================
# 7. Available Updates
# ==============================================================================
def collect_available_updates() -> Dict[str, Any]:
    """
    List upgradable packages using existing lists only.
    Never runs apt update. Checks if apt lists look stale.
    """
    result: Dict[str, Any] = {
        "updates": [],
        "count": 0,
        "is_stale": False,
        "stale_days": 0,
        "last_updated_str": "Unknown",
        "error": "",
    }

    # Check list freshness by inspecting /var/lib/apt/periodic/update-success-stamp or /var/lib/apt/lists/
    stamp_path = "/var/lib/apt/periodic/update-success-stamp"
    lists_dir = "/var/lib/apt/lists"
    last_mtime: Optional[float] = None

    if os.path.isfile(stamp_path):
        try:
            last_mtime = os.path.getmtime(stamp_path)
        except Exception:
            pass

    if last_mtime is None and os.path.isdir(lists_dir):
        try:
            # Check newest file in lists directory
            mtimes = [
                os.path.getmtime(os.path.join(lists_dir, f))
                for f in os.listdir(lists_dir)
                if not f.startswith("lock") and not f.startswith("partial")
            ]
            if mtimes:
                last_mtime = max(mtimes)
        except Exception:
            pass

    if last_mtime:
        age_seconds = time.time() - last_mtime
        days = int(age_seconds // 86400)
        dt = datetime.datetime.fromtimestamp(last_mtime).strftime("%Y-%m-%d %H:%M")
        result["last_updated_str"] = f"{dt} ({days} days ago)" if days > 0 else f"{dt} (today)"
        result["stale_days"] = days
        if days >= 7:
            result["is_stale"] = True
    else:
        result["is_stale"] = True
        result["last_updated_str"] = "Unknown (lists timestamp unavailable)"

    # Run apt list --upgradable
    rc, out, err = run_command_safe(["apt", "list", "--upgradable"], timeout=10)
    if rc != 0 and not out:
        result["error"] = err or "Could not retrieve upgradable package list."
        return result

    # Example lines:
    # curl/jammy-updates 7.81.0-1ubuntu1.16 amd64 [upgradable from: 7.81.0-1ubuntu1.15]
    pattern = re.compile(r"^([^/\s]+)/\S+\s+(\S+)\s+(\S+)\s+\[upgradable from:\s+([^\]]+)\]")
    updates = []

    for line in out.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("Listing..."):
            continue
        m = pattern.match(line_clean)
        if m:
            pkg, new_ver, arch, cur_ver = m.groups()
            updates.append({
                "package": pkg,
                "current_version": cur_ver,
                "new_version": new_ver,
                "arch": arch,
            })
        else:
            # Fallback looser parsing
            if "/" in line_clean and "upgradable from" in line_clean:
                try:
                    pkg = line_clean.split("/")[0].strip()
                    parts = line_clean.split()
                    new_ver = parts[1] if len(parts) > 1 else "?"
                    cur_ver = line_clean.split("upgradable from:")[1].rstrip("]").strip()
                    updates.append({
                        "package": pkg,
                        "current_version": cur_ver,
                        "new_version": new_ver,
                        "arch": "",
                    })
                except Exception:
                    continue

    result["updates"] = updates
    result["count"] = len(updates)
    return result


# ==============================================================================
# 8. Service Status
# ==============================================================================
def collect_service_status(service_name: str) -> Dict[str, Any]:
    """
    Query systemctl is-active and is-enabled for a service.
    """
    clean_name = service_name.strip()
    if not clean_name.endswith(".service") and "." not in clean_name:
        unit_name = f"{clean_name}.service"
    else:
        unit_name = clean_name

    result: Dict[str, Any] = {
        "service": clean_name,
        "unit": unit_name,
        "active_state": "unknown",
        "enabled_state": "unknown",
        "sub_state": "unknown",
        "description": "",
        "main_pid": "",
        "error": "",
    }

    # is-active
    rc_act, out_act, err_act = run_command_safe(["systemctl", "is-active", unit_name], timeout=4)
    result["active_state"] = out_act.strip() or ("inactive" if rc_act != 0 else "unknown")

    # is-enabled
    rc_en, out_en, _ = run_command_safe(["systemctl", "is-enabled", unit_name], timeout=4)
    result["enabled_state"] = out_en.strip() or ("disabled" if rc_en != 0 else "unknown")

    # Query details via systemctl show
    rc_sh, out_sh, _ = run_command_safe(
        ["systemctl", "show", unit_name, "--property=Description,SubState,ActiveState,UnitFileState,MainPID"],
        timeout=4,
    )
    if rc_sh == 0 and out_sh:
        for line in out_sh.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "Description":
                    result["description"] = v
                elif k == "SubState":
                    result["sub_state"] = v
                elif k == "ActiveState" and result["active_state"] == "unknown":
                    result["active_state"] = v
                elif k == "UnitFileState" and result["enabled_state"] == "unknown":
                    result["enabled_state"] = v
                elif k == "MainPID" and v != "0":
                    result["main_pid"] = v

    if result["active_state"] in ("unknown", "failed", "inactive") and "not-found" in out_act:
        result["active_state"] = "not-found"

    return result


# ==============================================================================
# 9. Network Info
# ==============================================================================
def collect_network_info() -> Dict[str, Any]:
    """
    Collect network info wrapping ip addr, ip route, and /etc/resolv.conf.
    """
    result: Dict[str, Any] = {
        "interfaces": [],
        "default_gateway": "None",
        "default_interface": "",
        "dns_servers": [],
        "online_state": "Offline",
        "error": "",
    }

    # 1. Default route via ip -j route or ip route
    rc_rj, out_rj, _ = run_command_safe(["ip", "-j", "route"], timeout=4)
    if rc_rj == 0 and out_rj:
        try:
            routes = json.loads(out_rj)
            for r in routes:
                if r.get("dst") == "default":
                    result["default_gateway"] = r.get("gateway", "None")
                    result["default_interface"] = r.get("dev", "")
                    break
        except Exception:
            pass

    if result["default_gateway"] == "None":
        rc_r, out_r, _ = run_command_safe(["ip", "route"], timeout=4)
        if rc_r == 0 and out_r:
            for line in out_r.splitlines():
                if line.startswith("default"):
                    parts = line.split()
                    if "via" in parts:
                        idx = parts.index("via")
                        if idx + 1 < len(parts):
                            result["default_gateway"] = parts[idx + 1]
                    if "dev" in parts:
                        idx = parts.index("dev")
                        if idx + 1 < len(parts):
                            result["default_interface"] = parts[idx + 1]

    # 2. Interfaces via ip -j addr or ip addr
    rc_aj, out_aj, _ = run_command_safe(["ip", "-j", "addr"], timeout=4)
    if rc_aj == 0 and out_aj:
        try:
            ifaces = json.loads(out_aj)
            for iface in ifaces:
                name = iface.get("ifname", "")
                flags = iface.get("flags", [])
                operstate = iface.get("operstate", "UNKNOWN")
                mac = iface.get("address", "")
                ipv4_list = []
                ipv6_list = []

                for addr_info in iface.get("addr_info", []):
                    family = addr_info.get("family")
                    local = addr_info.get("local")
                    prefixlen = addr_info.get("prefixlen")
                    if family == "inet" and local:
                        ipv4_list.append(f"{local}/{prefixlen}")
                    elif family == "inet6" and local:
                        # Skip link-local fe80 if other ipv6 exists
                        ipv6_list.append(f"{local}/{prefixlen}")

                is_up = "UP" in flags or operstate == "UP"
                result["interfaces"].append({
                    "name": name,
                    "state": "UP" if is_up else operstate,
                    "is_up": is_up,
                    "ipv4": ipv4_list,
                    "ipv6": ipv6_list,
                    "mac": mac,
                })
        except Exception:
            pass

    if not result["interfaces"]:
        # Fallback parsing plain ip addr
        rc_a, out_a, _ = run_command_safe(["ip", "addr"], timeout=4)
        if rc_a == 0 and out_a:
            current_if: Optional[Dict[str, Any]] = None
            for line in out_a.splitlines():
                if re.match(r"^\d+:\s+(\S+):", line):
                    if current_if:
                        result["interfaces"].append(current_if)
                    m = re.match(r"^\d+:\s+([^:]+):\s*<([^>]+)>", line)
                    if m:
                        name = m.group(1).split("@")[0]
                        flags = m.group(2).split(",")
                        current_if = {
                            "name": name,
                            "state": "UP" if "UP" in flags else "DOWN",
                            "is_up": "UP" in flags,
                            "ipv4": [],
                            "ipv6": [],
                            "mac": "",
                        }
                elif current_if:
                    line_s = line.strip()
                    if line_s.startswith("inet "):
                        current_if["ipv4"].append(line_s.split()[1])
                    elif line_s.startswith("inet6 "):
                        current_if["ipv6"].append(line_s.split()[1])
                    elif line_s.startswith("link/ether "):
                        current_if["mac"] = line_s.split()[1]
            if current_if:
                result["interfaces"].append(current_if)

    # 3. DNS servers from /etc/resolv.conf
    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        result["dns_servers"].append(parts[1])
    except Exception:
        pass

    # Determine online status
    has_gw = result["default_gateway"] not in ("None", "")
    has_up_iface = any(i["is_up"] and i["name"] != "lo" for i in result["interfaces"])
    if has_gw and has_up_iface:
        result["online_state"] = "Online"
    else:
        result["online_state"] = "Offline / Disconnected"

    return result


# ==============================================================================
# 10. Logs
# ==============================================================================
def collect_logs(lines_count: int = 50) -> Dict[str, Any]:
    """
    Collect recent journal logs with journalctl -n N --no-pager.
    Handles lack of systemd-journal permission gracefully.
    """
    result: Dict[str, Any] = {
        "requested_lines": lines_count,
        "logs": [],
        "permission_limited": False,
        "permission_message": "",
        "error": "",
    }

    cmd = ["journalctl", "-n", str(lines_count), "--no-pager"]
    rc, out, err = run_command_safe(cmd, timeout=8)

    # Check for journal access permission hints in stderr or stdout
    full_text = f"{out}\n{err}"
    if "Users in groups 'adm', 'systemd-journal' can see all messages" in full_text or "not seeing messages from other users" in full_text:
        result["permission_limited"] = True
        result["permission_message"] = (
            "Notice: Showing user-level logs only. To view full system and service logs, "
            "your user account requires membership in the 'adm' or 'systemd-journal' group."
        )

    if rc != 0 and not out:
        if "No journal files were found" in err or "Permission denied" in err:
            result["permission_limited"] = True
            result["permission_message"] = (
                "Unable to read system journals: Permission denied. "
                "EasyCLI is running in read-only mode without root permissions."
            )
        else:
            result["error"] = err or "Could not retrieve journal logs."
        return result

    parsed_logs: List[Dict[str, str]] = []
    lines = out.splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        # Skip journalctl hints
        if line_clean.startswith("Hint:") or "systemd-journal" in line_clean and "Users in groups" in line_clean:
            continue

        # Classify log severity
        lower_line = line_clean.lower()
        level = "info"
        if any(err_kw in lower_line for err_kw in ["error", "failed", "failure", "critical", "panic", "emerg", "alert"]):
            level = "error"
        elif any(warn_kw in lower_line for warn_kw in ["warning", "warn", "deprecated"]):
            level = "warning"
        elif any(ok_kw in lower_line for ok_kw in ["started", "reached target", "success", "active", "listening"]):
            level = "ok"

        parsed_logs.append({
            "raw": line_clean,
            "level": level,
        })

    result["logs"] = parsed_logs
    return result
