"""Declarative feature templates and configuration for EasyCLI (ez)."""

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


# Feature Templates (v0.1, v0.2, v0.3)
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
                help="Path to folder (or 'choose-directory' to select visually; defaults to ~)",
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
        description="Search packages across APT 📦, Flatpak 🟣, and Snap 🟢 with platform choices",
        wrapped_commands=["apt search", "flathub", "snapcraft"],
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
    FeatureTemplate(
        id="installed_packages",
        subcommand="installed-packages",
        title="Installed Packages",
        icon="📋",
        description="List all installed system and desktop packages (wraps apt list --installed)",
        wrapped_commands=["apt list --installed", "dpkg-query", "flatpak list", "snap list"],
        arguments=[],
        renderer_name="render_installed_packages",
    ),
    FeatureTemplate(
        id="installed_package_search",
        subcommand="installed-package-search",
        title="Search Installed Packages",
        icon="🔎",
        description="Search installed packages by name (wraps apt list --installed | grep -i <name>)",
        wrapped_commands=["apt list --installed | grep -i <name>", "dpkg-query"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Package name or application keyword to search",
                required=True,
            )
        ],
        renderer_name="render_installed_package_search",
    ),
    FeatureTemplate(
        id="choose_directory",
        subcommand="choose-directory",
        title="File Explorer",
        icon="📁",
        description="Modern visual terminal file explorer with mouse support and action menu",
        wrapped_commands=["explorer"],
        arguments=[
            ArgumentDef(
                name="path",
                help="Starting directory to browse",
                required=False,
                default="~",
            )
        ],
        renderer_name="run_choose_directory",
    ),
    FeatureTemplate(
        id="copy",
        subcommand="copy",
        title="Copy Items",
        icon="📋",
        description="Copy file/folder in current directory or choose visually with choose-directory",
        wrapped_commands=["cp"],
        arguments=[
            ArgumentDef(
                name="target",
                help="File, folder/, or 'choose-directory'",
                required=False,
            )
        ],
        renderer_name="run_cli_copy",
    ),
    FeatureTemplate(
        id="move",
        subcommand="move",
        title="Move / Cut Items",
        icon="🚚",
        description="Move file/folder in current directory or choose visually with choose-directory",
        wrapped_commands=["mv"],
        arguments=[
            ArgumentDef(
                name="target",
                help="File, folder/, or 'choose-directory'",
                required=False,
            )
        ],
        renderer_name="run_cli_move",
    ),
    FeatureTemplate(
        id="paste",
        subcommand="paste",
        title="Paste Items",
        icon="📥",
        description="Paste staged items into current directory, or choose destination with choose-directory",
        wrapped_commands=["paste"],
        arguments=[
            ArgumentDef(
                name="destination",
                help="'choose-directory' or omit for current directory",
                required=False,
            )
        ],
        renderer_name="run_cli_paste",
    ),
    FeatureTemplate(
        id="undo",
        subcommand="undo",
        title="Undo Operation",
        icon="⏪",
        description="Revert the most recent paste operation with safety confirmation",
        wrapped_commands=["undo"],
        arguments=[],
        renderer_name="run_cli_undo",
    ),
    FeatureTemplate(
        id="redo",
        subcommand="redo",
        title="Redo Operation",
        icon="⏩",
        description="Re-apply the most recently undone operation with safety confirmation",
        wrapped_commands=["redo"],
        arguments=[],
        renderer_name="run_cli_redo",
    ),
    FeatureTemplate(
        id="create_folder",
        subcommand="create-folder",
        title="Create New Folder",
        icon="📁",
        description="Create a new folder directly or via visual directory picker",
        wrapped_commands=["create-folder"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Name of folder to create (or 'choose-directory' to pick location visually)",
                required=False,
                default="",
            )
        ],
        renderer_name="run_cli_create_folder",
    ),
    FeatureTemplate(
        id="create_file",
        subcommand="create-file",
        title="Create New File",
        icon="📄",
        description="Create a new blank file directly or via visual directory picker",
        wrapped_commands=["create-file"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Name of file to create with extension (or 'choose-directory' to pick location visually)",
                required=False,
                default="",
            )
        ],
        renderer_name="run_cli_create_file",
    ),
    FeatureTemplate(
        id="delete",
        subcommand="delete",
        title="Delete Items",
        icon="🗑️",
        description="Permanently delete files or folders with safety consent (non-force first)",
        wrapped_commands=["delete"],
        arguments=[
            ArgumentDef(
                name="target",
                help="Folder name (with /) or file in current directory, or 'choose-directory'",
                required=False,
                default="choose-directory",
            )
        ],
        renderer_name="run_cli_delete",
    ),
    FeatureTemplate(
        id="edit_file",
        subcommand="edit-file",
        title="Edit Text/Code File",
        icon="📝",
        description="Terminal text and code editor with syntax highlighting and auto-elevation",
        wrapped_commands=["edit-file"],
        arguments=[
            ArgumentDef(
                name="target",
                help="File in current directory (name.ext) or 'choose-directory'",
                required=False,
                default="choose-directory",
            )
        ],
        renderer_name="run_cli_edit_file",
    ),
]

# Lookup map by subcommand
FEATURES_BY_SUBCOMMAND: Dict[str, FeatureTemplate] = {
    f.subcommand: f for f in FEATURES
}

# Convenient aliases
FEATURES_BY_SUBCOMMAND["installed"] = FEATURES_BY_SUBCOMMAND["installed-packages"]
FEATURES_BY_SUBCOMMAND["choose"] = FEATURES_BY_SUBCOMMAND["choose-directory"]
FEATURES_BY_SUBCOMMAND["explorer"] = FEATURES_BY_SUBCOMMAND["choose-directory"]
FEATURES_BY_SUBCOMMAND["new-folder"] = FEATURES_BY_SUBCOMMAND["create-folder"]
FEATURES_BY_SUBCOMMAND["new-file"] = FEATURES_BY_SUBCOMMAND["create-file"]
FEATURES_BY_SUBCOMMAND["del"] = FEATURES_BY_SUBCOMMAND["delete"]
FEATURES_BY_SUBCOMMAND["remove"] = FEATURES_BY_SUBCOMMAND["delete"]
