"""Scanning and toggling engine for login applications and boot services."""

import configparser
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..elevation import elevated_toggle_service


CRITICAL_SERVICES = [
    "networkmanager",
    "systemd-networkd",
    "systemd-resolved",
    "dbus",
    "systemd-logind",
    "gdm",
    "gdm3",
    "sddm",
    "lightdm",
    "lxdm",
    "ssh",
    "sshd",
    "ufw",
    "firewalld",
    "pipewire",
    "pulseaudio",
    "polkit",
    "accounts-daemon",
]


@dataclass
class StartupItem:
    id: str
    name: str
    description: str
    item_type: str  # "login" or "service"
    state: str      # "Enabled" or "Disabled"
    exec_cmd: str
    file_path: str
    is_critical: bool = False


def is_service_critical(unit_name: str) -> bool:
    """Check if a systemd service is critical for system stability."""
    name_clean = unit_name.lower().replace(".service", "")
    for crit in CRITICAL_SERVICES:
        if name_clean == crit or name_clean.startswith(crit + "."):
            return True
    return False


def parse_desktop_file(filepath: Path) -> Optional[Dict[str, str]]:
    """Parse a .desktop autostart file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except (PermissionError, OSError):
        return None

    data: Dict[str, str] = {
        "Name": filepath.stem,
        "Comment": "",
        "Exec": "",
        "Hidden": "false",
        "X-GNOME-Autostart-enabled": "true",
        "NoDisplay": "false",
    }

    in_entry = False
    for line in content.splitlines():
        line_clean = line.strip()
        if line_clean == "[Desktop Entry]":
            in_entry = True
            continue
        elif line_clean.startswith("[") and line_clean.endswith("]"):
            in_entry = False
            continue

        if in_entry and "=" in line_clean and not line_clean.startswith("#"):
            k, v = line_clean.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k in data:
                data[k] = v

    return data


def scan_login_apps() -> List[StartupItem]:
    """Scan user and system autostart directories for login applications."""
    items: List[StartupItem] = []
    seen_ids = set()

    user_dir = Path.home() / ".config" / "autostart"
    system_dir = Path("/etc/xdg/autostart")

    # 1. User autostart first (overrides system)
    if user_dir.is_dir():
        try:
            for p in sorted(user_dir.glob("*.desktop")):
                d = parse_desktop_file(p)
                if not d:
                    continue
                is_disabled = (
                    d.get("Hidden", "").lower() == "true"
                    or d.get("X-GNOME-Autostart-enabled", "").lower() == "false"
                )
                state = "Disabled" if is_disabled else "Enabled"
                item = StartupItem(
                    id=p.name,
                    name=d.get("Name") or p.stem,
                    description=d.get("Comment") or "User startup application",
                    item_type="login",
                    state=state,
                    exec_cmd=d.get("Exec", ""),
                    file_path=str(p),
                    is_critical=False,
                )
                items.append(item)
                seen_ids.add(p.name)
        except (PermissionError, OSError):
            pass

    # 2. System autostart (if not overridden by user)
    if system_dir.is_dir():
        try:
            for p in sorted(system_dir.glob("*.desktop")):
                if p.name in seen_ids:
                    continue
                d = parse_desktop_file(p)
                if not d:
                    continue
                is_disabled = (
                    d.get("Hidden", "").lower() == "true"
                    or d.get("X-GNOME-Autostart-enabled", "").lower() == "false"
                )
                state = "Disabled" if is_disabled else "Enabled"
                item = StartupItem(
                    id=p.name,
                    name=d.get("Name") or p.stem,
                    description=d.get("Comment") or "System startup application",
                    item_type="login",
                    state=state,
                    exec_cmd=d.get("Exec", ""),
                    file_path=str(p),
                    is_critical=False,
                )
                items.append(item)
                seen_ids.add(p.name)
        except (PermissionError, OSError):
            pass

    return sorted(items, key=lambda x: x.name.lower())


def toggle_login_app(item: StartupItem) -> Tuple[bool, str]:
    """Toggle a login application state without admin rights."""
    user_dir = Path.home() / ".config" / "autostart"
    user_dir.mkdir(parents=True, exist_ok=True)
    target_path = user_dir / item.id

    new_state = "Disabled" if item.state == "Enabled" else "Enabled"
    hidden_val = "true" if new_state == "Disabled" else "false"
    autostart_val = "false" if new_state == "Disabled" else "true"

    try:
        if target_path.exists():
            # Update existing user file
            content = target_path.read_text(encoding="utf-8", errors="ignore")
            lines = []
            has_hidden = False
            has_gnome = False
            for line in content.splitlines():
                if line.startswith("Hidden="):
                    lines.append(f"Hidden={hidden_val}")
                    has_hidden = True
                elif line.startswith("X-GNOME-Autostart-enabled="):
                    lines.append(f"X-GNOME-Autostart-enabled={autostart_val}")
                    has_gnome = True
                else:
                    lines.append(line)
            if not has_hidden:
                lines.append(f"Hidden={hidden_val}")
            if not has_gnome:
                lines.append(f"X-GNOME-Autostart-enabled={autostart_val}")
            target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            # Copy from system file or create override
            src_path = Path(item.file_path)
            if src_path.exists():
                content = src_path.read_text(encoding="utf-8", errors="ignore")
            else:
                content = (
                    "[Desktop Entry]\n"
                    f"Name={item.name}\n"
                    f"Exec={item.exec_cmd}\n"
                    "Type=Application\n"
                )
            lines = []
            for line in content.splitlines():
                if not line.startswith("Hidden=") and not line.startswith("X-GNOME-Autostart-enabled="):
                    lines.append(line)
            lines.append(f"Hidden={hidden_val}")
            lines.append(f"X-GNOME-Autostart-enabled={autostart_val}")
            target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        item.state = new_state
        return True, f"Application '{item.name}' is now {new_state}."
    except Exception as e:
        return False, f"Failed to toggle login app: {e}"


def scan_boot_services() -> List[StartupItem]:
    """Scan systemd service units for boot services."""
    if not shutil.which("systemctl"):
        return []

    items: List[StartupItem] = []
    try:
        proc = subprocess.run(
            ["systemctl", "list-unit-files", "--type=service", "--no-legend", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = (proc.stdout or "").splitlines()
    except Exception:
        return []

    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            unit = parts[0].strip()
            unit_state = parts[1].strip().lower()

            if unit_state not in ("enabled", "disabled"):
                continue

            state = "Enabled" if unit_state == "enabled" else "Disabled"
            clean_name = unit.replace(".service", "")
            is_crit = is_service_critical(unit)

            items.append(
                StartupItem(
                    id=unit,
                    name=clean_name,
                    description=f"System service ({unit})",
                    item_type="service",
                    state=state,
                    exec_cmd="",
                    file_path=unit,
                    is_critical=is_crit,
                )
            )

    return sorted(items, key=lambda x: x.name.lower())


def toggle_boot_service(item: StartupItem, console: Optional[Any] = None) -> Tuple[bool, str]:
    """Toggle a boot service via elevated systemctl."""
    enable = (item.state != "Enabled")
    ok, err = elevated_toggle_service(item.id, enable=enable, console=console)
    if ok:
        item.state = "Enabled" if enable else "Disabled"
        return True, f"Service '{item.name}' is now {item.state}."
    return False, err or "Failed to change service state."
