"""Interactive CLI workflows and rendering for 'ez update' and 'ez upgrade'.

Safe, beginner-friendly package catalog updates and comprehensive system upgrades.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from .collectors import collect_available_updates, format_bytes
from .elevation import (
    ElevationSession,
    authenticate_elevation_session,
    elevated_apt_simulate_upgrade,
    elevated_apt_update,
    elevated_apt_upgrade,
    elevated_flatpak_update,
    elevated_snap_refresh,
    elevated_timeshift_snapshot,
    explain_elevation,
    is_root,
)


# ==============================================================================
# Helper Functions: Snaps, Flatpaks, Reboot Checks, Risk Analysis
# ==============================================================================

def check_flatpak_updates() -> List[str]:
    """Return list of Flatpak applications/runtimes with available updates."""
    if not shutil.which("flatpak"):
        return []
    try:
        proc = subprocess.run(
            ["flatpak", "remote-ls", "--updates"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            lines = [l.split("\t")[0].strip() for l in proc.stdout.splitlines() if l.strip()]
            return [l for l in lines if l]
    except Exception:
        pass
    return []


def check_snap_updates() -> List[str]:
    """Return list of Snap packages with available updates."""
    if not shutil.which("snap"):
        return []
    try:
        proc = subprocess.run(
            ["snap", "refresh", "--list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            lines = proc.stdout.splitlines()
            if len(lines) > 1:
                # First line is header: Name Version Rev Size Publisher Notes
                return [l.split()[0].strip() for l in lines[1:] if l.strip()]
    except Exception:
        pass
    return []


def assess_upgrade_risk(
    apt_pkgs: List[str],
    download_size: str,
    new_pkgs: List[str],
) -> Tuple[str, str]:
    """Determine upgrade risk level (Medium vs High) based on package types and volume."""
    high_risk_triggers = [
        "linux-image",
        "linux-headers",
        "linux-generic",
        "libc6",
        "systemd",
        "udev",
        "grub",
        "dbus",
        "xorg",
        "wayland",
    ]

    reasons: List[str] = []

    # Check for core system packages
    for pkg in apt_pkgs + new_pkgs:
        for trigger in high_risk_triggers:
            if trigger in pkg.lower():
                reasons.append(f"Core system component: {pkg}")
                break

    # Check package volume
    if len(apt_pkgs) > 40:
        reasons.append(f"Large package volume ({len(apt_pkgs)} packages)")

    if reasons:
        return "high", "; ".join(reasons[:2])
    return "medium", "Standard software maintenance"


# ==============================================================================
# Command 1: ez update (Catalog Refresh Only)
# ==============================================================================

def run_cli_update(console: Optional[Console] = None) -> None:
    """Execute 'ez update': Refresh repository package catalog without installing software."""
    console = console or Console()

    console.print(
        Panel(
            "🔄 [bold cyan]Software Catalog Refresh[/bold cyan]\n\n"
            "This command connects to your configured package repositories to check\n"
            "for new versions and security patches.\n\n"
            "[bold green]✔ Strictly Read-Only:[/bold green] Nothing will be installed, upgraded, or removed.\n"
            "[dim]Admin authentication is required to write updated repository metadata\n"
            "to /var/lib/apt/lists/.[/dim]",
            title="[bold cyan]EasyCLI Software Update[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # 1. Elevation Flow: Upfront consent & password authentication
    reason = "Refresh software repository package lists in /var/lib/apt/lists/"
    task_desc = "Fetch updated catalog of available software from package repositories"

    if not is_root():
        approved = explain_elevation(reason, task_desc, risk_level="low", console=console)
        if not approved:
            console.print("[yellow]Update cancelled. No repository lists were changed.[/yellow]")
            return

        session = authenticate_elevation_session(
            reason=reason,
            task_description=task_desc,
            risk_level="low",
            skip_explanation=True,
            console=console,
        )
        if not session:
            return
    else:
        session = ElevationSession(password="")

    # 2. Execution with status: Password was ALREADY verified, so spinner runs only during real work!
    with session:
        with console.status("[bold cyan]Connecting to repositories and updating catalog...[/bold cyan]", spinner="dots"):
            success, res, err = elevated_apt_update(
                reason=reason,
                task_description=task_desc,
                risk_level="low",
                skip_explanation=True,
                console=console,
            )

    if not success or not res:
        console.print(
            Panel(
                f"[bold red]Failed to update software catalog:[/bold red]\n\n{err or 'Unknown error occurred.'}\n\n"
                "[dim]Tip: Check your Internet connection or review /etc/apt/sources.list.[/dim]",
                title="[bold red]Update Notice[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        return

    # 3. Check for repository notices / warnings
    warnings = res.get("warnings", [])
    if warnings:
        warn_text = "\n".join(f"  • {w}" for w in warnings[:5])
        if len(warnings) > 5:
            warn_text += f"\n  • [dim]...and {len(warnings) - 5} more notice(s)[/dim]"
        console.print(
            Panel(
                f"[bold yellow]Repository Notices:[/bold yellow]\n\n{warn_text}\n\n"
                "[dim]These are informational notices from individual repositories (e.g. expired keys or skipped architectures).\n"
                "Your main repositories were refreshed successfully.[/dim]",
                title="[bold yellow]Repository Warning[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )

    # 4. Success Summary: Count known upgradable packages
    updates_info = collect_available_updates()
    upgradable_count = updates_info.get("count", 0)

    count_str = (
        f"[bold green]{upgradable_count} package(s) can be upgraded[/bold green]"
        if upgradable_count > 0
        else "[bold green]Your software catalog is up to date (no upgrades pending)[/bold green]"
    )

    next_steps = (
        "\n\n[bold cyan]Next Steps:[/bold cyan]\n"
        "  • View list of updates: [bold green]ez available-updates[/bold green]\n"
        "  • Install updates safely: [bold green]ez upgrade[/bold green]"
        if upgradable_count > 0
        else ""
    )

    anti_panic_line = (
        "\n\n[bold white]💡 Note:[/bold white] [dim]This was only an information refresh — nothing was installed.\n"
        "You do not need to run this repeatedly.[/dim]"
    )

    console.print(
        Panel(
            f"✔ [bold green]Software catalog refreshed successfully![/bold green]\n\n"
            f"  • Repository hits: [cyan]{res.get('repos_hit', 0)}[/cyan] cached, [cyan]{res.get('repos_get', 0)}[/cyan] updated\n"
            f"  • Status: {count_str}"
            f"{next_steps}"
            f"{anti_panic_line}",
            title="[bold cyan]🔄 Software Catalog Updated[/bold cyan]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


# ==============================================================================
# Command 2: ez upgrade (Comprehensive System Upgrade)
# ==============================================================================

def run_cli_upgrade(console: Optional[Console] = None) -> None:
    """Execute 'ez upgrade': Comprehensive upgrade across APT, Flatpak, and Snap."""
    console = console or Console()

    console.print(
        Panel(
            "⬆️ [bold cyan]Comprehensive System Upgrade[/bold cyan]\n\n"
            "EasyCLI will inspect all available software sources on your system\n"
            "(APT packages, Flatpaks, and Snaps) and prepare a safe upgrade plan.\n\n"
            "[bold green]✔ Safe Upgrade Semantics:[/bold green] Standard non-destructive upgrades only.\n"
            "Will [bold red]never[/bold red] force package removals or execute full system replacements.\n"
            "[dim]A single administrator consent covers the complete upgrade operation.[/dim]",
            title="[bold cyan]EasyCLI System Upgrade[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    # 1. Single Elevation Consent & Upfront Authentication
    reason = "Install system package upgrades and refresh desktop application runtimes"
    task_desc = "Perform a multi-source system upgrade (APT, Flatpak, Snap) with safety preview"

    if not is_root():
        approved = explain_elevation(reason, task_desc, risk_level="medium", console=console)
        if not approved:
            console.print("[yellow]Upgrade cancelled. No packages were modified.[/yellow]")
            return

        session = authenticate_elevation_session(
            reason=reason,
            task_description=task_desc,
            risk_level="medium",
            skip_explanation=True,
            console=console,
        )
        if not session:
            return
    else:
        session = ElevationSession(password="")

    with session:
        # 2. Step 1: Refresh Lists
        with console.status("[bold cyan]Step 1/5: Checking for latest updates across all sources...[/bold cyan]", spinner="dots"):
            elevated_apt_update(skip_explanation=True, console=console)

        # 3. Step 2: Impact Preview (Simulation)
        with console.status("[bold cyan]Step 2/5: Calculating upgrade impact preview...[/bold cyan]", spinner="dots"):
            sim_success, sim_data, sim_err = elevated_apt_simulate_upgrade(skip_explanation=True, console=console)
            flatpak_updates = check_flatpak_updates()
            snap_updates = check_snap_updates()

        if not sim_success or not sim_data:
            console.print(
                Panel(
                    f"[bold red]Unable to calculate upgrade simulation:[/bold red]\n\n{sim_err or 'Simulation failed.'}",
                    title="[bold red]Simulation Error[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            return

        apt_upgrades = sim_data.get("upgraded_packages", [])
        apt_new = sim_data.get("new_packages", [])
        apt_kept = sim_data.get("kept_back_packages", [])
        download_size = sim_data.get("download_size", "")
        disk_delta = sim_data.get("disk_delta", "")

        total_update_count = len(apt_upgrades) + len(flatpak_updates) + len(snap_updates)

        # If completely up to date
        if total_update_count == 0:
            console.print(
                Panel(
                    "✨ [bold green]Your system is completely up to date![/bold green]\n\n"
                    "All APT packages, Flatpaks, and Snaps are at their latest versions.\n\n"
                    "[dim]Done. Run this only when you choose to — there is no daily obligation.[/dim]",
                    title="[bold green]No Upgrades Pending[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
            return

        # Determine Risk Badge
        risk_level, risk_reason = assess_upgrade_risk(apt_upgrades, download_size, apt_new)
        if risk_level == "high":
            risk_badge = f"[bold red]⚠️ RISK LEVEL: HIGH[/bold red] ({risk_reason})"
            badge_border = "red"
        else:
            risk_badge = f"[bold yellow]ℹ️ RISK LEVEL: MEDIUM[/bold yellow] ({risk_reason})"
            badge_border = "yellow"

        # Render Impact Preview Table
        preview_table = Table(box=box.ROUNDED, border_style="cyan", padding=(0, 1))
        preview_table.add_column("Software Source", style="bold cyan", width=18)
        preview_table.add_column("Packages Pending", justify="right", style="bold green", width=18)
        preview_table.add_column("Details", style="white")

        # APT Row
        apt_detail = f"Download: {download_size or 'Unknown'}"
        if disk_delta:
            apt_detail += f" ({disk_delta})"
        preview_table.add_row("📦 APT (System)", f"{len(apt_upgrades)} upgradable", apt_detail)

        # Flatpak Row
        if shutil.which("flatpak"):
            fp_str = f"{len(flatpak_updates)} upgradable" if flatpak_updates else "Up to date"
            fp_detail = ", ".join(flatpak_updates[:3]) + ("..." if len(flatpak_updates) > 3 else "") if flatpak_updates else "No updates pending"
            preview_table.add_row("🟣 Flatpak", fp_str, fp_detail)

        # Snap Row
        if shutil.which("snap"):
            sn_str = f"{len(snap_updates)} upgradable" if snap_updates else "Up to date"
            sn_detail = ", ".join(snap_updates[:3]) + ("..." if len(snap_updates) > 3 else "") if snap_updates else "No updates pending"
            preview_table.add_row("🟢 Snap", sn_str, sn_detail)

        console.print(
            Panel(
                f"{risk_badge}\n\n"
                f"[bold]Total Software Items to Upgrade:[/bold] [cyan]{total_update_count}[/cyan]\n\n"
                f"[bold]Breakdown by Source:[/bold]",
                title="[bold cyan]Step 2/5: Upgrade Impact Preview[/bold cyan]",
                border_style=badge_border,
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print(preview_table)

        # Show kept back packages if any
        if apt_kept:
            kept_sample = ", ".join(apt_kept[:6])
            if len(apt_kept) > 6:
                kept_sample += f" [dim](+{len(apt_kept) - 6} more)[/dim]"
            console.print(
                Panel(
                    f"⏸️ [bold yellow]{len(apt_kept)} package(s) were kept back:[/bold yellow]\n\n"
                    f"  {kept_sample}\n\n"
                    "[dim]Why? These packages require new dependencies or conflict with existing configurations.\n"
                    "EasyCLI preserves system stability by not forcing removals. They will be handled in a future update.[/dim]",
                    title="[bold yellow]Held-Back Packages (Preserved)[/bold yellow]",
                    border_style="yellow",
                    box=box.ROUNDED,
                )
            )

        # Timeshift Snapshot Recommendation
        if shutil.which("timeshift"):
            console.print(
                Panel(
                    "🛡️ [bold cyan]Timeshift System Restore Available[/bold cyan]\n\n"
                    "Timeshift is installed on your computer. It is recommended to create a\n"
                    "system snapshot before applying updates so you can easily roll back if needed.",
                    title="[bold cyan]System Restore Point[/bold cyan]",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
            )
            do_snapshot = Confirm.ask("Would you like to create a Timeshift snapshot now?", default=True)
            if do_snapshot:
                with console.status("[bold cyan]Creating Timeshift snapshot...[/bold cyan]", spinner="dots"):
                    ts_ok, ts_res, ts_err = elevated_timeshift_snapshot(
                        comment="Pre-ez-upgrade snapshot",
                        skip_explanation=True,
                        console=console,
                    )
                if ts_ok:
                    console.print("[green]✔ Timeshift snapshot created successfully.[/green]\n")
                else:
                    console.print(f"[yellow]Warning: Could not create Timeshift snapshot ({ts_err}). Proceeding anyway.[/yellow]\n")

        # 4. Step 3: User Confirmation
        console.print()
        proceed = Confirm.ask(f"[bold cyan]Proceed with upgrading {total_update_count} package(s)?[/bold cyan]", default=True)
        if not proceed:
            console.print("[yellow]Upgrade cancelled by user. No packages were modified.[/yellow]")
            return

        # 5. Step 4: Per-Source Progress Execution
        upgraded_sources: List[str] = []

        # Execute APT Upgrade
        if apt_upgrades:
            with console.status(f"[bold cyan]Step 4/5: Installing {len(apt_upgrades)} APT package upgrade(s)...[/bold cyan]", spinner="dots"):
                apt_ok, apt_res, apt_err = elevated_apt_upgrade(skip_explanation=True, console=console)
            if apt_ok:
                upgraded_sources.append(f"✔ APT: {len(apt_upgrades)} package(s) upgraded successfully")
            else:
                console.print(f"[bold red]APT Upgrade Warning:[/bold red] {apt_err or 'Some packages could not be installed.'}")

        # Execute Flatpak Update
        if flatpak_updates:
            with console.status(f"[bold cyan]Updating {len(flatpak_updates)} Flatpak application(s)...[/bold cyan]", spinner="dots"):
                fp_ok, fp_res, fp_err = elevated_flatpak_update(skip_explanation=True, console=console)
            if fp_ok:
                upgraded_sources.append(f"✔ Flatpak: {len(flatpak_updates)} update(s) applied")
            else:
                console.print(f"[bold red]Flatpak Update Warning:[/bold red] {fp_err}")

        # Execute Snap Refresh
        if snap_updates:
            with console.status(f"[bold cyan]Refreshing {len(snap_updates)} Snap package(s)...[/bold cyan]", spinner="dots"):
                sn_ok, sn_res, sn_err = elevated_snap_refresh(skip_explanation=True, console=console)
            if sn_ok:
                upgraded_sources.append(f"✔ Snap: {len(snap_updates)} package(s) refreshed")
            else:
                console.print(f"[bold red]Snap Refresh Warning:[/bold red] {sn_err}")

        # 6. Step 5: Success Summary & Reboot Check
        reboot_needed = os.path.exists("/var/run/reboot-required")
        reboot_pkgs = ""
        if reboot_needed and os.path.exists("/var/run/reboot-required.pkgs"):
            try:
                with open("/var/run/reboot-required.pkgs", "r") as f:
                    reboot_pkgs = ", ".join([l.strip() for l in f.readlines() if l.strip()])
            except Exception:
                pass

        reboot_notice = ""
        if reboot_needed:
            reboot_notice = (
                "\n\n[bold yellow]🔄 System Restart Recommended:[/bold yellow]\n"
                "Some updated components (such as the Linux kernel or system libraries)\n"
                "require a system restart to take full effect.\n"
            )
            if reboot_pkgs:
                reboot_notice += f"[dim]Affected packages: {reboot_pkgs}[/dim]\n"

        sources_summary = "\n".join(f"  {s}" for s in upgraded_sources) if upgraded_sources else "  ✔ System packages updated"

        reassurance_note = (
            "\n[bold white]✨ Done.[/bold white] [dim]Run this only when you choose to — there is no daily obligation.[/dim]"
        )

        console.print(
            Panel(
                f"[bold green]System upgrade completed successfully![/bold green]\n\n"
                f"[bold]Summary of Operations:[/bold]\n"
                f"{sources_summary}"
                f"{reboot_notice}"
                f"{reassurance_note}",
                title="[bold green]🎉 Upgrade Complete[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
