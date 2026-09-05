"""Rich-based formatters and renderers for EasyCLI subcommands."""

from typing import Any, Dict, List
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

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
    collect_installed_packages,
)


def make_bar(percent: float, width: int = 10) -> str:
    """Generate a compact inline visual bar with color coding."""
    pct = max(0.0, min(100.0, percent))
    filled = round((pct / 100.0) * width)
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
def render_system_info(console: Console, is_admin: bool = False) -> None:
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

    title_admin = " [dim](Admin Mode)[/dim]" if is_admin else ""
    panel = Panel(
        table,
        title=f"[bold cyan]💻 System Information{title_admin}[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 2. Resource Stats Renderer
# ==============================================================================
def render_stats(console: Console, is_admin: bool = False) -> None:
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

    title_admin = " [dim](Admin Mode)[/dim]" if is_admin else ""
    panel = Panel(
        table,
        title=f"[bold cyan]⚡ System Resource Statistics{title_admin}[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


# ==============================================================================
# 3. Disk Space Renderer
# ==============================================================================
def render_disk_info(console: Console, is_admin: bool = False) -> None:
    """Render disk space usage table with inline usage bars."""
    disks = collect_disk_info()

    if not disks:
        console.print("[yellow]No physical or persistent storage partitions found.[/yellow]")
        return

    title_admin = " [dim](Admin Mode)[/dim]" if is_admin else ""
    table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 1), title=f"[bold]Storage Partitions{title_admin}[/bold]")
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
def render_big_files(console: Console, folder: str = "~", is_admin: bool = False) -> None:
    """Scan and render top largest items with partial and full permission handling."""
    status_text = f"Scanning directory '{folder}' (Admin Rights Active)..." if is_admin else f"Scanning directory '{folder}'..."
    with console.status(f"[bold cyan]{status_text}[/bold cyan]", spinner="dots"):
        data = collect_big_files(folder, is_admin=is_admin)

    # 1. Full permission failure
    if data.get("full_failure"):
        console.print(
            Panel(
                "🔒 [bold red]Admin rights are required for this task.[/bold red]\n\n"
                f"EasyCLI cannot inspect '{data['folder']}' without administrator rights.",
                title="[bold yellow]Admin Rights Required[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        if not is_admin and Confirm.ask("Would you like to run it with admin rights now?", default=True):
            render_big_files(console, folder, is_admin=True)
        return

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    items = data.get("items", [])
    if not items:
        console.print(f"[yellow]No files or folders found in {data['folder']}[/yellow]")
        return

    title_admin = " [dim](Admin Mode)[/dim]" if is_admin else ""
    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=f"[bold]Top Largest Items in {data['folder']}{title_admin}[/bold]",
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

    # 2. Partial permission failure offer
    if not is_admin and data.get("partial_failure"):
        console.print()
        if Confirm.ask("⚠️ Some locations were inaccessible. Retry with admin rights? [Y/n]", default=True):
            render_big_files(console, folder, is_admin=True)


# ==============================================================================
# 5. Package Search Renderer
# ==============================================================================
def render_package_choice_card(console: Console, pkg: Dict[str, Any]) -> None:
    """Render platform details, install command, and setup guide for selected package."""
    plat = pkg.get("platform", "apt")
    plat_icon = pkg.get("platform_icon", "📦")
    plat_name = pkg.get("platform_name", "APT")
    name = pkg.get("name", "")
    app_id = pkg.get("app_id", name)
    is_supported = pkg.get("platform_supported", True)

    table = Table(box=None, show_header=False, padding=(0, 2))
    table.add_column("Property", style="bold cyan", no_wrap=True, width=18)
    table.add_column("Value", style="white")

    table.add_row("Platform", f"{plat_icon} {plat_name}")
    table.add_row("Package / App ID", f"[bold green]{app_id}[/bold green]")
    if name != app_id:
        table.add_row("Application Name", name)

    st_text = "[bold green]Installed[/bold green]" if pkg.get("installed") else "[yellow]Available (Not Installed)[/yellow]"
    table.add_row("Installed Status", st_text)

    if pkg.get("description"):
        table.add_row("Description", pkg["description"])

    if is_supported:
        table.add_row("System Support", f"[bold green]✔ {plat_name} runtime is installed on this PC[/bold green]")
        table.add_row("Install Command", f"[bold cyan]{pkg.get('install_cmd', '')}[/bold cyan]")
        if plat == "flatpak":
            table.add_row("Run Command", f"[dim]flatpak run {app_id}[/dim]")
    else:
        table.add_row("System Support", f"[bold red]✖ {plat_name} is NOT installed on this PC[/bold red]")
        table.add_row("Setup Required", f"To enable {plat_name} on Debian/Ubuntu, run:\n[bold yellow]{pkg.get('setup_cmd', '')}[/bold yellow]")
        table.add_row("Then Install", f"[bold cyan]{pkg.get('install_cmd', '')}[/bold cyan]")

    border_color = "cyan" if is_supported else "yellow"
    panel = Panel(
        table,
        title=f"[bold]{plat_icon} {plat_name}: {name}[/bold]",
        border_style=border_color,
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


def render_package_search(console: Console, term: str, interactive: bool = True, is_admin: bool = False) -> None:
    """Render multi-platform package search results (APT, Flatpak, Snap)."""
    with console.status(f"[bold cyan]Searching APT 📦, Flatpak 🟣, and Snap 🟢 for '{term}'...[/bold cyan]", spinner="dots"):
        data = collect_package_search(term)

    if data.get("error"):
        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    packages = data.get("packages", [])
    if not packages:
        tips_table = Table(box=None, show_header=False, padding=(0, 1))
        tips_table.add_column("Icon", style="bold cyan", width=3)
        tips_table.add_column("Guidance", style="white")
        tips_table.add_row("🔄", "Refresh Index: Debian systems read from a local package cache. Run [bold green]sudo apt update[/bold green] to fetch the latest index.")
        tips_table.add_row("🔍", "Broader Search: Try searching with a broader keyword (e.g. 'player', 'codec', or 'video').")
        tips_table.add_row("📦", f"Direct Lookup: If you know the package name, run [bold cyan]ez package {term}[/bold cyan] directly.")
        tips_table.add_row("🌐", "Repositories: Some packages require 'contrib' or 'non-free' in /etc/apt/sources.list.")

        console.print(
            Panel(
                tips_table,
                title=f"[bold yellow]🔍 No Packages Matching '{term}'[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )
        return

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=f"[bold]Search Results for '{term}' ({len(packages)} packages across APT, Flatpak, Snap)[/bold]",
    )
    table.add_column("#", justify="right", style="bold yellow", width=3)
    table.add_column("Platform", style="white", width=12)
    table.add_column("Package / App ID", style="bold green", width=22)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Description", style="white")

    for idx, pkg in enumerate(packages, 1):
        status = "[bold green]Installed[/bold green]" if pkg["installed"] else "[dim]Available[/dim]"
        desc = pkg["description"] or "[dim]No description[/dim]"
        plat_badge = f"{pkg.get('platform_icon', '📦')} {pkg.get('platform_name', 'APT')}"
        table.add_row(str(idx), plat_badge, pkg.get("app_id", pkg["name"]), status, desc)

    console.print(table)

    # Interactive item selection for viewing platform details & install commands
    import sys
    if interactive and sys.stdin.isatty():
        console.print()
        while True:
            try:
                from rich.prompt import Prompt
                choice = Prompt.ask(
                    f"[bold cyan]Select an item [1-{len(packages)}] to view details & install command[/bold cyan] (or press Enter to exit)",
                    default="",
                ).strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not choice:
                break

            if choice.isdigit() and 1 <= int(choice) <= len(packages):
                selected = packages[int(choice) - 1]
                console.print()
                render_package_choice_card(console, selected)
                console.print()
            else:
                console.print(f"[yellow]Please choose a number between 1 and {len(packages)} or press Enter to exit.[/yellow]")


# ==============================================================================
# 6. Package Details Renderer
# ==============================================================================
def render_package(console: Console, name: str, is_admin: bool = False) -> None:
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
def render_available_updates(console: Console, is_admin: bool = False) -> None:
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
        status_table = Table(box=None, show_header=False, padding=(0, 2))
        status_table.add_column("Property", style="bold cyan", width=18)
        status_table.add_column("Value", style="white")
        status_table.add_row("Status", "[bold green]✔ All system packages are up to date[/bold green]")
        status_table.add_row("Upgradable Packages", "[bold green]0 packages pending[/bold green]")
        status_table.add_row("Cache Timestamp", f"{data['last_updated_str']}")
        status_table.add_row("How It Works", "EasyCLI inspects local package indices via [dim]apt list --upgradable[/dim].")
        status_table.add_row("Check For Updates", "To fetch new upstream updates, run [bold cyan]sudo apt update[/bold cyan], then re-check.")

        console.print(
            Panel(
                status_table,
                title="[bold green]🔄 System Update Status[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )
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
def render_service_status(console: Console, service_name: str, is_admin: bool = False) -> None:
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
def render_network_info(console: Console, is_admin: bool = False) -> None:
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
def render_logs(console: Console, lines_count: int = 50, is_admin: bool = False) -> None:
    """Render system logs with severity coloring, handling partial and full permission failures."""
    status_text = f"Retrieving system logs (Admin Rights Active)..." if is_admin else "Retrieving system logs..."
    with console.status(f"[bold cyan]{status_text}[/bold cyan]", spinner="dots"):
        data = collect_logs(lines_count, is_admin=is_admin)

    if data.get("error"):
        if "permission" in data["error"].lower() or "admin rights" in data["error"].lower():
            console.print(
                Panel(
                    "🔒 [bold red]Admin rights are required for this task.[/bold red]\n\n"
                    f"{data['error']}",
                    title="[bold yellow]Admin Rights Required[/bold yellow]",
                    border_style="yellow",
                    box=box.ROUNDED,
                )
            )
            if not is_admin and Confirm.ask("Would you like to run it with admin rights now?", default=True):
                render_logs(console, lines_count, is_admin=True)
            return

        console.print(f"[bold red]Error:[/bold red] {data['error']}")
        return

    logs = data.get("logs", [])
    if not logs:
        console.print("[dim]No journal log entries available.[/dim]")
        return

    title_admin = " [dim](Admin Mode)[/dim]" if is_admin else ""
    console.print(f"\n[bold]📄 Recent System Logs (last {len(logs)} entries){title_admin}:[/bold]")
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

    # Offer elevation if partial failure (user-level logs only)
    if not is_admin and data.get("permission_limited"):
        if Confirm.ask("⚠️ Some locations were inaccessible (showing user-level logs only). Retry with admin rights? [Y/n]", default=True):
            render_logs(console, lines_count, is_admin=True)


# ==============================================================================
# 11. Installed Packages Renderer
# ==============================================================================
def render_installed_packages(console: Console, filter_term: str = "", is_admin: bool = False) -> None:
    """Render installed packages with optional keyword filtering."""
    status_msg = f"Filtering installed packages for '{filter_term}'..." if filter_term else "Scanning installed packages..."
    with console.status(f"[bold cyan]{status_msg}[/bold cyan]", spinner="dots"):
        data = collect_installed_packages(filter_term)

    # Summary Badges Panel
    summary_table = Table(box=None, show_header=False, padding=(0, 2))
    summary_table.add_column("Property", style="bold cyan", width=24)
    summary_table.add_column("Value", style="white")

    breakdown = f"📦 APT: [bold cyan]{data['total_apt']}[/bold cyan]"
    if data["total_flatpak"] > 0:
        breakdown += f"  |  🟣 Flatpak: [bold magenta]{data['total_flatpak']}[/bold magenta]"
    if data["total_snap"] > 0:
        breakdown += f"  |  🟢 Snap: [bold green]{data['total_snap']}[/bold green]"

    summary_table.add_row("Total Installed Packages", f"[bold green]{data['total_count']:,}[/bold green]")
    summary_table.add_row("Ecosystem Breakdown", breakdown)

    if not filter_term:
        summary_table.add_row("Search Tip", "Search installed apps with [cyan]ez installed-package-search <app_name>[/cyan]")
    else:
        summary_table.add_row("Active Search", f"[bold yellow]'{filter_term}'[/bold yellow] ({len(data['matches'])} matching)")

    console.print(
        Panel(
            summary_table,
            title="[bold cyan]📋 Installed Packages Overview[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 1),
        )
    )

    matches = data.get("matches", [])
    if not matches:
        if filter_term:
            console.print(
                Panel(
                    f"[bold yellow]No installed packages matching '{filter_term}' were found.[/bold yellow]\n\n"
                    f"💡 [dim]To search repositories for available packages to install, run:[/dim]\n"
                    f"   [bold cyan]ez package-search {filter_term}[/bold cyan]",
                    border_style="yellow",
                    box=box.ROUNDED,
                    title="[bold yellow]No Matches[/bold yellow]",
                )
            )
        return

    # Limit default view to 50 if no filter
    display_items = matches if filter_term else matches[:50]

    title_str = (
        f"[bold]Installed Packages Matching '{filter_term}' ({len(matches)} found)[/bold]"
        if filter_term
        else f"[bold]Installed Packages (Showing first {len(display_items)} of {data['total_count']:,})[/bold]"
    )

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
        title=title_str,
    )
    table.add_column("#", justify="right", style="bold yellow", width=4)
    table.add_column("Platform", style="white", width=12)
    table.add_column("Package / Application", style="bold green", width=26)
    table.add_column("Version", style="yellow", width=18)
    table.add_column("Size", justify="right", style="dim", width=10)
    table.add_column("Description", style="white")

    for idx, item in enumerate(display_items, 1):
        plat_badge = f"{item['platform_icon']} {item['platform_name']}"
        table.add_row(
            str(idx),
            plat_badge,
            item["name"],
            item["version"] or "-",
            item["size"] or "-",
            item["description"],
        )

    console.print(table)

    if not filter_term and len(matches) > len(display_items):
        console.print(
            f"[dim]Showing {len(display_items)} of {data['total_count']:,} installed packages. "
            f"Run [bold cyan]ez installed-package-search <app_name>[/bold cyan] to search for specific packages.[/dim]\n"
        )


def render_installed_package_search(console: Console, term: str, is_admin: bool = False) -> None:
    """Search installed packages by name (wraps apt list --installed | grep -i <app>)."""
    render_installed_packages(console, filter_term=term)

