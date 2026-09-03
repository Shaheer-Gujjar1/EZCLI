"""Distribution detection and validation for Debian-based systems."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class DistroInfo:
    id: str
    name: str
    version: str
    pretty_name: str
    codename: str
    id_like: str
    is_debian_based: bool
    package_manager: str
    init_system: str


KNOWN_DEBIAN_DERIVATIVES = {
    "debian",
    "ubuntu",
    "zorin",
    "deepin",
    "ubuntudde",
    "mint",
    "linuxmint",
    "pop",
    "elementary",
    "kali",
    "parrot",
    "devuan",
    "raspbian",
    "mx",
    "antix",
    "pureos",
    "tails",
    "bodhi",
    "peppermint",
    "lite",
}


def parse_os_release(filepath: Optional[str] = None) -> Dict[str, str]:
    """Parse /etc/os-release (or fallback /usr/lib/os-release) key-values."""
    paths_to_check = [filepath] if filepath else ["/etc/os-release", "/usr/lib/os-release"]
    data: Dict[str, str] = {}

    for path_str in paths_to_check:
        if not path_str:
            continue
        p = Path(path_str)
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        data[k] = v
                if data:
                    break
            except Exception:
                continue

    return data


def detect_distro(os_release_path: Optional[str] = None) -> DistroInfo:
    """Detect distribution details and verify Debian derivative status."""
    data = parse_os_release(os_release_path)

    distro_id = data.get("ID", "").lower()
    id_like = data.get("ID_LIKE", "").lower()
    name = data.get("NAME", "Linux")
    pretty_name = data.get("PRETTY_NAME", name)
    version = data.get("VERSION", data.get("VERSION_ID", ""))
    codename = data.get("VERSION_CODENAME", "")

    # Check for debian indicators
    has_apt = shutil.which("apt") is not None
    has_dpkg = shutil.which("dpkg") is not None
    has_systemd = shutil.which("systemctl") is not None or Path("/run/systemd/system").exists()
    has_debian_version = Path("/etc/debian_version").exists()

    id_like_tokens = id_like.split() if id_like else []
    is_derivative = (
        distro_id in KNOWN_DEBIAN_DERIVATIVES
        or "debian" in id_like_tokens
        or "ubuntu" in id_like_tokens
        or has_debian_version
        or (has_apt and has_dpkg)
    )

    return DistroInfo(
        id=distro_id or "unknown",
        name=name,
        version=version,
        pretty_name=pretty_name,
        codename=codename,
        id_like=id_like,
        is_debian_based=bool(is_derivative),
        package_manager="apt / dpkg" if (has_apt or has_dpkg) else "unknown",
        init_system="systemd" if has_systemd else "unknown",
    )
