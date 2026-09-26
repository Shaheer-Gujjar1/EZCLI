"""CLI orchestrator for the Hardware Drivers command."""

import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .drivers_engine import detect_hardware_drivers


def run_drivers_cli(console: Optional[Console] = None) -> None:
    """Entry point for `ez drivers`."""
    if console is None:
        console = Console()

    # Step 1: Launch Textual TUI if interactive
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .drivers_tui import DriversApp

            app = DriversApp()
            app.run()
            return

    # Fallback: Rich console output
    devices = detect_hardware_drivers()
    console.print(
        Panel(
            f"Detected Hardware Devices: [bold cyan]{len(devices)}[/bold cyan]\n"
            "EasyCLI scans for proprietary GPU, Wi-Fi, and microcode firmware recommendations.",
            title="🖥️ [bold cyan]EasyCLI Hardware Driver Detector[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if devices:
        table = Table(
            title="Hardware & Driver Recommendations",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("Category", width=18)
        table.add_column("Device Model", width=34)
        table.add_column("Current Driver", width=22)
        table.add_column("Recommended Driver", width=24)
        table.add_column("Status", width=22)

        for dev in devices:
            table.add_row(
                f"{dev.icon} {dev.category}",
                dev.model,
                dev.current_driver,
                dev.recommended_driver or "None needed",
                dev.status_badge,
            )
        console.print(table)
    else:
        console.print("[dim]No hardware devices requiring proprietary drivers detected.[/dim]")
