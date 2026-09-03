"""Declarative feature templates and configuration for EasyCLI (ezcli)."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ArgumentDef:
    name: str
    help: str
    required: bool = False
    default: Optional[str] = None
    type_name: str = "str"


@dataclass
class FeatureTemplate:
    id: str
    subcommand: str
    title: str
    icon: str
    description: str
    wrapped_commands: List[str]
    arguments: List[ArgumentDef] = field(default_factory=list)
    renderer_name: str = ""


# 10 Final v0.1 Feature Templates
FEATURES: List[FeatureTemplate] = [
    FeatureTemplate(
        id="system_info",
        subcommand="system-info",
        title="System Information",
        icon="💻",
        description="Show OS name, version, hostname, kernel, and system uptime",
        wrapped_commands=["hostnamectl", "uptime -p", "/etc/os-release"],
        renderer_name="render_system_info",
    ),
    FeatureTemplate(
        id="stats",
        subcommand="stats",
        title="Resource Statistics",
        icon="⚡",
        description="Show CPU load averages and RAM usage with progress bars",
        wrapped_commands=["free -h", "uptime", "nproc"],
        renderer_name="render_stats",
    ),
    FeatureTemplate(
        id="disk_info",
        subcommand="disk-info",
        title="Disk Space Usage",
        icon="💽",
        description="Show mounted storage partitions with inline usage bars (excluding pseudo-filesystems)",
        wrapped_commands=["df -h"],
        renderer_name="render_disk_info",
    ),
    FeatureTemplate(
        id="big_files",
        subcommand="big-files",
        title="Largest Files & Folders",
        icon="📁",
        description="Scan directory for top largest items with progress spinner",
        wrapped_commands=["du -h --max-depth=1", "find"],
        arguments=[
            ArgumentDef(
                name="folder",
                help="Path to folder to scan (defaults to user home directory)",
                required=False,
                default="~",
            )
        ],
        renderer_name="render_big_files",
    ),
    FeatureTemplate(
        id="package_search",
        subcommand="package-search",
        title="Search Packages",
        icon="🔍",
        description="Search apt repository packages without clutter or apt noise",
        wrapped_commands=["apt search"],
        arguments=[
            ArgumentDef(
                name="term",
                help="Package search keyword",
                required=True,
            )
        ],
        renderer_name="render_package_search",
    ),
    FeatureTemplate(
        id="package",
        subcommand="package",
        title="Package Details",
        icon="📦",
        description="View package version, size, description and installed status",
        wrapped_commands=["apt show", "dpkg -s"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Name of the package to inspect",
                required=True,
            )
        ],
        renderer_name="render_package",
    ),
    FeatureTemplate(
        id="available_updates",
        subcommand="available-updates",
        title="Available Updates",
        icon="🔄",
        description="List upgradable packages using existing lists without modifying the system",
        wrapped_commands=["apt list --upgradable"],
        renderer_name="render_available_updates",
    ),
    FeatureTemplate(
        id="service_status",
        subcommand="service-status",
        title="Service Status",
        icon="⚙️",
        description="Inspect systemd service running state and boot enablement",
        wrapped_commands=["systemctl is-active", "systemctl is-enabled"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Name of the systemd service (e.g. ssh, NetworkManager)",
                required=True,
            )
        ],
        renderer_name="render_service_status",
    ),
    FeatureTemplate(
        id="network_info",
        subcommand="network-info",
        title="Network Information",
        icon="🌐",
        description="View network interfaces, IP addresses, default gateway, and DNS",
        wrapped_commands=["ip addr", "ip route", "/etc/resolv.conf"],
        renderer_name="render_network_info",
    ),
    FeatureTemplate(
        id="logs",
        subcommand="logs",
        title="Recent System Logs",
        icon="📄",
        description="View recent journal logs with color-coded severity indicators",
        wrapped_commands=["journalctl -n N --no-pager"],
        arguments=[
            ArgumentDef(
                name="lines",
                help="Number of log lines to show (default: 50)",
                required=False,
                default="50",
                type_name="int",
            )
        ],
        renderer_name="render_logs",
    ),
]

# Lookup map by subcommand
FEATURES_BY_SUBCOMMAND: Dict[str, FeatureTemplate] = {
    f.subcommand: f for f in FEATURES
}
