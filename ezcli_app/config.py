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


# Feature Templates (v0.1, v0.2, v0.3, v0.4, v0.5)
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
        description="Live hardware & system metrics monitor (per-core CPU, RAM/Swap, and top resource consumers)",
        wrapped_commands=["free -h", "uptime", "nproc", "/proc/stat"],
        renderer_name="render_stats",
    ),
    FeatureTemplate(
        id="task_manager",
        subcommand="task-manager",
        title="Task Manager",
        icon="📋",
        description="Lite and modern terminal Task Manager showing active user apps, unresponsive detection, and instant process termination",
        wrapped_commands=["ps", "kill"],
        renderer_name="run_task_manager",
    ),
    FeatureTemplate(
        id="task_manager_pro",
        subcommand="task-manager-pro",
        title="Task Manager (Pro)",
        icon="🔒",
        description="Comprehensive Task Manager showing all user apps, background daemons, and system processes with automatic admin elevation",
        wrapped_commands=["ps", "kill", "sudo kill"],
        renderer_name="run_task_manager_pro",
    ),
    FeatureTemplate(
        id="time_machine",
        subcommand="time-machine",
        title="Time Machine (System Restore Points)",
        icon="🕒",
        description="Mini Timeshift system restore manager: view snapshots, create restore points, and safely recover system state",
        wrapped_commands=["rsync", "cp", "btrfs"],
        arguments=[
            ArgumentDef(
                name="action",
                help="Optional 'list' or 'create [comment]' (defaults to interactive TUI)",
                required=False,
                default="",
            )
        ],
        renderer_name="run_cli_time_machine",
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
        id="package_info",
        subcommand="package-info",
        title="Package & App Info",
        icon="📦",
        description="Unified package inspector: check local & store, run, install, or uninstall",
        wrapped_commands=["apt", "dpkg", "snap", "flatpak", "pip", "npm"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Package or application name to inspect (or blank for App Hub)",
                required=False,
                default="",
            )
        ],
        renderer_name="render_package_info",
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
        id="update",
        subcommand="update",
        title="Update Software Catalog",
        icon="🔄",
        description="Refresh package catalog from repositories without installing or modifying software",
        wrapped_commands=["apt update", "apt-get update"],
        renderer_name="run_cli_update",
    ),
    FeatureTemplate(
        id="upgrade",
        subcommand="upgrade",
        title="Upgrade System Software",
        icon="🚀",
        description="Comprehensive upgrade across APT, Flatpak, and Snap with safety preview",
        wrapped_commands=["apt upgrade", "snap refresh", "flatpak update"],
        renderer_name="run_cli_upgrade",
    ),
    FeatureTemplate(
        id="uninstall",
        subcommand="uninstall",
        title="Uninstall Application",
        icon="🧹",
        description="Safely uninstall an application across APT, Flatpak, or Snap with admin authorization",
        wrapped_commands=["apt remove", "flatpak uninstall", "snap remove"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Name or ID of the application to uninstall",
                required=False,
            )
        ],
        renderer_name="run_cli_uninstall",
    ),
    FeatureTemplate(
        id="service_status",
        subcommand="service-status",
        title="Service Status",
        icon="🔧",
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
        id="list",
        subcommand="list",
        title="Directory List & Tree",
        icon="🗂",
        description="Instant directory listing with progressive folder sizing or interactive TUI inspector (choose-directory)",
        wrapped_commands=["ls", "tree", "du", "stat"],
        arguments=[
            ArgumentDef(
                name="mode",
                help="'choose-directory' to pick visually and inspect in TUI (omit for instant current directory listing)",
                required=False,
                default="",
            )
        ],
        renderer_name="render_list_directory",
    ),
    FeatureTemplate(
        id="list_installed_packages",
        subcommand="list-installed-packages",
        title="List Installed Packages",
        icon="📋",
        description="List installed desktop applications and/or system packages (interactive filter for apps, packages, or both)",
        wrapped_commands=["apt list --installed", "dpkg-query", "flatpak list", "snap list"],
        arguments=[
            ArgumentDef(
                name="filter",
                help="Optional filter: 'apps', 'packages', 'both', or search keyword",
                required=False,
            )
        ],
        renderer_name="render_list_installed_packages",
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
        description="Create new folder(s) directly or via visual directory picker",
        wrapped_commands=["create-folder"],
        arguments=[
            ArgumentDef(
                name="name",
                help="Folder name(s) separated by commas (in current directory), or 'choose-directory'",
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
        description="Create new blank file(s) directly or via visual directory picker",
        wrapped_commands=["create-file"],
        arguments=[
            ArgumentDef(
                name="name",
                help="File name(s) with extension separated by commas (in current directory), or 'choose-directory'",
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
        icon="🧹",
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
    FeatureTemplate(
        id="check_internet",
        subcommand="check-internet",
        title="Check Internet Connection",
        icon="📶",
        description="Check router ping, DNS resolution, internet reachability, and why internet isn't working",
        wrapped_commands=["ping", "ip route", "socket"],
        arguments=[],
        renderer_name="render_internet_check",
    ),
    FeatureTemplate(
        id="connect_wifi",
        subcommand="connect-wifi",
        title="Connect Wi-Fi",
        icon="📶",
        description="In-terminal graphical Wi-Fi manager with mouse support, network scanning, and password dialog",
        wrapped_commands=["nmcli", "iw"],
        arguments=[],
        renderer_name="run_wifi_app",
    ),
    FeatureTemplate(
        id="search_file",
        subcommand="search-file",
        title="Search Files",
        icon="🔍",
        description="Fuzzy file search starting from /home with interactive selection and optional system-wide fallback",
        wrapped_commands=["find", "locate", "ls"],
        arguments=[
            ArgumentDef(
                name="term",
                help="Keyword or file name to search",
                required=False,
                default="",
            )
        ],
        renderer_name="run_search_file_cli",
    ),
    FeatureTemplate(
        id="compress",
        subcommand="compress",
        title="Compress Files & Folders",
        icon="📦",
        description="Compress files or folders into .zip, .tar.gz, .tar.xz, .7z, or .tar.bz2 with live progress",
        wrapped_commands=["zip", "tar", "7z"],
        arguments=[
            ArgumentDef(
                name="targets",
                help="Files (name.ext) or folders (folder/) in current directory, or 'choose-directory'",
                required=False,
                default="choose-directory",
            )
        ],
        renderer_name="run_cli_compress",
    ),
    FeatureTemplate(
        id="extract",
        subcommand="extract",
        title="Extract Archives",
        icon="📂",
        description="Extract archive file(s) into current directory, specific folder ('to <folder>'), or visual picker",
        wrapped_commands=["unzip", "tar", "7z"],
        arguments=[
            ArgumentDef(
                name="targets",
                help="Archive file(s) in current directory, 'to <destination>', or 'choose-directory'",
                required=False,
                default="choose-directory",
            )
        ],
        renderer_name="run_cli_extract",
    ),
    FeatureTemplate(
        id="run",
        subcommand="run",
        title="Universal Application & Script Runner",
        icon="🎯",
        description="Run scripts, binaries, AppImages, or launch apps with guided flag-free mode",
        wrapped_commands=["bash", "python3", "gio", "snap", "flatpak"],
        arguments=[
            ArgumentDef(
                name="target",
                help="File path or application name [args...]",
                required=False,
                default="",
            )
        ],
        renderer_name="run_cli_run",
    ),
    FeatureTemplate(
        id="cleanup",
        subcommand="cleanup",
        title="Safe System Cleaner",
        icon="🧹",
        description="Safe system cleaner for package caches, orphan packages, trash, and old logs",
        wrapped_commands=["apt-get clean", "apt-get autoremove", "rm"],
        arguments=[],
        renderer_name="run_cleanup_cli",
    ),
    FeatureTemplate(
        id="profile",
        subcommand="profile",
        title="User Profile & Password",
        icon="👤",
        description="Display current user profile, groups, sudo status, and secure password change",
        wrapped_commands=["whoami", "id", "chpasswd"],
        arguments=[],
        renderer_name="run_profile_cli",
    ),
    FeatureTemplate(
        id="fix_packages",
        subcommand="fix-packages",
        title="Package Repair Engine",
        icon="🔧",
        description="Repair broken package states, unconfigured dpkg packages, and missing dependencies",
        wrapped_commands=["dpkg --configure -a", "apt-get --fix-broken install"],
        arguments=[],
        renderer_name="run_fix_packages_cli",
    ),
    FeatureTemplate(
        id="startup_apps",
        subcommand="startup-apps",
        title="Startup & Boot Manager",
        icon="🚀",
        description="Manage login startup applications and systemd boot services with critical service locking",
        wrapped_commands=["systemctl enable", "systemctl disable"],
        arguments=[
            ArgumentDef(
                name="target",
                help="Application name or service unit to view/toggle (omit for interactive TUI)",
                required=False,
                default="",
            )
        ],
        renderer_name="run_startup_apps_cli",
    ),
    FeatureTemplate(
        id="firewall",
        subcommand="firewall",
        title="Firewall Manager (UFW)",
        icon="🛡️",
        description="Visual frontend for UFW with safety status, rules table, and SSH lockout prevention",
        wrapped_commands=["ufw", "ufw status", "ufw allow"],
        arguments=[],
        renderer_name="run_firewall_cli",
    ),
    FeatureTemplate(
        id="bluetooth",
        subcommand="bluetooth",
        title="Bluetooth Device Manager",
        icon="📡",
        description="Visual Bluetooth scanner, device pairing, connection manager, and signal monitor",
        wrapped_commands=["bluetoothctl", "bluetoothctl scan", "bluetoothctl connect"],
        arguments=[],
        renderer_name="run_bluetooth_cli",
    ),
    FeatureTemplate(
        id="drivers",
        subcommand="drivers",
        title="Hardware Drivers Detector",
        icon="🖥️",
        description="Detect and install recommended proprietary drivers for NVIDIA GPUs, Wi-Fi, and microcode",
        wrapped_commands=["ubuntu-drivers", "lspci", "apt-get install"],
        arguments=[],
        renderer_name="run_drivers_cli",
    ),
    FeatureTemplate(
        id="permissions",
        subcommand="permissions",
        title="Permissions & Ownership",
        icon="🔐",
        description="Visual chmod/chown matrix with live octal preview and dangerous combo warnings",
        wrapped_commands=["chmod", "chown", "stat"],
        arguments=[
            ArgumentDef(
                name="target",
                help="File or directory in current path, or 'choose-directory'",
                required=False,
                default="",
            )
        ],
        renderer_name="run_permissions_cli",
    ),
    FeatureTemplate(
        id="speed-test",
        subcommand="speed-test",
        title="Internet Speed Test",
        icon="⚡",
        description="Real-time internet download, upload bandwidth, and latency speedometer",
        wrapped_commands=["speedtest-cli", "ping", "curl"],
        arguments=[],
        renderer_name="run_speedtest_cli",
    ),
    FeatureTemplate(
        id="shortcuts",
        subcommand="shortcuts",
        title="Command Shortcuts",
        icon="⌨️",
        description="Create, edit, and manage custom terminal command shortcuts with automatic backup",
        wrapped_commands=["alias", "bashrc", "zshrc"],
        arguments=[],
        renderer_name="run_shortcuts_cli",
    ),
]

# Sort features alphabetically by subcommand (A-Z) for clean and predictable listing
FEATURES.sort(key=lambda f: f.subcommand)

# Lookup map by subcommand
FEATURES_BY_SUBCOMMAND: Dict[str, FeatureTemplate] = {
    f.subcommand: f for f in FEATURES
}
