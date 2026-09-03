"""Rich-based formatters and renderers for EasyCLI subcommands."""

from typing import Any, Dict, List, Optional
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .collectors import (
    collect_system_info,
    collect_stats,
    collect_disk_info,
    collect_big_files,
    collect_package_search,
    collect_package_info,
    collect_available_updates,
    collect_service_status,
    collect_network_info,
    collect_logs,
)


def make_bar(percent: float, width: int = 10) -> str:
    """Generate a compact inline visual bar with color coding."""
    pct = max(0.0, min(100.0, float(percent)))
    filled = int(round((pct / 100.0) * width))
    empty = width - filled
    bar_chars = "█" * filled + "░" * empty
    if pct >= 85:
        color = "bold red"
    elif pct >= 65:
        color = "bold yellow"
    else:
        color = "bold green"
    return f"[{color}]{bar_chars}[/{color}] {pct:.1f}%"


# ==============================================================================
# 1. System Info Renderer
# ==============================================================================
def render_system_info(console: Console) -> None:
    """Render system info card."""
    data = collect_system_info()

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")

    distro_str = data["os_name"]
    if data["codename"]:
        distro_str += f" ({data['codename']})"
    if data["is_debian_based"]:
        distro_str += " [green](Debian-based)[/green]"

    table.add_row("Distribution", distro_str)
    table.add_row("Hostname", data["hostname"])
    table.add_row("Kernel", data["kernel"])
    table.add_row("Architecture", data["arch"])
    table.add_row("System Uptime", f"[bold green]{data['uptime']}[/bold green]")

    if data.get("hardware_model"):
        table.add_row("Hardware Model", data["hardware_model"])
    if data.get("chassis"):
        table.add_row("Chassis Type", data["chassis"])

    panel = Panel(
        table,
        title="[bold cyan]💻 System Information[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 2. Resource Stats Renderer
# ==============================================================================
def render_stats(console: Console) -> None:
    """Render CPU and RAM usage statistics card."""
    data = collect_stats()

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="bold cyan", no_wrap=True, width=14)
    table.add_column("Usage Bar", style="white", width=22)
    table.add_column("Details", style="bright_white")

    # CPU Load
    cpu_bar = make_bar(data["load_percent"], width=12)
    cpu_details = f"1m: {data['load_1m']} | 5m: {data['load_5m']} | 15m: {data['load_15m']} ({data['cpu_cores']} cores)"
    table.add_row("CPU Load", cpu_bar, cpu_details)

    # RAM Usage
    ram_bar = make_bar(data["ram_percent"], width=12)
    ram_details = f"{data['ram_used_str']} used / {data['ram_total_str']} total (avail: {data['ram_avail_str']})"
    table.add_row("Memory (RAM)", ram_bar, ram_details)

    # Swap Usage
    if data["swap_total_str"] and data["swap_total_str"] != "0B":
        swap_bar = make_bar(data["swap_percent"], width=12)
        swap_details = f"{data['swap_used_str']} used / {data['swap_total_str']} total"
        table.add_row("Swap Space", swap_bar, swap_details)

    panel = Panel(
        table,
        title="[bold cyan]⚡ System Resource Statistics[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 3. Disk Space Renderer
# ==============================================================================
def render_disk_info(console: Console) -> None:
    """Render disk space usage table with inline usage bars."""
    disks = collect_disk_info()

    if not disks:
        console.print("[yellow]No physical or persistent storage partitions found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 1), title="[bold]Storage Partitions[/bold]")
    table.add_column("Mount Point", style="bold green", no_wrap=True)
    table.add_column("Filesystem", style="dim white")
    table.add_column("Total", justify="right", style="cyan")
    table.add_column("Used", justify="right", style="magenta")
    table.add_column("Avail", justify="right", style="bold green")
    table.add_column("Usage", style="white", justify="left")

    for d in disks:
        bar = make_bar(d["percent"], width=8)
        table.add_row(
            d["mount"],
            d["filesystem"],
            d["size"],
            d["used"],
            d["available"],
            bar,
        )

    console.print(table)


# ==============================================================================
# 4. Big Files Renderer
# ==============================================================================
def render_big_files(console: Console, folder: str = "~") -> None:
    """Scan and render top largest items."""
    with console.status(f"[bold cyan]Scanning directory '{folder}'...[/bold cyan]", spinner="dots"):
        data = collect_big_files(folder)

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    items = data.get("items", [])
    if not items:
        console.print(f"[yellow]No files or folders found in {data['folder']}[/yellow]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=f"[bold]Top Largest Items in {data['folder']}[/bold]",
    )
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Type", justify="center", style="cyan", width=5)
    table.add_column("Size", justify="right", style="bold yellow", width=10)
    table.add_column("Name", style="white")

    for idx, item in enumerate(items, 1):
        type_icon = "📁" if item["is_dir"] else "📄"
        table.add_row(
            str(idx),
            type_icon,
            item["size_str"],
            item["name"],
        )

    console.print(table)


# ==============================================================================
# 5. Package Search Renderer
# ==============================================================================
def render_package_search(console: Console, term: str) -> None:
    """Render package search results."""
    with console.status(f"[bold cyan]Searching repositories for '{term}'...[/bold cyan]", spinner="dots"):
        data = collect_package_search(term)

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    packages = data.get("packages", [])
    if not packages:
        console.print(f"[yellow]No packages matching '{term}' were found.[/yellow]")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=f"[bold]Search Results for '{term}' ({len(packages)} packages)[/bold]",
    )
    table.add_column("Package", style="bold green", no_wrap=True)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Description", style="white")

    for pkg in packages:
        status = "[bold green]Installed[/bold green]" if pkg["installed"] else "[dim]Available[/dim]"
        desc = pkg["description"] or "[dim]No description[/dim]"
        table.add_row(pkg["name"], status, desc)

    console.print(table)


# ==============================================================================
# 6. Package Details Renderer
# ==============================================================================
def render_package(console: Console, name: str) -> None:
    """Render detailed package information card."""
    with console.status(f"[bold cyan]Querying details for package '{name}'...[/bold cyan]", spinner="dots"):
        data = collect_package_info(name)

    if not data["found"]:
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold cyan", no_wrap=True, width=16)
    table.add_column("Value", style="white")

    # Installed Status Badge
    if data["is_installed"]:
        status_text = f"[bold green]Installed[/bold green] (v{data['installed_version']})"
    else:
        status_text = "[bold yellow]Not Installed[/bold yellow]"
    table.add_row("Installation", status_text)

    if data["repo_version"] and data["repo_version"] != data["installed_version"]:
        table.add_row("Repo Candidate", data["repo_version"])
    if data["section"]:
        table.add_row("Section", data["section"])
    if data["size"]:
        table.add_row("Download Size", data["size"])
    if data["installed_size"]:
        table.add_row("Installed Size", data["installed_size"])
    if data["homepage"]:
        table.add_row("Homepage", f"[link={data['homepage']}]{data['homepage']}[/link]")
    if data["maintainer"]:
        table.add_row("Maintainer", data["maintainer"])

    if data["description"]:
        table.add_row("Description", data["description"])

    panel = Panel(
        table,
        title=f"[bold cyan]📦 Package: {data['name']}[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 7. Available Updates Renderer
# ==============================================================================
def render_available_updates(console: Console) -> None:
    """Render list of upgradable packages without running apt update."""
    with console.status("[bold cyan]Checking upgradable packages...[/bold cyan]", spinner="dots"):
        data = collect_available_updates()

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    # Check freshness warning
    if data["is_stale"]:
        console.print(
            Panel(
                f"[bold yellow]Friendly Note:[/bold yellow] Results depend on existing repository lists.\n"
                f"Lists were last refreshed: [bold]{data['last_updated_str']}[/bold].\n"
                f"EasyCLI is strictly read-only and never runs 'apt update' automatically.",
                box=box.ROUNDED,
                border_style="yellow",
            )
        )

    updates = data.get("updates", [])
    if not updates:
        console.print("[bold green]System is up to date![/bold green] No upgradable packages found.")
        return

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=f"[bold]Available Updates ({data['count']} packages)[/bold]",
    )
    table.add_column("Package", style="bold white", no_wrap=True)
    table.add_column("Current Version", style="yellow")
    table.add_column("New Version", style="bold green")
    table.add_column("Arch", style="dim")

    for u in updates:
        table.add_row(u["package"], u["current_version"], u["new_version"], u.get("arch", ""))

    console.print(table)


# ==============================================================================
# 8. Service Status Renderer
# ==============================================================================
def render_service_status(console: Console, service_name: str) -> None:
    """Render systemd service status card."""
    data = collect_service_status(service_name)

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold cyan", no_wrap=True, width=16)
    table.add_column("Value", style="white")

    # State indicator
    active_st = data["active_state"]
    if active_st == "active":
        act_badge = "[bold green]● Active (Running)[/bold green]"
    elif active_st == "inactive":
        act_badge = "[bold yellow]○ Inactive (Dead)[/bold yellow]"
    elif active_st == "failed":
        act_badge = "[bold red]✖ Failed[/bold red]"
    elif active_st == "not-found":
        act_badge = "[bold red]Unit Not Found[/bold red]"
    else:
        act_badge = f"[bold yellow]{active_st}[/bold yellow]"

    table.add_row("Service Unit", data["unit"])
    table.add_row("Running State", act_badge)

    # Boot enablement
    enabled_st = data["enabled_state"]
    if enabled_st == "enabled":
        en_badge = "[bold green]Enabled (Starts on boot)[/bold green]"
    elif enabled_st == "disabled":
        en_badge = "[dim yellow]Disabled[/dim yellow]"
    elif enabled_st == "masked":
        en_badge = "[bold red]Masked[/bold red]"
    else:
        en_badge = enabled_st
    table.add_row("Boot State", en_badge)

    if data["sub_state"] and data["sub_state"] != "unknown":
        table.add_row("Sub State", data["sub_state"])
    if data["main_pid"]:
        table.add_row("Main PID", data["main_pid"])
    if data["description"]:
        table.add_row("Description", data["description"])

    border_color = "green" if active_st == "active" else ("red" if active_st in ("failed", "not-found") else "yellow")

    panel = Panel(
        table,
        title=f"[bold]⚙️ Service: {data['service']}[/bold]",
        border_style=border_color,
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 9. Network Info Renderer
# ==============================================================================
def render_network_info(console: Console) -> None:
    """Render network interfaces, gateway, DNS, and connectivity status."""
    data = collect_network_info()

    # Summary Panel
    summary_table = Table(box=None, show_header=False, padding=(0, 2))
    summary_table.add_column("Property", style="bold cyan", width=18)
    summary_table.add_column("Value", style="white")

    online_badge = (
        "[bold green]Connected (Online)[/bold green]"
        if "Online" in data["online_state"]
        else "[bold red]Offline / Disconnected[/bold red]"
    )
    summary_table.add_row("Internet Status", online_badge)
    summary_table.add_row("Default Gateway", f"{data['default_gateway']} [dim]({data['default_interface']})[/dim]")
    dns_str = ", ".join(data["dns_servers"]) if data["dns_servers"] else "[dim]None detected[/dim]"
    summary_table.add_row("DNS Servers", dns_str)

    console.print(
        Panel(
            summary_table,
            title="[bold cyan]🌐 Network Overview[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )

    # Interfaces Table
    if data["interfaces"]:
        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 1),
            title="[bold]Network Interfaces[/bold]",
        )
        table.add_column("Interface", style="bold cyan", no_wrap=True)
        table.add_column("Status", justify="center", width=10)
        table.add_column("IPv4 Address", style="bold white")
        table.add_column("MAC Address", style="dim")

        for iface in data["interfaces"]:
            st = "[bold green]UP[/bold green]" if iface["is_up"] else "[dim red]DOWN[/dim red]"
            ipv4_str = ", ".join(iface["ipv4"]) if iface["ipv4"] else "[dim]None[/dim]"
            table.add_row(iface["name"], st, ipv4_str, iface["mac"] or "-")

        console.print(table)


# ==============================================================================
# 10. Logs Renderer
# ==============================================================================
def render_logs(console: Console, lines_count: int = 50) -> None:
    """Render system logs with severity coloring."""
    data = collect_logs(lines_count)

    if data.get("permission_limited") and data.get("permission_message"):
        console.print(
            Panel(
                f"[bold yellow]{data['permission_message']}[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                title="[bold yellow]Journal Permissions[/bold yellow]",
            )
        )

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    logs = data.get("logs", [])
    if not logs:
        console.print("[dim]No journal log entries available.[/dim]")
        return

    console.print(f"\n[bold]📄 Recent System Logs (last {len(logs)} entries):[/bold]")
    for entry in logs:
        lvl = entry["level"]
        raw = entry["raw"]
        if lvl == "error":
            console.print(f"[bold red]{raw}[/bold red]")
        elif lvl == "warning":
            console.print(f"[yellow]{raw}[/yellow]")
        elif lvl == "ok":
            console.print(f"[green]{raw}[/green]")
        else:
            console.print(raw)
    console.print()
