"""CLI orchestrator for the Bluetooth command."""

import shutil
import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..elevation import elevated_package_install
from .bluetooth_engine import BluetoothManager


def run_bluetooth_cli(console: Optional[Console] = None) -> None:
    """Entry point for `ez bluetooth`."""
    if console is None:
        console = Console()

    manager = BluetoothManager()

    # Step 1: Check if bluetoothctl is installed
    if not manager.is_available():
        console.print(
            Panel(
                "📡 [bold cyan]Bluetooth Management Tools Missing[/bold cyan]\n\n"
                "The [bold yellow]bluez[/bold yellow] package (including `bluetoothctl`) is required to manage Bluetooth connections.\n\n"
                "Would you like EasyCLI to install [bold green]bluez[/bold green] now via the administrator helper?",
                title="[bold yellow]Bluetooth Tools Not Found[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        try:
            if sys.stdin.isatty() and Confirm.ask("[bold cyan]Install bluez now?[/bold cyan]", default=True):
                success = elevated_package_install(
                    ["bluez"],
                    reason="Install BlueZ Bluetooth stack",
                    task_description="Install bluez",
                    console=console,
                )
                if not success:
                    console.print("[bold red]Installation aborted or failed.[/bold red]")
                    return
                console.print("[bold green]✓ BlueZ installed successfully![/bold green]\n")
                manager = BluetoothManager()
            else:
                return
        except (KeyboardInterrupt, EOFError):
            return

    # Step 2: Check if adapter exists
    controller = manager.get_controller()
    if not controller.available:
        console.print(
            Panel(
                "📡 [bold yellow]No Bluetooth Adapter Detected[/bold yellow]\n\n"
                "EasyCLI could not detect an active Bluetooth controller on this machine.\n\n"
                "Possible causes:\n"
                " • Your PC lacks a built-in Bluetooth adapter or USB dongle\n"
                " • Bluetooth is turned off in BIOS or blocked via hardware switch / [bold cyan]rfkill[/bold cyan]\n"
                " • The Bluetooth system service is stopped ([bold cyan]sudo systemctl start bluetooth[/bold cyan])",
                title="[bold yellow]Bluetooth Adapter Unavailable[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        return

    # Step 3: Launch Textual TUI if interactive
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .bluetooth_tui import BluetoothApp

            app = BluetoothApp(manager=manager)
            app.run()
            return

    # Fallback: Rich console output
    devices = manager.list_devices()
    power_str = "[bold green]ON[/bold green]" if controller.powered else "[bold red]OFF[/bold red]"
    console.print(
        Panel(
            f"Controller: [bold cyan]{controller.name}[/bold cyan] ({controller.mac}) | Power: {power_str}\n"
            f"Known & Discovered Devices: {len(devices)}",
            title="📡 [bold cyan]EasyCLI Bluetooth Status[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if devices:
        table = Table(
            title="Bluetooth Devices",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("State", width=14)
        table.add_column("Device Name", width=26)
        table.add_column("MAC Address", width=18)
        table.add_column("Type", width=18)
        table.add_column("Signal", width=10)

        for dev in devices:
            state = "[bold green]Connected[/bold green]" if dev.connected else ("[bold cyan]Paired[/bold cyan]" if dev.paired else "[dim]Available[/dim]")
            table.add_row(
                state,
                f"{dev.icon} {dev.name}",
                dev.mac,
                dev.device_type,
                dev.bars,
            )
        console.print(table)
    else:
        console.print("[dim]No Bluetooth devices currently discovered or paired.[/dim]")
