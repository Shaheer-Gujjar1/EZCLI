"""Visually distinct Textual TUI application for Proprietary Hardware Drivers."""

import glob
import os
import sys
from typing import List, Optional

venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Horizontal, Vertical  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Static,
)

from .drivers_engine import (
    HardwareDeviceDriver,
    detect_hardware_drivers,
    install_driver_package,
    simulate_driver_installation,
)


class DriverSimulationModal(ModalScreen[bool]):
    """Modal displaying simulation preview and safety checks before installing drivers."""

    DEFAULT_CSS = """
    DriverSimulationModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #sim-box {
        width: 70;
        height: auto;
        border: round #10b981;
        background: #022c22;
        padding: 1 2;
    }
    #sim-title {
        text-style: bold;
        color: #34d399;
        text-align: center;
        margin-bottom: 1;
    }
    #sim-details {
        color: #d1fae5;
        margin-bottom: 1;
    }
    #sim-actions {
        align: center middle;
        height: auto;
    }
    #sim-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, device: HardwareDeviceDriver) -> None:
        super().__init__()
        self.device = device
        self.sim = simulate_driver_installation(device.recommended_driver)

    def compose(self) -> ComposeResult:
        with Vertical(id="sim-box"):
            yield Label("🔬 Driver Installation Simulation & Safety Check", id="sim-title")
            info_text = (
                f"Device: [bold white]{self.device.icon} {self.device.model}[/bold white]\n"
                f"Target Driver: [bold green]{self.device.recommended_driver}[/bold green]\n"
                f"Current Driver: [dim]{self.device.current_driver}[/dim]\n\n"
                f"• Packages to install: [bold]{self.sim.get('new_packages', 1)}[/bold]\n"
                f"• Estimated download: [bold]{self.sim.get('download_size', 'Approx. 100 MB')}[/bold]\n"
                f"• Impact & Risk: [bold yellow]Standard System Kernel Module[/bold yellow]\n"
                f"• Reboot Requirement: [bold red]System reboot required after installation[/bold red]\n\n"
                "EasyCLI will request administrator elevation to complete installation."
            )
            yield Label(info_text, id="sim-details")
            with Horizontal(id="sim-actions"):
                yield Button("🚀 Proceed with Installation", variant="success", id="btn-proceed")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-proceed":
            self.dismiss(True)
        else:
            self.dismiss(False)


class DriversApp(App[None]):
    """Textual interactive terminal Hardware Drivers manager."""

    TITLE = "EasyCLI Hardware Driver Manager"
    SUB_TITLE = "Detect & Safely Install Proprietary Hardware Drivers"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("r", "refresh_devices", "🔄 Rescan Hardware", show=True),
        Binding("i", "install_selected", "🚀 Install Driver", show=True),
        Binding("s", "simulate_selected", "🔬 Simulation Preview", show=True),
    ]

    CSS = """
    Screen {
        background: #022c22;
        color: #ecfdf5;
    }

    #summary-banner {
        height: 3;
        background: #064e3b;
        border: round #10b981;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
    }

    #table-container {
        height: 1fr;
        margin: 0 1;
    }

    DataTable {
        height: 100%;
        border: round #10b981;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #065f46;
        color: #a7f3d0;
    }

    DataTable > .datatable--cursor {
        background: #059669;
        color: white;
        text-style: bold;
    }

    #action-bar {
        height: auto;
        dock: bottom;
        margin: 1;
        align: center middle;
    }

    #action-bar Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.devices: List[HardwareDeviceDriver] = []
        self.selected_device: Optional[HardwareDeviceDriver] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="summary-banner")
        with Vertical(id="table-container"):
            yield DataTable(id="drivers-table", cursor_type="row")
        with Horizontal(id="action-bar"):
            yield Button("🚀 Install Recommended Driver", variant="success", id="btn-install")
            yield Button("🔬 Simulation Preview", variant="primary", id="btn-simulate")
            yield Button("🔄 Rescan", variant="default", id="btn-rescan")
            yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#drivers-table", DataTable)
        table.add_column("Category", width=20)
        table.add_column("Hardware Component", width=36)
        table.add_column("Current Driver", width=22)
        table.add_column("Recommended Driver", width=24)
        table.add_column("Status", width=22)

        self.refresh_devices()

    def refresh_devices(self) -> None:
        self.devices = detect_hardware_drivers()
        banner = self.query_one("#summary-banner", Static)

        needing = sum(1 for d in self.devices if d.needs_driver)
        if needing > 0:
            badge = f"[bold yellow]⚠️ {needing} device(s) have recommended proprietary drivers available[/bold yellow]"
        else:
            badge = "[bold green]✅ All detected hardware is using optimal drivers[/bold green]"

        banner.update(
            f"Detected Hardware: [bold cyan]{len(self.devices)}[/bold cyan] device(s)  |  {badge}"
        )

        table = self.query_one("#drivers-table", DataTable)
        table.clear()

        for idx, dev in enumerate(self.devices):
            cat_str = f"{dev.icon} {dev.category}"
            status_style = "[bold yellow]" if dev.needs_driver else "[bold green]"
            status_text = f"{status_style}{dev.status_badge}[/]"

            table.add_row(
                cat_str,
                dev.model,
                dev.current_driver,
                dev.recommended_driver or "None needed",
                status_text,
                key=str(idx),
            )

        if self.devices:
            self.selected_device = self.devices[0]

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        try:
            idx = int(key)
            self.selected_device = self.devices[idx]
        except (ValueError, IndexError):
            pass

    def action_install_selected(self) -> None:
        if not self.selected_device or not self.selected_device.recommended_driver:
            return

        def on_confirmed(proceed: bool) -> None:
            if proceed and self.selected_device:
                install_driver_package(self.selected_device.recommended_driver)
                self.refresh_devices()

        self.push_screen(DriverSimulationModal(self.selected_device), on_confirmed)

    def action_simulate_selected(self) -> None:
        if not self.selected_device or not self.selected_device.recommended_driver:
            return

        def on_closed(_: bool) -> None:
            pass

        self.push_screen(DriverSimulationModal(self.selected_device), on_closed)

    def action_refresh_devices(self) -> None:
        self.refresh_devices()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-install":
            self.action_install_selected()
        elif event.button.id == "btn-simulate":
            self.action_simulate_selected()
        elif event.button.id == "btn-rescan":
            self.action_refresh_devices()
        elif event.button.id == "btn-close":
            self.exit()
