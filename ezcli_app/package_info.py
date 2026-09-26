"""
Unified Package & App Information Subcommand ('ez package-info [name]').

App-store style package inspection checking local system and remote stores simultaneously:
- Local offline sources: dpkg/apt, snap, flatpak, pip, npm global, and PATH binaries.
- Store & catalog sources: APT repository, Snap Store, Flathub.
- Loose name resolution: exact match, substring, and fuzzy matching with chooser.
- Nature classification: Desktop App, CLI Tool, Library, Service.
- Context-aware result cards: Installed card vs Store card with safe actions.
- Safe elevation with impact preview and dependency removal preview.
- No-argument hub mode: My Installed Apps, Available Updates, Search/Inspect.
"""

import datetime
import difflib
import glob
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

from .collectors import format_bytes, run_command_safe
from .elevation import elevated_package_install, elevated_package_uninstall


# ==============================================================================
# Data Models
# ==============================================================================
@dataclass
class PackageSourceInfo:
    """Detailed information from a specific software source."""
    source_type: str        # "dpkg", "snap", "flatpak", "pip", "npm", "binary", "apt_store", "snap_store", "flathub"
    source_name: str        # "APT 📦", "Snap 🟢", "Flatpak 🟣", "Python Pip 🐍", "Node npm 📦", "Binary 🖥️", "Flathub 🟣", "Snap Store 🟢"
    source_icon: str        # 📦, 🟢, 🟣, 🐍, 🖥️
    is_installed: bool
    name: str = ""
    app_id: str = ""
    version: str = ""
    installed_size: str = ""
    download_size: str = ""
    summary: str = ""
    description: str = ""
    homepage: str = ""
    maintainer: str = ""
    location: str = ""
    desktop_file: str = ""
    section: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class PackageCandidate:
    """A matched package candidate across one or more sources."""
    name: str
    nature: str             # "Desktop App", "CLI Tool", "Library", "Service"
    nature_icon: str        # 🖥️, ⌨️, 📚, ⚙️
    is_installed: bool
    sources: List[PackageSourceInfo] = field(default_factory=list)
    summary: str = ""
    primary_version: str = ""
    match_score: int = 0    # 100=exact, 75=case-exact, 50=prefix/suffix, 30=substring, 10=fuzzy


# ==============================================================================
# Nature Detection Helper
# ==============================================================================
def detect_package_nature(name: str, sources: List[PackageSourceInfo]) -> Tuple[str, str]:
    """
    Determine the primary nature of a package:
    - Desktop App: Has .desktop file or Flatpak GUI app
    - CLI Tool: Executable on PATH and not purely a desktop app
    - Library: Python module, Node module, or system development library
    - Service: Systemd service unit exists
    Returns (nature_label, nature_icon).
    """
    name_clean = name.lower()

    # 1. Desktop Application check
    desktop_dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        "/var/lib/flatpak/exports/share/applications",
        "/var/lib/snapd/desktop/applications",
    ]
    for d in desktop_dirs:
        if os.path.isdir(d):
            # Check for direct desktop file match
            pattern = os.path.join(d, f"*{name_clean}*.desktop")
            matches = glob.glob(pattern)
            if matches:
                return "Desktop App", "🖥️"

    for s in sources:
        if s.source_type in ("flatpak", "flathub") and ("." in s.app_id or s.is_installed):
            return "Desktop App", "🖥️"
        if s.desktop_file:
            return "Desktop App", "🖥️"

    # 2. System Service check
    service_dirs = [
        "/etc/systemd/system",
        "/lib/systemd/system",
        "/usr/lib/systemd/system",
    ]
    for sd in service_dirs:
        svc_path = os.path.join(sd, f"{name_clean}.service")
        if os.path.exists(svc_path):
            return "Service", "⚙️"

    # 3. Library check
    for s in sources:
        if s.source_type in ("pip", "npm"):
            return "Library", "📚"
        sec = s.section.lower()
        if sec in ("libs", "libdevel", "python", "perl", "ruby", "devel", "javascript"):
            return "Library", "📚"

    if (
        name_clean.startswith("lib")
        or name_clean.startswith("python3-")
        or name_clean.startswith("node-")
        or name_clean.endswith("-dev")
        or name_clean.endswith("-devel")
    ):
        return "Library", "📚"

    # 4. CLI Tool check
    if shutil.which(name) or any(s.source_type == "binary" for s in sources):
        return "CLI Tool", "⌨️"

    # Default based on sources
    for s in sources:
        if s.source_type in ("dpkg", "apt_store"):
            if "util" in s.section.lower() or "admin" in s.section.lower() or "net" in s.section.lower():
                return "CLI Tool", "⌨️"

    return "Application", "📦"


# ==============================================================================
# Local Offline Collectors
# ==============================================================================
def collect_local_dpkg(query: str) -> List[PackageSourceInfo]:
    """Query locally installed Debian packages via dpkg-query (offline)."""
    results: List[PackageSourceInfo] = []
    q_lower = query.lower()

    # Exact check first via dpkg-query
    rc, out, _ = run_command_safe(
        ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\t${Section}\t${Status}\n", query],
        timeout=3,
    )
    if rc == 0 and out.strip():
        for line in out.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5 and "installed" in parts[4].lower() and "not-installed" not in parts[4].lower():
                pkg_name, ver, sz_kb, sec, _ = parts[:5]
                size_str = ""
                if sz_kb and sz_kb.isdigit():
                    size_str = format_bytes(int(sz_kb) * 1024)

                # Get description and homepage via dpkg -s
                desc = ""
                homepage = ""
                maint = ""
                rc_s, out_s, _ = run_command_safe(["dpkg", "-s", pkg_name], timeout=2)
                if rc_s == 0 and out_s:
                    for s_line in out_s.splitlines():
                        if s_line.startswith("Description:"):
                            desc = s_line.split(":", 1)[1].strip()
                        elif s_line.startswith("Homepage:"):
                            homepage = s_line.split(":", 1)[1].strip()
                        elif s_line.startswith("Maintainer:"):
                            maint = s_line.split(":", 1)[1].strip()

                results.append(
                    PackageSourceInfo(
                        source_type="dpkg",
                        source_name="APT",
                        source_icon="📦",
                        is_installed=True,
                        name=pkg_name,
                        app_id=pkg_name,
                        version=ver,
                        installed_size=size_str,
                        summary=desc,
                        description=desc,
                        homepage=homepage,
                        maintainer=maint,
                        section=sec,
                    )
                )

    # If query is a substring search, scan installed packages
    if not results:
        rc_all, out_all, _ = run_command_safe(
            ["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Installed-Size}\t${Section}\t${Status}\n"],
            timeout=5,
        )
        if rc_all == 0 and out_all:
            for line in out_all.splitlines():
                parts = line.split("\t")
                if len(parts) >= 5 and "installed" in parts[4].lower() and "not-installed" not in parts[4].lower():
                    pkg_name = parts[0].strip()
                    if q_lower in pkg_name.lower():
                        ver = parts[1].strip()
                        sz_kb = parts[2].strip()
                        sec = parts[3].strip()
                        size_str = format_bytes(int(sz_kb) * 1024) if sz_kb.isdigit() else ""
                        results.append(
                            PackageSourceInfo(
                                source_type="dpkg",
                                source_name="APT",
                                source_icon="📦",
                                is_installed=True,
                                name=pkg_name,
                                app_id=pkg_name,
                                version=ver,
                                installed_size=size_str,
                                section=sec,
                            )
                        )
                        if len(results) >= 20:
                            break

    return results


def collect_local_snap(query: str) -> List[PackageSourceInfo]:
    """Query locally installed snaps via snap list (offline)."""
    if not shutil.which("snap"):
        return []

    results: List[PackageSourceInfo] = []
    rc, out, _ = run_command_safe(["snap", "list"], timeout=4)
    if rc != 0 or not out.strip():
        return []

    q_lower = query.lower()
    for line in out.strip().splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            snap_name = parts[0].strip()
            ver = parts[1].strip()
            if snap_name.lower() == q_lower or q_lower in snap_name.lower():
                results.append(
                    PackageSourceInfo(
                        source_type="snap",
                        source_name="Snap",
                        source_icon="🟢",
                        is_installed=True,
                        name=snap_name,
                        app_id=snap_name,
                        version=ver,
                        summary=f"Snap package '{snap_name}'",
                    )
                )

    return results


def collect_local_flatpak(query: str) -> List[PackageSourceInfo]:
    """Query locally installed Flatpaks via flatpak list (offline)."""
    if not shutil.which("flatpak"):
        return []

    results: List[PackageSourceInfo] = []
    rc, out, _ = run_command_safe(
        ["flatpak", "list", "--app", "--columns=application,version,size,description,name"],
        timeout=4,
    )
    if rc != 0 or not out.strip():
        return []

    q_lower = query.lower()
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 1:
            app_id = parts[0].strip()
            ver = parts[1].strip() if len(parts) > 1 else ""
            size = parts[2].strip() if len(parts) > 2 else ""
            desc = parts[3].strip() if len(parts) > 3 else ""
            friendly_name = parts[4].strip() if len(parts) > 4 else app_id

            id_lower = app_id.lower()
            name_lower = friendly_name.lower()
            if q_lower == id_lower or q_lower == name_lower or q_lower in id_lower or q_lower in name_lower:
                results.append(
                    PackageSourceInfo(
                        source_type="flatpak",
                        source_name="Flatpak",
                        source_icon="🟣",
                        is_installed=True,
                        name=friendly_name or app_id,
                        app_id=app_id,
                        version=ver,
                        installed_size=size,
                        summary=desc,
                        description=desc,
                    )
                )

    return results


def collect_local_pip(query: str) -> List[PackageSourceInfo]:
    """Query installed Python distributions via importlib.metadata (offline)."""
    results: List[PackageSourceInfo] = []
    q_lower = query.lower()

    try:
        for dist in importlib.metadata.distributions():
            dist_name = dist.metadata.get("Name", "")
            if not dist_name:
                continue
            d_lower = dist_name.lower()
            if d_lower == q_lower or q_lower in d_lower:
                summary = dist.metadata.get("Summary", "")
                homepage = dist.metadata.get("Home-page", "") or dist.metadata.get("Project-URL", "")
                author = dist.metadata.get("Author", "") or dist.metadata.get("Author-email", "")
                results.append(
                    PackageSourceInfo(
                        source_type="pip",
                        source_name="Python Pip",
                        source_icon="🐍",
                        is_installed=True,
                        name=dist_name,
                        app_id=dist_name,
                        version=dist.version,
                        summary=summary,
                        description=summary,
                        homepage=homepage,
                        maintainer=author,
                        section="python",
                    )
                )
                if len(results) >= 10:
                    break
    except Exception:
        pass

    return results


def collect_local_npm(query: str) -> List[PackageSourceInfo]:
    """Query globally installed Node npm packages via npm list -g --depth=0 --json (offline)."""
    if not shutil.which("npm"):
        return []

    results: List[PackageSourceInfo] = []
    q_lower = query.lower()

    rc, out, _ = run_command_safe(["npm", "list", "-g", "--depth=0", "--json"], timeout=4)
    if rc == 0 and out.strip():
        try:
            data = json.loads(out)
            deps = data.get("dependencies", {})
            for mod_name, mod_info in deps.items():
                m_lower = mod_name.lower()
                if m_lower == q_lower or q_lower in m_lower:
                    ver = mod_info.get("version", "") if isinstance(mod_info, dict) else str(mod_info)
                    results.append(
                        PackageSourceInfo(
                            source_type="npm",
                            source_name="Node npm",
                            source_icon="📦",
                            is_installed=True,
                            name=mod_name,
                            app_id=mod_name,
                            version=ver,
                            summary=f"Global npm module '{mod_name}'",
                            section="javascript",
                        )
                    )
        except Exception:
            pass

    return results


def collect_local_binary(query: str) -> List[PackageSourceInfo]:
    """Check PATH for an executable binary (offline)."""
    bin_path = shutil.which(query)
    if not bin_path or not os.path.isfile(bin_path):
        return []

    detected_ver = ""
    candidate_flags = ["--version", "-v", "-V", "version"]
    for flag in candidate_flags:
        rc, out, err = run_command_safe([bin_path, flag], timeout=2)
        combined = f"{out}\n{err}".strip()
        m = re.search(r"\b(\d+\.\d+(?:\.\d+)*(?:[-.+][a-zA-Z0-9_.~]+)?)\b", combined)
        if m:
            detected_ver = m.group(1).rstrip("),;:-_")
            break

    sz_str = ""
    try:
        sz_bytes = os.path.getsize(bin_path)
        sz_str = format_bytes(sz_bytes)
    except Exception:
        pass

    return [
        PackageSourceInfo(
            source_type="binary",
            source_name="Binary Executable",
            source_icon="🖥️",
            is_installed=True,
            name=os.path.basename(bin_path),
            app_id=os.path.basename(bin_path),
            version=detected_ver or "Detected on PATH",
            installed_size=sz_str,
            location=bin_path,
            summary=f"System executable located at {bin_path}",
        )
    ]


# ==============================================================================
# Store & Catalog Collectors (Network-Aware)
# ==============================================================================
def collect_store_apt(query: str) -> List[PackageSourceInfo]:
    """Search APT repository catalog via apt-cache search / apt show."""
    results: List[PackageSourceInfo] = []
    q_lower = query.lower()

    # 1. Exact query via apt-cache show
    rc_show, out_show, _ = run_command_safe(["apt-cache", "show", query], timeout=6)
    if rc_show == 0 and out_show.strip():
        current: Dict[str, str] = {}
        for line in out_show.splitlines():
            if line.startswith("Package:"):
                if current.get("Package"):
                    break
                current["Package"] = line.split(":", 1)[1].strip()
            elif line.startswith("Version:") and not current.get("Version"):
                current["Version"] = line.split(":", 1)[1].strip()
            elif (line.startswith("Size:") or line.startswith("Download-Size:")) and not current.get("Size"):
                current["Size"] = line.split(":", 1)[1].strip()
            elif line.startswith("Section:") and not current.get("Section"):
                current["Section"] = line.split(":", 1)[1].strip()
            elif line.startswith("Description:") and not current.get("Description"):
                current["Description"] = line.split(":", 1)[1].strip()
            elif line.startswith("Homepage:") and not current.get("Homepage"):
                current["Homepage"] = line.split(":", 1)[1].strip()
            elif line.startswith("Maintainer:") and not current.get("Maintainer"):
                current["Maintainer"] = line.split(":", 1)[1].strip()

        if current.get("Package"):
            pkg_name = current["Package"]
            sz_val = current.get("Size", "")
            if sz_val.isdigit():
                sz_val = format_bytes(int(sz_val))

            results.append(
                PackageSourceInfo(
                    source_type="apt_store",
                    source_name="APT Repository",
                    source_icon="📦",
                    is_installed=False,
                    name=pkg_name,
                    app_id=pkg_name,
                    version=current.get("Version", ""),
                    download_size=sz_val,
                    summary=current.get("Description", ""),
                    description=current.get("Description", ""),
                    homepage=current.get("Homepage", ""),
                    maintainer=current.get("Maintainer", ""),
                    section=current.get("Section", ""),
                )
            )

    # 2. Substring search if exact match wasn't found or as additional candidates
    if not results:
        rc_srch, out_srch, _ = run_command_safe(["apt-cache", "search", query], timeout=6)
        if rc_srch == 0 and out_srch.strip():
            for line in out_srch.strip().splitlines():
                if " - " in line:
                    p_name, p_desc = line.split(" - ", 1)
                    p_name = p_name.strip()
                    if q_lower in p_name.lower():
                        results.append(
                            PackageSourceInfo(
                                source_type="apt_store",
                                source_name="APT Repository",
                                source_icon="📦",
                                is_installed=False,
                                name=p_name,
                                app_id=p_name,
                                summary=p_desc.strip(),
                                description=p_desc.strip(),
                            )
                        )
                        if len(results) >= 15:
                            break

    return results


def collect_store_snap(query: str) -> List[PackageSourceInfo]:
    """Search Snap Store via snap find (network required)."""
    if not shutil.which("snap"):
        return []

    results: List[PackageSourceInfo] = []
    rc, out, _ = run_command_safe(["snap", "find", query], timeout=8)
    if rc == 0 and out.strip():
        lines = out.strip().splitlines()
        if len(lines) > 1:
            for line in lines[1:]:
                line_clean = line.strip()
                if not line_clean or "no matching" in line_clean.lower() or "error" in line_clean.lower():
                    continue
                parts = line_clean.split()
                if len(parts) >= 3:
                    s_name = parts[0].strip()
                    s_ver = parts[1].strip()
                    s_desc = " ".join(parts[3:]) if len(parts) > 3 else ""
                    results.append(
                        PackageSourceInfo(
                            source_type="snap_store",
                            source_name="Snap Store",
                            source_icon="🟢",
                            is_installed=False,
                            name=s_name,
                            app_id=s_name,
                            version=s_ver,
                            summary=s_desc,
                            description=s_desc,
                        )
                    )
                    if len(results) >= 10:
                        break

    return results


def collect_store_flatpak(query: str) -> List[PackageSourceInfo]:
    """Search Flathub repository via flatpak search (network required)."""
    if not shutil.which("flatpak"):
        return []

    results: List[PackageSourceInfo] = []
    rc, out, _ = run_command_safe(
        ["flatpak", "search", query, "--columns=application,version,branch,remotes,description,name"],
        timeout=8,
    )
    if rc == 0 and out.strip():
        for line in out.strip().splitlines():
            line_clean = line.strip()
            if not line_clean or "no matches found" in line_clean.lower() or "error" in line_clean.lower():
                continue
            parts = line_clean.split("\t")
            if len(parts) >= 1:
                app_id = parts[0].strip()
                if not app_id or "no matches found" in app_id.lower():
                    continue
                ver = parts[1].strip() if len(parts) > 1 else ""
                desc = parts[4].strip() if len(parts) > 4 else ""
                friendly = parts[5].strip() if len(parts) > 5 else app_id
                results.append(
                    PackageSourceInfo(
                        source_type="flathub",
                        source_name="Flathub",
                        source_icon="🟣",
                        is_installed=False,
                        name=friendly or app_id,
                        app_id=app_id,
                        version=ver,
                        summary=desc,
                        description=desc,
                    )
                )
                if len(results) >= 10:
                    break

    return results


# ==============================================================================
# Master Package Info Resolver
# ==============================================================================
def resolve_package_info(query: str) -> Tuple[List[PackageCandidate], bool, str]:
    """
    Simultaneously query local machine (offline) and remote stores (online).
    Performs loose matching:
      1. Exact match across sources
      2. Substring matches
      3. Fuzzy matches
    Returns (candidates, store_available, store_note).
    """
    clean_query = (query or "").strip()
    if not clean_query:
        return [], True, ""

    q_lower = clean_query.lower()
    local_sources: List[PackageSourceInfo] = []
    store_sources: List[PackageSourceInfo] = []
    store_available = True
    store_note = ""

    # 1. Local machine collection (always works offline)
    local_sources.extend(collect_local_dpkg(clean_query))
    local_sources.extend(collect_local_snap(clean_query))
    local_sources.extend(collect_local_flatpak(clean_query))
    local_sources.extend(collect_local_pip(clean_query))
    local_sources.extend(collect_local_npm(clean_query))
    local_sources.extend(collect_local_binary(clean_query))

    # 2. Store & catalog collection (network-aware)
    try:
        apt_remote = collect_store_apt(clean_query)
        store_sources.extend(apt_remote)
    except Exception as e:
        store_available = False
        store_note = f"APT catalog query failed: {e}"

    try:
        snap_remote = collect_store_snap(clean_query)
        store_sources.extend(snap_remote)
    except Exception:
        pass

    try:
        flatpak_remote = collect_store_flatpak(clean_query)
        store_sources.extend(flatpak_remote)
    except Exception:
        pass

    # If all store sources came back empty and offline
    if not store_sources and not store_note:
        # Check basic socket or reachability quickly
        import socket
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1.0).close()
        except Exception:
            store_available = False
            store_note = "Online stores are unreachable (system appears offline). Displaying local offline results."

    # 3. Group sources by canonical name / app_id
    grouped: Dict[str, List[PackageSourceInfo]] = {}
    for s in local_sources + store_sources:
        canon_key = s.name.strip()
        if not canon_key:
            canon_key = s.app_id.strip()
        if not canon_key:
            continue

        # Normalize key for grouping: if exact app name matches
        match_key = canon_key.lower()
        # Find existing group key that matches closely
        found_key = None
        for k in grouped:
            if k.lower() == match_key:
                found_key = k
                break
        if not found_key:
            found_key = canon_key
            grouped[found_key] = []
        grouped[found_key].append(s)

    # 4. Rank each candidate group
    candidates: List[PackageCandidate] = []
    for canon_name, src_list in grouped.items():
        c_lower = canon_name.lower()
        is_installed = any(s.is_installed for s in src_list)
        nature, n_icon = detect_package_nature(canon_name, src_list)

        # Determine match score
        if c_lower == q_lower:
            score = 100
        elif c_lower.startswith(q_lower) or c_lower.endswith(q_lower):
            score = 60
        elif q_lower in c_lower:
            score = 40
        else:
            ratio = difflib.SequenceMatcher(None, q_lower, c_lower).ratio()
            score = int(ratio * 30)

        # Bonus score for installed packages
        if is_installed:
            score += 15

        # Best summary and version
        summary = ""
        version = ""
        for s in src_list:
            if s.is_installed and s.version and not version:
                version = s.version
            if s.summary and not summary:
                summary = s.summary
            if s.description and not summary:
                summary = s.description

        if not version:
            for s in src_list:
                if s.version:
                    version = s.version
                    break

        candidates.append(
            PackageCandidate(
                name=canon_name,
                nature=nature,
                nature_icon=n_icon,
                is_installed=is_installed,
                sources=src_list,
                summary=summary or f"Software item '{canon_name}'",
                primary_version=version,
                match_score=score,
            )
        )

    # Sort candidates by score descending
    candidates.sort(key=lambda c: c.match_score, reverse=True)

    return candidates, store_available, store_note


# ==============================================================================
# Action Handlers (Safe Elevation & Preview)
# ==============================================================================
def preview_apt_removal_impact(pkg_name: str) -> Dict[str, Any]:
    """
    Run apt-get remove -s to preview exactly what packages and auto-installed
    dependencies will be removed without making modifications.
    """
    result = {
        "packages_to_remove": [],
        "autoremove_packages": [],
        "summary": "",
        "error": "",
    }
    rc, out, err = run_command_safe(["apt-get", "remove", "-s", pkg_name], timeout=15)
    if rc != 0 and not out:
        result["error"] = err or "Simulation check failed."
        return result

    in_to_remove = False
    in_autoremove = False
    for line in out.splitlines():
        line_clean = line.strip()
        if "The following packages will be REMOVED:" in line:
            in_to_remove = True
            in_autoremove = False
            continue
        elif "The following packages were automatically installed and are no longer required:" in line:
            in_autoremove = True
            in_to_remove = False
            continue
        elif line_clean.endswith("not upgraded."):
            result["summary"] = line_clean
            in_to_remove = False
            in_autoremove = False
            continue

        if in_to_remove:
            if line_clean and not line_clean.startswith("Use ") and not line_clean.startswith("0 upgraded"):
                for p in line_clean.split():
                    if p and p not in result["packages_to_remove"]:
                        result["packages_to_remove"].append(p)
            else:
                in_to_remove = False

        if in_autoremove:
            if line_clean and not line_clean.startswith("Use ") and not line_clean.startswith("The following"):
                for p in line_clean.split():
                    if p and p not in result["autoremove_packages"]:
                        result["autoremove_packages"].append(p)
            else:
                in_autoremove = False

    return result


def execute_uninstall_action(console: Console, candidate: PackageCandidate) -> None:
    """Execute safe uninstallation with dependency preview and elevation guardrails."""
    # Find installed source
    inst_sources = [s for s in candidate.sources if s.is_installed]
    if not inst_sources:
        console.print(f"[yellow]'{candidate.name}' is not currently installed.[/yellow]")
        return

    src = inst_sources[0]
    plat = src.source_type
    pkg_id = src.app_id or src.name

    # 1. Dependency and impact preview
    console.print()
    impact_table = Table(box=None, show_header=False, padding=(0, 1))
    impact_table.add_column("Key", style="bold cyan", width=18)
    impact_table.add_column("Value", style="white")

    impact_table.add_row("Target Software", f"[bold red]{candidate.name}[/bold red]")
    impact_table.add_row("Package Manager", f"{src.source_icon} {src.source_name}")
    impact_table.add_row("Installed Version", src.version or "[dim]N/A[/dim]")
    if src.installed_size:
        impact_table.add_row("Space Freed", src.installed_size)

    # For APT, run dry-run to display dependency preview
    if plat == "dpkg":
        with console.status("[bold cyan]Analyzing package removal dependencies...[/bold cyan]", spinner="dots"):
            apt_prev = preview_apt_removal_impact(pkg_id)

        to_remove = apt_prev["packages_to_remove"]
        auto_remove = apt_prev["autoremove_packages"]

        if to_remove:
            rem_list = ", ".join(to_remove[:10])
            if len(to_remove) > 10:
                rem_list += f" [dim](and {len(to_remove) - 10} more)[/dim]"
            impact_table.add_row("Packages Removed", f"[bold yellow]{rem_list}[/bold yellow]")

        if auto_remove:
            auto_list = ", ".join(auto_remove[:8])
            if len(auto_remove) > 8:
                auto_list += f" [dim](and {len(auto_remove) - 8} orphaned dependencies)[/dim]"
            impact_table.add_row("Unused Dependencies", f"[dim]{auto_list}[/dim]")

        if apt_prev["summary"]:
            impact_table.add_row("Simulation Summary", f"[cyan]{apt_prev['summary']}[/cyan]")

    notice = (
        "\n[bold yellow]⚠️ IMPACT NOTICE:[/bold yellow]\n"
        "• This action removes executable binaries, application shortcuts, and desktop integration.\n"
        "• Personal documents and configuration files in your home folder are preserved.\n"
        "• Administrator privileges are required to perform this removal."
    )

    content = Table(box=None, show_header=False, padding=(0, 0))
    content.add_column("Body")
    content.add_row(impact_table)
    content.add_row(notice)

    console.print(
        Panel(
            content,
            title=f"[bold yellow]⚠️ Confirm Uninstallation: {candidate.name}[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # 2. Explicit confirmation
    approved = Confirm.ask(
        f"Are you sure you want to completely uninstall '[bold red]{candidate.name}[/bold red]'?",
        default=False,
    )
    if not approved:
        console.print("[yellow]Uninstallation cancelled by user.[/yellow]")
        return

    # 3. Elevated execution
    helper_plat = "apt" if plat == "dpkg" else plat
    with console.status(f"[bold cyan]Uninstalling '{pkg_id}' via {src.source_name}...[/bold cyan]", spinner="dots"):
        ok, _, err = elevated_package_uninstall(
            platform=helper_plat,
            package=pkg_id,
            skip_explanation=True,
            console=console,
        )

    if ok:
        console.print(
            Panel(
                f"✔ [bold green]Successfully uninstalled '{candidate.name}'![/bold green]\n\n"
                f"[dim]The application and its system dependencies have been cleanly removed.[/dim]",
                title=f"[bold green]Uninstallation Complete[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        src.is_installed = False
        candidate.is_installed = False
    else:
        console.print(
            Panel(
                f"[bold red]Failed to uninstall '{candidate.name}':[/bold red]\n\n{err or 'Unknown error.'}",
                title="[bold red]Uninstallation Error[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


def execute_install_action(console: Console, candidate: PackageCandidate) -> None:
    """Execute safe installation with runtime checks, impact preview, and elevation guardrails."""
    # Find available store sources
    avail_sources = [s for s in candidate.sources if not s.is_installed]
    if not avail_sources:
        console.print(f"[yellow]No store sources available to install '{candidate.name}'.[/yellow]")
        return

    # If multiple store sources exist, let user choose
    if len(avail_sources) > 1:
        console.print("[bold cyan]Multiple sources provide this package. Choose installation source:[/bold cyan]")
        for idx, s in enumerate(avail_sources, 1):
            console.print(f"  [bold yellow][{idx}][/bold yellow] {s.source_icon} [bold]{s.source_name}[/bold] ({s.app_id or s.name})")
        console.print()
        src_choice = Prompt.ask(f"Select source [1-{len(avail_sources)}] (or Enter to cancel)", default="").strip()
        if not src_choice or not src_choice.isdigit() or not (1 <= int(src_choice) <= len(avail_sources)):
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
        chosen = avail_sources[int(src_choice) - 1]
    else:
        chosen = avail_sources[0]

    # Map source type to helper platform
    plat_map = {"apt_store": "apt", "flathub": "flatpak", "snap_store": "snap"}
    plat = plat_map.get(chosen.source_type, "apt")
    pkg_id = chosen.app_id or chosen.name

    # Check runtime support
    if plat in ("flatpak", "snap") and not shutil.which(plat):
        console.print(f"\n[bold yellow]Notice:[/bold yellow] The [cyan]{chosen.source_name}[/cyan] runtime is not installed on this system.")
        enable_rt = Confirm.ask(f"Would you like EasyCLI to install {chosen.source_name} runtime first?", default=True)
        if not enable_rt:
            console.print("[yellow]Installation cancelled.[/yellow]")
            return
        rt_pkg = "flatpak" if plat == "flatpak" else "snapd"
        with console.status(f"[bold cyan]Installing {chosen.source_name} runtime via APT...[/bold cyan]", spinner="dots"):
            rt_ok, _, rt_err = elevated_package_install("apt", rt_pkg, console=console)
        if not rt_ok:
            console.print(f"[bold red]Failed to install runtime:[/bold red] {rt_err}")
            return

    # Impact preview
    console.print()
    install_table = Table(box=None, show_header=False, padding=(0, 1))
    install_table.add_column("Key", style="bold cyan", width=18)
    install_table.add_column("Value", style="white")
    install_table.add_row("Package", f"[bold green]{candidate.name}[/bold green]")
    install_table.add_row("Provider", f"{chosen.source_icon} {chosen.source_name}")
    if chosen.version:
        install_table.add_row("Version", chosen.version)
    if chosen.download_size:
        install_table.add_row("Download Size", chosen.download_size)
    if chosen.description:
        install_table.add_row("Description", chosen.description)

    console.print(
        Panel(
            install_table,
            title=f"[bold cyan]📥 Install Software: {candidate.name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    approved = Confirm.ask(
        f"Proceed with installing '[bold green]{candidate.name}[/bold green]' via {chosen.source_name}?",
        default=True,
    )
    if not approved:
        console.print("[yellow]Installation cancelled.[/yellow]")
        return

    with console.status(f"[bold cyan]Installing '{pkg_id}' via {chosen.source_name}...[/bold cyan]", spinner="dots"):
        ok, _, err = elevated_package_install(plat, pkg_id, console=console)

    if ok:
        console.print(
            Panel(
                f"✔ [bold green]Successfully installed '{candidate.name}' via {chosen.source_name}![/bold green]\n\n"
                f"[dim]The application is now installed and ready to run with [bold green]ez run {candidate.name}[/bold green].[/dim]",
                title=f"[bold green]{candidate.name} Installed[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        chosen.is_installed = True
        candidate.is_installed = True
    else:
        console.print(
            Panel(
                f"[bold red]Installation failed:[/bold red]\n\n{err or 'Unknown installation error.'}",
                title="[bold red]Installation Error[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


def execute_run_action(console: Console, candidate: PackageCandidate) -> None:
    """Hand over to existing ez run flow."""
    from .run_cli import run_cli_execute
    console.print(f"[bold cyan]Launching '{candidate.name}' via EasyCLI Universal Runner...[/bold cyan]\n")
    run_cli_execute(candidate.name, console=console)


# ==============================================================================
# UI Card Renderers
# ==============================================================================
def render_installed_card(console: Console, candidate: PackageCandidate, store_available: bool, store_note: str) -> None:
    """Render comprehensive card for an installed package with actions."""
    inst_sources = [s for s in candidate.sources if s.is_installed]
    source_badges = " ".join(f"[{s.source_icon} {s.source_name}]" for s in inst_sources)

    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    table.add_row("Status", "[bold green]✔ Installed on this machine[/bold green]")
    table.add_row("Classification", f"{candidate.nature_icon} [bold]{candidate.nature}[/bold]")
    table.add_row("Active Sources", source_badges)
    if candidate.primary_version:
        table.add_row("Version", f"[bold white]{candidate.primary_version}[/bold white]")

    # Installed sizes
    sizes = [s.installed_size for s in inst_sources if s.installed_size]
    if sizes:
        table.add_row("Installed Size", ", ".join(sizes))

    # Location / executable path
    locs = [s.location for s in inst_sources if s.location]
    if locs:
        table.add_row("Binary Path", locs[0])

    if candidate.summary:
        table.add_row("Summary", candidate.summary)

    # Online store comparison if available
    store_sources = [s for s in candidate.sources if not s.is_installed]
    if store_sources:
        store_badges = " ".join(f"[{s.source_icon} {s.source_name}]" for s in store_sources)
        table.add_row("Also Available In", f"[dim]{store_badges}[/dim]")
    elif not store_available and store_note:
        table.add_row("Store Status", f"[dim yellow]{store_note}[/dim yellow]")

    console.print(
        Panel(
            table,
            title=f"[bold green]✔ {candidate.name} ({candidate.nature_icon} {candidate.nature})[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def render_store_card(console: Console, candidate: PackageCandidate) -> None:
    """Render comprehensive card for a software item available in a store."""
    store_sources = [s for s in candidate.sources if not s.is_installed]
    provider_badges = " ".join(f"[{s.source_icon} {s.source_name}]" for s in store_sources)

    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("Key", style="bold cyan", width=18)
    table.add_column("Value", style="white")

    table.add_row("Status", "[bold yellow]Available in Software Catalog (Not Installed)[/bold yellow]")
    table.add_row("Classification", f"{candidate.nature_icon} [bold]{candidate.nature}[/bold]")
    table.add_row("Providers", provider_badges)
    if candidate.primary_version:
        table.add_row("Latest Version", f"[bold white]{candidate.primary_version}[/bold white]")

    sizes = [s.download_size for s in store_sources if s.download_size]
    if sizes:
        table.add_row("Download Size", sizes[0])

    if candidate.summary:
        table.add_row("Description", candidate.summary)

    for s in store_sources:
        if s.homepage:
            table.add_row("Homepage", f"[link={s.homepage}]{s.homepage}[/link]")
            break

    console.print(
        Panel(
            table,
            title=f"[bold cyan]📦 {candidate.name} ({candidate.nature_icon} {candidate.nature})[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def render_not_found_card(console: Console, query: str) -> None:
    """Render friendly guidance when no package matches."""
    # Find closest known names from common binaries and packages
    suggestions: List[str] = []
    try:
        common_candidates = [
            "curl", "git", "vim", "nano", "vlc", "htop", "wget", "tmux", "ffmpeg",
            "build-essential", "python3", "python3-pip", "nodejs", "npm", "flatpak",
            "gimp", "audacity", "firefox", "chromium", "neofetch", "zip", "tar",
        ]
        suggestions = difflib.get_close_matches(query.lower(), common_candidates, n=3, cutoff=0.4)
    except Exception:
        pass

    tips_table = Table(box=None, show_header=False, padding=(0, 1))
    tips_table.add_column("Icon", style="bold cyan", width=3)
    tips_table.add_column("Guidance", style="white")

    tips_table.add_row("❌", f"No package or application matching '[bold cyan]{query}[/bold cyan]' was found locally or in configured stores.")
    if suggestions:
        sugg_str = ", ".join(f"[bold green]{s}[/bold green]" for s in suggestions)
        tips_table.add_row("💡", f"Did you mean: {sugg_str}?")
    tips_table.add_row("🔄", "Refresh Index: Run [bold green]ez update[/bold green] to refresh your system package catalogs.")
    tips_table.add_row("📋", "Installed Apps: View all installed software with [bold green]ez list-installed-packages[/bold green].")
    tips_table.add_row("🔍", "Broader Query: Try searching by keyword (e.g. 'browser', 'video', 'editor').")

    console.print(
        Panel(
            tips_table,
            title=f"[bold yellow]🔍 Software Not Found: '{query}'[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )


def render_candidate_chooser(console: Console, query: str, candidates: List[PackageCandidate]) -> Optional[PackageCandidate]:
    """Present formatted chooser when multiple packages match query."""
    console.print(f"\n[bold cyan]Multiple packages match '{query}':[/bold cyan]")
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 1))
    table.add_column("#", justify="right", style="bold yellow", width=3)
    table.add_column("Type", justify="center", width=4)
    table.add_column("Package / Application", style="bold white", width=24)
    table.add_column("Status", justify="center", width=18)
    table.add_column("Description", style="white")

    for idx, cand in enumerate(candidates, 1):
        st = "[bold green]✔ Installed[/bold green]" if cand.is_installed else "[dim]Available[/dim]"
        table.add_row(str(idx), cand.nature_icon, cand.name, st, cand.summary[:55])

    console.print(table)
    console.print()

    try:
        choice = Prompt.ask(
            f"[bold cyan]Select a package [1-{len(candidates)}] to view details / actions[/bold cyan] (or press Enter to cancel)",
            default="",
        ).strip()
    except (KeyboardInterrupt, EOFError):
        return None

    if choice.isdigit() and 1 <= int(choice) <= len(candidates):
        return candidates[int(choice) - 1]
    return None


def render_extended_details(console: Console, candidate: PackageCandidate) -> None:
    """Display comprehensive technical details (maintainer, files, source list)."""
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 1))
    table.add_column("Source", style="bold cyan", width=16)
    table.add_column("Identifier", style="bold green", width=22)
    table.add_column("Installed", justify="center", width=12)
    table.add_column("Version", style="white", width=16)
    table.add_column("Location / Origin", style="dim")

    for s in candidate.sources:
        inst_label = "[bold green]Yes[/bold green]" if s.is_installed else "[dim]No[/dim]"
        loc = s.location or s.homepage or s.section or "Repository"
        table.add_row(f"{s.source_icon} {s.source_name}", s.app_id or s.name, inst_label, s.version or "N/A", loc)

    console.print()
    console.print(
        Panel(
            table,
            title=f"[bold cyan]Technical Metadata: {candidate.name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


# ==============================================================================
# Main Interactive Flow
# ==============================================================================
def handle_candidate_actions(console: Console, candidate: PackageCandidate) -> None:
    """Prompt user for safe context-aware actions on chosen package."""
    while True:
        console.print()
        if candidate.is_installed:
            actions_prompt = (
                "[bold cyan]Safe Actions[/bold cyan]: "
                "[bold][1][/bold] 🎯 Run | "
                "[bold][2][/bold] 🗑️ Uninstall | "
                "[bold][3][/bold] ℹ️ Details | "
                "[bold][q][/bold] Exit"
            )
            choices = ["1", "2", "3", "q", ""]
        else:
            actions_prompt = (
                "[bold cyan]Safe Actions[/bold cyan]: "
                "[bold][1][/bold] 📥 Install | "
                "[bold][2][/bold] ℹ️ Details | "
                "[bold][q][/bold] Exit"
            )
            choices = ["1", "2", "q", ""]

        try:
            act = Prompt.ask(actions_prompt, choices=choices, default="q", show_choices=False).strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if act in ("q", ""):
            break

        if candidate.is_installed:
            if act == "1":
                execute_run_action(console, candidate)
                break
            elif act == "2":
                execute_uninstall_action(console, candidate)
                break
            elif act == "3":
                render_extended_details(console, candidate)
        else:
            if act == "1":
                execute_install_action(console, candidate)
                break
            elif act == "2":
                render_extended_details(console, candidate)


def run_package_info_hub(console: Console) -> None:
    """Hub mode displayed when 'ez package-info' is run without arguments."""
    if sys.stdout.isatty():
        from .main import check_textual_installed
        if check_textual_installed(console):
            from .package_info_tui import PackageInfoApp
            app = PackageInfoApp()
            app.run()
            return

    while True:
        console.clear()
        header = (
            "[bold cyan]EasyCLI Package & App Hub[/bold cyan] [dim]─ Unified App Store & Manager[/dim]\n"
            "[dim]Manage local software, inspect store catalogs, check updates, and run safe actions.[/dim]"
        )
        console.print(Panel(header, box=box.ROUNDED, border_style="cyan"))

        table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 2))
        table.add_column("#", justify="right", style="bold yellow", width=3)
        table.add_column("Option", style="bold white", width=28)
        table.add_column("Description", style="white")

        table.add_row("1", "📱 My Installed Apps", "View and filter all installed system software across APT, Flatpak, and Snap")
        table.add_row("2", "🔄 Available Updates", "Inspect pending software upgrades from repositories without applying changes")
        table.add_row("3", "🏪 Inspect / Search Package", "Check local and store details for any package, library, or desktop app")
        table.add_row("4", "❌ Exit", "Return to terminal shell")

        console.print(table)
        console.print()

        try:
            choice = Prompt.ask(
                "[bold cyan]Select an option [1-4][/bold cyan] (or [bold]q[/bold]uit)",
                choices=["1", "2", "3", "4", "q"],
                default="1",
                show_choices=False,
            ).strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice in ("4", "q"):
            console.print("\n[dim]Exiting Package Hub.[/dim]")
            break
        elif choice == "1":
            from .renderers import render_list_installed_packages
            console.clear()
            render_list_installed_packages(console)
            Prompt.ask("\n[dim]Press Enter to return to Hub...[/dim]", default="")
        elif choice == "2":
            from .renderers import render_available_updates
            console.clear()
            render_available_updates(console)
            Prompt.ask("\n[dim]Press Enter to return to Hub...[/dim]", default="")
        elif choice == "3":
            console.print()
            try:
                pkg_name = Prompt.ask("[bold cyan]Enter package or application name to inspect[/bold cyan]").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if pkg_name:
                run_cli_package_info(pkg_name, console=console)
                Prompt.ask("\n[dim]Press Enter to return to Hub...[/dim]", default="")


def run_cli_package_info(name: Optional[str] = None, console: Optional[Console] = None) -> None:
    """
    Main entrypoint for 'ez package-info [name]'.
    If no name provided, launches the App Hub menu.
    """
    console = console or Console()
    query = (name or "").strip()

    # Launch full interactive TUI in terminal sessions
    if sys.stdout.isatty():
        from .main import check_textual_installed
        if check_textual_installed(console):
            from .package_info_tui import PackageInfoApp
            app = PackageInfoApp(initial_query=query)
            app.run()
            return

    if not query:
        run_package_info_hub(console)
        return

    with console.status(f"[bold cyan]Inspecting local machine & store catalogs for '{query}'...[/bold cyan]", spinner="dots"):
        candidates, store_avail, store_note = resolve_package_info(query)

    if not candidates:
        render_not_found_card(console, query)
        return

    # Check for an exact match (or single candidate)
    selected_candidate: Optional[PackageCandidate] = None
    if candidates[0].match_score >= 100 or len(candidates) == 1:
        selected_candidate = candidates[0]
    else:
        # Multiple candidates: show chooser
        selected_candidate = render_candidate_chooser(console, query, candidates[:10])

    if not selected_candidate:
        return

    console.print()
    if selected_candidate.is_installed:
        render_installed_card(console, selected_candidate, store_avail, store_note)
    else:
        render_store_card(console, selected_candidate)

    # Offer safe context-aware actions
    handle_candidate_actions(console, selected_candidate)
