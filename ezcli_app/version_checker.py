"""
Universal Version Checker Subcommand ('ez version [name]').

Provides automatic, multi-source version inspection for any executable application,
Debian package, APT catalog candidate, Snap, Flatpak, Python library, or Node.js library.
Strictly read-only and requires zero flags or type specifiers.
"""

import datetime
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__


def format_mtime(timestamp: Optional[float]) -> str:
    """Format file modification timestamp into friendly YYYY-MM-DD HH:MM string."""
    if not timestamp or timestamp < 86400:  # Ignore epoch 0 / normalized packaging dates
        return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "N/A"


def extract_version_from_text(text: str) -> Optional[str]:
    """
    Extract the first sane semantic version string from text.
    Handles varied outputs like:
      - 'git version 2.43.0'
      - 'curl 8.14.1 (x86_64-pc-linux-gnu)...'
      - 'Python 3.12.3'
      - 'node v20.11.1'
      - 'OpenSSH_9.6p1'
      - 'tmux 3.4'
    """
    if not text:
        return None

    # Check the first few lines of output
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()][:5]
    for line in lines:
        # Pattern 1: explicit 'version 1.2.3', 'v1.2.3', '/1.2.3', or 'Name_1.2.3'
        m = re.search(
            r"(?:version\s*|(?<=\s)v|(?<=^)v|/|(?<=[a-zA-Z])_)\s*(\d+(?:\.\d+)*(?:[a-zA-Z0-9_.~+-]+)?)",
            line,
            re.IGNORECASE,
        )
        if m:
            ver = m.group(1).rstrip("),;:-_")
            if ver and any(c.isdigit() for c in ver) and ("." in ver or len(ver) > 1):
                return ver

        # Pattern 2: standalone semantic version X.Y or X.Y.Z
        m2 = re.search(r"\b(\d+\.\d+(?:\.\d+)*(?:[-.+][a-zA-Z0-9_.~]+)?)\b", line)
        if m2:
            ver2 = m2.group(1).rstrip("),;:-_")
            if ver2:
                return ver2

    return None


# ------------------------------------------------------------------------------
# 1. Executable on PATH (Binary)
# ------------------------------------------------------------------------------
def detect_executable_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect executable on PATH by quietly running common version flags."""
    bin_path = shutil.which(name)
    if not bin_path or not os.path.isfile(bin_path):
        return None

    detected_ver: Optional[str] = None
    candidate_flags = ["--version", "-v", "-V", "version", "-version"]

    for flag in candidate_flags:
        try:
            res = subprocess.run(
                [bin_path, flag],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2,
            )
            # Some tools write version to stdout, others to stderr (e.g., java, openssl)
            combined_output = f"{res.stdout}\n{res.stderr}".strip()
            ver = extract_version_from_text(combined_output)
            if ver:
                detected_ver = ver
                break
        except Exception:
            continue

    # Fallback if flag execution produced no version string
    if not detected_ver:
        detected_ver = "Detected (unversioned binary)"

    mtime_val = None
    try:
        mtime_val = os.path.getmtime(bin_path)
    except OSError:
        pass

    return {
        "source_type": "Binary",
        "source_icon": "🖥️",
        "name": os.path.basename(bin_path),
        "version": detected_ver,
        "location": bin_path,
        "install_date": format_mtime(mtime_val),
        "source_order": 1,
    }


# ------------------------------------------------------------------------------
# 2. Installed Debian Package via dpkg
# ------------------------------------------------------------------------------
def detect_dpkg_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect installed Debian package using dpkg-query."""
    try:
        res = subprocess.run(
            ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Status}\n", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode != 0 or not res.stdout:
            return None

        line = res.stdout.strip().splitlines()[0]
        parts = line.split("\t")
        if len(parts) < 3:
            return None

        pkg_name = parts[0].strip()
        version = parts[1].strip()
        status = parts[2].strip()

        if "install ok installed" not in status:
            return None

        # Look up install date from /var/lib/dpkg/info/<pkg>.list
        mtime_val = None
        info_dir = "/var/lib/dpkg/info"
        list_file = os.path.join(info_dir, f"{pkg_name}.list")
        if os.path.exists(list_file):
            try:
                mtime_val = os.path.getmtime(list_file)
            except OSError:
                pass
        else:
            # Check architecture-qualified files (e.g. pkg:amd64.list)
            try:
                for f in os.listdir(info_dir):
                    if f.startswith(f"{pkg_name}:") and f.endswith(".list"):
                        mtime_val = os.path.getmtime(os.path.join(info_dir, f))
                        break
            except Exception:
                pass

        return {
            "source_type": "Debian Package",
            "source_icon": "📦",
            "name": pkg_name,
            "version": version,
            "location": f"dpkg ({pkg_name})",
            "install_date": format_mtime(mtime_val),
            "source_order": 2,
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 3. APT Catalog (Candidate Version)
# ------------------------------------------------------------------------------
def detect_apt_catalog_version(name: str) -> Optional[Dict[str, Any]]:
    """Query available repository candidate version via apt-cache policy."""
    try:
        res = subprocess.run(
            ["apt-cache", "policy", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=4,
        )
        if res.returncode != 0 or not res.stdout:
            return None

        candidate = ""
        for line in res.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("Candidate:"):
                candidate = line_str.replace("Candidate:", "").strip()
                break

        if not candidate or candidate == "(none)":
            return None

        return {
            "source_type": "APT Catalog",
            "source_icon": "📋",
            "name": name,
            "version": candidate,
            "location": "Repository catalog",
            "install_date": "N/A (Available in repos)",
            "source_order": 3,
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 4. Snap Package
# ------------------------------------------------------------------------------
def detect_snap_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect installed Snap application."""
    if not shutil.which("snap"):
        return None

    try:
        res = subprocess.run(
            ["snap", "list", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode != 0 or not res.stdout:
            return None

        lines = res.stdout.strip().splitlines()
        if len(lines) < 2:
            return None

        # Parse data row
        parts = lines[1].split()
        if len(parts) < 2:
            return None

        snap_name = parts[0].strip()
        version = parts[1].strip()

        # Check /snap/<name>/current timestamp
        mtime_val = None
        snap_path = f"/snap/{snap_name}/current"
        if os.path.exists(snap_path):
            try:
                mtime_val = os.path.getmtime(snap_path)
            except OSError:
                pass

        return {
            "source_type": "Snap",
            "source_icon": "🟢",
            "name": snap_name,
            "version": version,
            "location": f"snap ({snap_name})",
            "install_date": format_mtime(mtime_val),
            "source_order": 4,
        }
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 5. Flatpak Application
# ------------------------------------------------------------------------------
def detect_flatpak_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect installed Flatpak application."""
    if not shutil.which("flatpak"):
        return None

    try:
        # Try direct flatpak info <name>
        res = subprocess.run(
            ["flatpak", "info", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout:
            version = ""
            app_id = name
            for line in res.stdout.splitlines():
                line_str = line.strip()
                if line_str.startswith("Version:"):
                    version = line_str.replace("Version:", "").strip()
                elif line_str.startswith("Ref:"):
                    app_id = line_str.replace("Ref:", "").strip()

            if version:
                return {
                    "source_type": "Flatpak",
                    "source_icon": "🟣",
                    "name": name,
                    "version": version,
                    "location": f"flatpak ({app_id})",
                    "install_date": "N/A",
                    "source_order": 5,
                }

        # Fallback: scan flatpak list --app
        res_list = subprocess.run(
            ["flatpak", "list", "--app", "--columns=name,application,version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res_list.returncode == 0 and res_list.stdout:
            q_lower = name.lower()
            for line in res_list.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) < 2:
                    parts = line.split()
                if not parts:
                    continue
                app_title = parts[0].strip()
                app_ref = parts[1].strip() if len(parts) > 1 else app_title
                ver_val = parts[2].strip() if len(parts) > 2 else ""

                if (
                    q_lower == app_title.lower()
                    or q_lower == app_ref.lower()
                    or (app_ref.lower().endswith(f".{q_lower}"))
                ):
                    return {
                        "source_type": "Flatpak",
                        "source_icon": "🟣",
                        "name": app_title,
                        "version": ver_val or "Installed",
                        "location": f"flatpak ({app_ref})",
                        "install_date": "N/A",
                        "source_order": 5,
                    }
        return None
    except Exception:
        return None


# ------------------------------------------------------------------------------
# 6. Python Library
# ------------------------------------------------------------------------------
def detect_python_library_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect installed Python library via importlib.metadata."""
    candidates = [
        name,
        name.lower(),
        name.replace("-", "_"),
        name.replace("_", "-"),
    ]
    # Remove duplicates preserving order
    seen = set()
    clean_candidates = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            clean_candidates.append(c)

    dist = None
    for cand in clean_candidates:
        try:
            dist = importlib.metadata.distribution(cand)
            break
        except (importlib.metadata.PackageNotFoundError, ValueError):
            continue

    if not dist:
        return None

    ver = dist.version
    mtime_val = None
    location = "Python site-packages"

    if hasattr(dist, "_path") and dist._path:
        dist_path = str(dist._path)
        location = dist_path
        if os.path.exists(dist_path):
            try:
                mtime_val = os.path.getmtime(dist_path)
            except OSError:
                pass

    return {
        "source_type": "Python Library",
        "source_icon": "🐍",
        "name": dist.metadata.get("Name", name),
        "version": ver,
        "location": location,
        "install_date": format_mtime(mtime_val),
        "source_order": 6,
    }


# ------------------------------------------------------------------------------
# 7. Node.js Library
# ------------------------------------------------------------------------------
def detect_node_library_version(name: str) -> Optional[Dict[str, Any]]:
    """Inspect installed Node.js package in global npm or local node_modules."""
    search_dirs: List[str] = []

    # 1. Local project node_modules
    local_pkg = os.path.abspath(os.path.join("node_modules", name, "package.json"))
    if os.path.isfile(local_pkg):
        search_dirs.append(local_pkg)

    # 2. Global npm root
    if shutil.which("npm"):
        try:
            res = subprocess.run(
                ["npm", "root", "-g"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                g_root = res.stdout.strip()
                g_pkg = os.path.join(g_root, name, "package.json")
                if os.path.isfile(g_pkg):
                    search_dirs.append(g_pkg)
        except Exception:
            pass

    # 3. Standard system node_modules paths
    common_node_paths = [
        f"/usr/lib/node_modules/{name}/package.json",
        f"/usr/local/lib/node_modules/{name}/package.json",
    ]
    for p in common_node_paths:
        if os.path.isfile(p) and p not in search_dirs:
            search_dirs.append(p)

    for pkg_json_path in search_dirs:
        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("version", "")
            if version:
                mtime_val = None
                try:
                    mtime_val = os.path.getmtime(pkg_json_path)
                except OSError:
                    pass

                return {
                    "source_type": "Node.js Library",
                    "source_icon": "📦",
                    "name": data.get("name", name),
                    "version": version,
                    "location": os.path.dirname(pkg_json_path),
                    "install_date": format_mtime(mtime_val),
                    "source_order": 7,
                }
        except Exception:
            continue

    return None


# ------------------------------------------------------------------------------
# Master Collector
# ------------------------------------------------------------------------------
def collect_all_versions(name: str) -> List[Dict[str, Any]]:
    """
    Collect versions across all 7 sources in exact order:
      1. Executable on PATH (Binary)
      2. Installed Debian Package (dpkg)
      3. APT Catalog (Candidate)
      4. Snap Package
      5. Flatpak Application
      6. Python Library
      7. Node.js Library
    """
    target = name.strip()
    if not target:
        return []

    matches: List[Dict[str, Any]] = []

    # 1. Executable on PATH
    binary_match = detect_executable_version(target)
    if binary_match:
        matches.append(binary_match)

    # 2. Installed Debian Package
    dpkg_match = detect_dpkg_version(target)
    if dpkg_match:
        matches.append(dpkg_match)

    # 3. APT Catalog
    apt_match = detect_apt_catalog_version(target)
    if apt_match:
        matches.append(apt_match)

    # 4. Snap Package
    snap_match = detect_snap_version(target)
    if snap_match:
        matches.append(snap_match)

    # 5. Flatpak Application
    flatpak_match = detect_flatpak_version(target)
    if flatpak_match:
        matches.append(flatpak_match)

    # 6. Python Library
    python_match = detect_python_library_version(target)
    if python_match:
        matches.append(python_match)

    # 7. Node.js Library
    node_match = detect_node_library_version(target)
    if node_match:
        matches.append(node_match)

    return matches


# ------------------------------------------------------------------------------
# UI Rendering
# ------------------------------------------------------------------------------
def render_version_results(
    console: Console,
    name: str,
    matches: List[Dict[str, Any]],
) -> None:
    """Render a single, clean Rich card displaying all matches or friendly not-found guidance."""
    clean_name = name.strip()

    if not matches:
        # Not-found card with actionable guidance
        guidance_table = Table(box=None, show_header=False, padding=(0, 1))
        guidance_table.add_column("Icon", style="bold yellow", width=3)
        guidance_table.add_column("Advice", style="white")
        guidance_table.add_row("🔍", f"Search available software packages: [bold green]ez package-search {clean_name}[/bold green]")
        guidance_table.add_row("📋", f"List installed system packages: [bold green]ez installed-packages[/bold green]")
        guidance_table.add_row("💡", "Check spelling or inspect library environments ([dim]pip list[/dim] or [dim]npm list[/dim]).")

        body = Table(box=None, show_header=False, padding=(0, 0))
        body.add_column("Content")
        body.add_row(f"[bold red]❌ No matches found for '{clean_name}'[/bold red]\n")
        body.add_row(f"[dim]Scanned executable binaries on PATH, Debian dpkg packages, APT catalog, Snaps, Flatpaks, Python libraries, and Node.js libraries.[/dim]\n")
        body.add_row(guidance_table)

        console.print(
            Panel(
                body,
                title=f"[bold yellow]ℹ️ Version Check: {clean_name}[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        return

    # Results Table
    res_table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        padding=(0, 1),
    )
    res_table.add_column("Source Type", style="bold white", width=20)
    res_table.add_column("Detected Version", style="bold green", width=26)
    res_table.add_column("Identifier / Location", style="dim", width=30)
    res_table.add_column("Install Date", style="cyan", width=18)

    for item in matches:
        src_label = f"{item['source_icon']} {item['source_type']}"
        res_table.add_row(
            src_label,
            item["version"],
            item["location"],
            item["install_date"],
        )

    count_str = f"{len(matches)} source{'s' if len(matches) > 1 else ''}"
    header_info = f"[bold cyan]Software Item:[/bold cyan] [bold white]{clean_name}[/bold white] [dim]({count_str} detected)[/dim]\n"

    content = Table(box=None, show_header=False, padding=(0, 0))
    content.add_column("Body")
    content.add_row(header_info)
    content.add_row(res_table)
    content.add_row("\n[dim]💡 Tip: All version lookups are strictly read-only and require zero admin privileges.[/dim]")

    console.print(
        Panel(
            content,
            title=f"[bold cyan]ℹ️ Version Information: {clean_name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def run_version_command(
    name: Optional[str] = None,
    console: Optional[Console] = None,
) -> None:
    """
    Main entrypoint for 'ez version [name]'.
    - With no argument: Displays EasyCLI's own version + one-line tip.
    - With argument: Auto-detects and displays version across all 7 sources.
    """
    console = console or Console()
    target = (name or "").strip()

    # 1. No argument -> Show EasyCLI's version and friendly usage hint
    if not target:
        console.print(f"EasyCLI (ez) v{__version__} [dim](Safe Automatic Elevation)[/dim]")
        console.print("[dim]💡 Tip: Check the version of any app, package, or library with '[bold cyan]ez version <name>[/bold cyan]'[/dim]")
        return

    # 2. Argument provided -> Detect across all sources with spinner
    with console.status(f"[bold cyan]Checking version for '{target}' across all sources...[/bold cyan]", spinner="dots"):
        matches = collect_all_versions(target)

    render_version_results(console, target, matches)
