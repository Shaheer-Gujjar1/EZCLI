"""CLI interface for ez cleanup."""

import sys
from typing import Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.status import Status
from rich.table import Table

from ..elevation import (
    elevated_apt_mark_manual,
    elevated_cleanup_apt,
    elevated_cleanup_autoremove,
    elevated_cleanup_logs,
)
from .cleaner_engine import (
    clean_thumbnails,
    clean_trash,
    detect_desktop_critical_packages,
    format_bytes,
    scan_apt_cache,
    scan_old_logs,
    scan_orphan_packages,
    scan_thumbnails,
    scan_trash,
)


def run_cleanup_cli(console: Optional[Console] = None) -> None:
    """Run the safe interactive system cleaner."""
    if console is None:
        console = Console()

    console.print(
        Panel(
            "[bold cyan]🧹 EasyCLI Safe System Cleaner[/bold cyan]\n\n"
            "Scanning system for removable cache files, orphan packages, trash, and old logs...\n"
            "[dim]Orphan packages are strictly simulated first with desktop-critical protection.[/dim]",
            title="[bold blue]System Cleaner[/bold blue]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    # 1. Scanning phase
    with console.status("[bold green]Scanning categories...[/bold green]"):
        apt_count, apt_bytes = scan_apt_cache()
        orphans, orphans_bytes = scan_orphan_packages()
        trash_count, trash_bytes = scan_trash()
        logs_count, logs_bytes = scan_old_logs()
        thumbs_count, thumbs_bytes = scan_thumbnails()

    critical_orphans = detect_desktop_critical_packages(orphans) if orphans else []

    # 2. Safety Check for Desktop-Critical Packages in Orphans
    if critical_orphans:
        crit_list = "\n".join(f"  • [bold red]{pkg}[/bold red]" for pkg in critical_orphans)
        console.print(
            Panel(
                f"[bold red]⚠️ HIGH RISK: Desktop-Critical Packages Detected in Autoremove![/bold red]\n\n"
                f"The following {len(critical_orphans)} package(s) were flagged as critical for display/desktop stability:\n\n"
                f"{crit_list}\n\n"
                "[yellow]Removing these packages could break your graphical desktop session![/yellow]\n"
                "[bold green]Recommended:[/bold green] Mark them as manually installed so the system safely keeps them.",
                title="[bold red]CRITICAL SAFETY WARNING[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )

        keep_choice = Prompt.ask(
            "[bold cyan]Action[/bold cyan] ([bold green]K[/bold green]=Keep safely via apt-mark manual, [dim]r[/dim]=review all, [dim]c[/dim]=cancel autoremove)",
            choices=["k", "r", "c", "K", "R", "C"],
            default="k",
            console=console,
        ).lower()

        if keep_choice == "k":
            console.print("[dim]Marking critical packages as manual...[/dim]")
            ok, err = elevated_apt_mark_manual(critical_orphans, console=console)
            if ok:
                console.print(f"[bold green]✔ Protected {len(critical_orphans)} critical package(s)![/bold green]")
                # Re-scan orphans
                orphans, orphans_bytes = scan_orphan_packages()
                critical_orphans = []
            else:
                console.print(f"[bold red]Failed to mark packages: {err}[/bold red]")
                orphans = []
                orphans_bytes = 0
        elif keep_choice == "c":
            console.print("[yellow]Autoremove category skipped for safety.[/yellow]")
            orphans = []
            orphans_bytes = 0
        elif keep_choice == "r":
            console.print("\n[bold]Complete orphan removal list:[/bold]")
            console.print(", ".join(orphans) if orphans else "[dim]None[/dim]")
            if not Confirm.ask("Do you STILL want to include orphan packages in this cleanup?", default=False, console=console):
                orphans = []
                orphans_bytes = 0

    # 3. Present Categories Table
    categories = [
        {"id": "apt", "name": "APT Package Cache", "icon": "📦", "count": f"{apt_count} package(s)", "bytes": apt_bytes, "elevated": True},
        {"id": "orphans", "name": "Orphan Dependencies", "icon": "🍂", "count": f"{len(orphans)} package(s)", "bytes": orphans_bytes, "elevated": True},
        {"id": "trash", "name": "User Trash Bin", "icon": "🗑️", "count": f"{trash_count} item(s)", "bytes": trash_bytes, "elevated": False},
        {"id": "logs", "name": "Old Rotated Logs", "icon": "📜", "count": f"{logs_count} log file(s)", "bytes": logs_bytes, "elevated": True},
        {"id": "thumbs", "name": "Thumbnail Cache", "icon": "🖼️", "count": f"{thumbs_count} thumbnail(s)", "bytes": thumbs_bytes, "elevated": False},
    ]

    total_bytes_available = sum(c["bytes"] for c in categories)

    if total_bytes_available == 0:
        console.print(
            Panel(
                "✨ [bold green]System is Already Clean![/bold green]\n\n"
                "No leftover package caches, orphan dependencies, trash, or bloated log files found.\n"
                "[dim]Zero removable junk detected. Everything is tidy![/dim]",
                title="[bold green]Clean System[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
        return

    table = Table(box=box.ROUNDED, title="Removable System Junk by Category")
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Category", style="bold white", width=24)
    table.add_column("Items Found", style="dim", width=18)
    table.add_column("Space to Reclaim", style="green", width=18)

    for idx, c in enumerate(categories, 1):
        size_str = format_bytes(c["bytes"]) if c["bytes"] > 0 else "[dim]0 B[/dim]"
        table.add_row(str(idx), f"{c['icon']} {c['name']}", c["count"], size_str)

    console.print(table)
    console.print(f"Total potential space to reclaim: [bold green]{format_bytes(total_bytes_available)}[/bold green]\n")

    # 4. Selection
    console.print("[bold]Selection Options:[/bold]")
    console.print("  • Press [bold green]Enter[/bold green] to clean [bold]All Categories[/bold]")
    console.print("  • Or enter comma-separated numbers (e.g. [cyan]1, 3, 5[/cyan])")
    console.print("  • Or enter [dim]0[/dim] to cancel\n")

    choice = Prompt.ask("Select categories to clean", default="all", console=console).strip().lower()
    if choice in ["0", "c", "cancel", "q", "quit"]:
        console.print("[dim]Cleanup cancelled. No files were removed.[/dim]")
        return

    selected_categories = []
    if choice in ["all", "a", ""]:
        selected_categories = [c for c in categories if c["bytes"] > 0]
    else:
        indices = [x.strip() for x in choice.split(",") if x.strip()]
        for idx_str in indices:
            if idx_str.isdigit():
                idx_num = int(idx_str)
                if 1 <= idx_num <= len(categories):
                    cat = categories[idx_num - 1]
                    if cat not in selected_categories:
                        selected_categories.append(cat)

    if not selected_categories:
        console.print("[yellow]No categories selected for cleaning. Exiting.[/yellow]")
        return

    # If orphans are selected, confirm explicitly
    orphan_cat = next((c for c in selected_categories if c["id"] == "orphans"), None)
    if orphan_cat and orphans:
        console.print("\n[bold yellow]Orphan Packages to be removed:[/bold yellow]")
        console.print(", ".join(orphans))

    selected_bytes = sum(c["bytes"] for c in selected_categories)
    console.print(
        Panel(
            f"Selected {len(selected_categories)} category(ies).\n"
            f"Total estimated space to free: [bold green]{format_bytes(selected_bytes)}[/bold green]",
            title="[bold cyan]Cleanup Preview[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if not Confirm.ask("Proceed with cleaning the selected categories?", default=True, console=console):
        console.print("[dim]Cleanup cancelled. No files were touched.[/dim]")
        return

    # 5. Execution Phase
    freed_summary: Dict[str, int] = {}

    for cat in selected_categories:
        cat_id = cat["id"]
        cat_name = cat["name"]

        if cat_id == "trash":
            with console.status(f"[cyan]Emptying user trash...[/cyan]"):
                freed = clean_trash()
                freed_summary[cat_name] = freed
        elif cat_id == "thumbs":
            with console.status(f"[cyan]Cleaning thumbnail cache...[/cyan]"):
                freed = clean_thumbnails()
                freed_summary[cat_name] = freed
        elif cat_id == "apt":
            with console.status(f"[cyan]Cleaning APT package cache...[/cyan]"):
                ok, err = elevated_cleanup_apt(console=console)
                if ok:
                    freed_summary[cat_name] = cat["bytes"]
                else:
                    console.print(f"[yellow]APT cache cleanup failed: {err}[/yellow]")
        elif cat_id == "logs":
            with console.status(f"[cyan]Cleaning rotated system logs...[/cyan]"):
                ok, res, err = elevated_cleanup_logs(console=console)
                if ok:
                    freed_summary[cat_name] = res.get("freed_bytes", cat["bytes"])
                else:
                    console.print(f"[yellow]Log cleanup failed: {err}[/yellow]")
        elif cat_id == "orphans":
            with console.status(f"[cyan]Removing orphan packages...[/cyan]"):
                ok, err = elevated_cleanup_autoremove(console=console)
                if ok:
                    freed_summary[cat_name] = cat["bytes"]
                else:
                    console.print(f"[yellow]Orphan autoremove failed: {err}[/yellow]")

    # 6. Final Summary Card
    total_reclaimed = sum(freed_summary.values())
    summary_lines = [f"  • {name}: [bold green]{format_bytes(bytes_freed)}[/bold green]" for name, bytes_freed in freed_summary.items()]

    console.print("\n")
    console.print(
        Panel(
            "✨ [bold green]System Cleanup Complete![/bold green]\n\n"
            f"Total Disk Space Reclaimed: [bold green]{format_bytes(total_reclaimed)}[/bold green]\n\n"
            + "\n".join(summary_lines) + "\n\n"
            "[dim]All temporary junk and caches were safely cleared.[/dim]",
            title="[bold green]Cleanup Summary[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )
