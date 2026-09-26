"""Visually distinct Textual TUI application for Proprietary Hardware Drivers (IObit Driver Booster style)."""

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

from textual import work  # type: ignore
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
    install_all_drivers,
    install_driver_package,
    simulate_all_drivers_installation,
    simulate_driver_installation,
)


class DriverBoosterInstallAllModal(ModalScreen[bool]):
    """Modal displaying 1-Click Driver Booster batch download & installation plan."""

    DEFAULT_CSS = """
    DriverBoosterInstallAllModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #batch-box {
        width: 76;
        height: auto;
        border: round #00e676;
        background: #09131e;
        padding: 1 2;
    }
    #batch-title {
        text-style: bold;
        color: #00e676;
        text-align: center;
        margin-bottom: 1;
    }
    #batch-details {
        color: #e2e8f0;
        margin-bottom: 1;
    }
    #batch-actions {
        align: center middle;
        height: auto;
    }
    #batch-actions Button {
        min-width: 18;
        margin: 0 1;
    }
    """

    def __init__(self, pending_devices: List[HardwareDeviceDriver], packages: List[str]) -> None:
        super().__init__()
        self.pending_devices = pending_devices
        self.packages = packages
        self.sim = simulate_all_drivers_installation(packages)

    def compose(self) -> ComposeResult:
        with Vertical(id="batch-box"):
            yield Label("⚡ 1-Click Driver Booster Batch Installation", id="batch-title")

            lines = [
                f"[bold white]Pending Drivers to Download & Install ({len(self.packages)}):[/bold white]"
            ]
            for dev in self.pending_devices:
                lines.append(f"  • {dev.icon} [bold cyan]{dev.model}[/bold cyan] -> [bold green]{dev.recommended_driver}[/bold green]")

            new_pkgs = self.sim.get("new_packages", len(self.packages))
            dl_size = self.sim.get("download_size", "Approx. 50-300 MB")

            lines.extend([
                "",
                f"• Packages to install: [bold]{new_pkgs}[/bold]",
                f"• Estimated download: [bold green]{dl_size}[/bold green]",
                "• Elevation: [bold yellow]Requires administrator permissions (sudo)[/bold yellow]",
                "• Reboot: [bold red]A system reboot is recommended after installation[/bold red]",
                "",
                "EasyCLI will install all recommended drivers in a single clean batch.",
            ])

            yield Label("\n".join(lines), id="batch-details")
            with Horizontal(id="batch-actions"):
                yield Button("⚡ Start 1-Click Install", variant="success", id="btn-proceed-all")
                yield Button("❌ Cancel", variant="default", id="btn-cancel-all")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-proceed-all":
            self.dismiss(True)
        else:
            self.dismiss(False)


class DriverSimulationModal(ModalScreen[bool]):
    """Modal displaying simulation preview and safety checks for a single driver."""

    DEFAULT_CSS = """
    DriverSimulationModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #sim-box {
        width: 72;
        height: auto;
        border: round #38bdf8;
        background: #09131e;
        padding: 1 2;
    }
    #sim-title {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 1;
    }
    #sim-details {
        color: #e2e8f0;
        margin-bottom: 1;
    }
    #sim-actions {
        align: center middle;
        height: auto;
    }
    #sim-actions Button {
        min-width: 18;
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
                f"• Reboot Requirement: [bold red]System reboot recommended after installation[/bold red]\n\n"
                "EasyCLI will request administrator elevation to complete installation."
            )
            yield Label(info_text, id="sim-details")
            with Horizontal(id="sim-actions"):
                yield Button("🚀 Proceed with Install", variant="success", id="btn-proceed")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-proceed":
            self.dismiss(True)
        else:
            self.dismiss(False)


class DriversApp(App[None]):
    """Textual interactive terminal Hardware Drivers manager (IObit Driver Booster style)."""

    TITLE = "EasyCLI Driver Booster"
    SUB_TITLE = "Scan System • Fix Missing & Outdated Drivers • 1-Click Install"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("r", "refresh_devices", "🔄 Rescan Hardware", show=True),
        Binding("a", "install_all", "⚡ 1-Click Install All", show=True),
        Binding("i", "install_selected", "🚀 Install Selected", show=True),
        Binding("s", "simulate_selected", "🔬 Simulation Preview", show=True),
    ]

    CSS = """
    Screen {
        background: #060b13;
        color: #ecfdf5;
    }

    #summary-banner {
        height: auto;
        min-height: 4;
        background: #09131e;
        border: round #00e5ff;
        margin: 0 1 1 1;
        padding: 1 2;
        content-align: center middle;
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
        background: #0d2822;
        color: #34d399;
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
        min-width: 14;
        margin: 0 1;
    }

    #btn-install-all {
        min-width: 22;
        text-style: bold;
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
            yield Button("⚡ 1-Click Install All", variant="success", id="btn-install-all")
            yield Button("🚀 Install Selected", variant="primary", id="btn-install-sel")
            yield Button("🔬 Simulation Preview", variant="warning", id="btn-simulate")
            yield Button("🔄 Rescan System", variant="default", id="btn-rescan")
            yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#drivers-table", DataTable)
        table.add_column("Category", width=22)
        table.add_column("Hardware Device", width=38)
        table.add_column("Current Driver", width=22)
        table.add_column("Recommended Driver", width=24)
        table.add_column("Driver Booster Status", width=24)

        self.action_refresh_devices()

    def action_refresh_devices(self) -> None:
        """Trigger background hardware scan."""
        banner = self.query_one("#summary-banner", Static)
        banner.update(
            "[bold cyan]🔄 DRIVER BOOSTER SCANNING SYSTEM HARDWARE...[/bold cyan]\n"
            "[dim]Scanning PCI bus, graphics controllers, sound hardware, network adapters, and CPU microcode...[/dim]"
        )
        self.scan_system_drivers()

    @work(thread=True)
    def scan_system_drivers(self) -> None:
        """Scan system hardware in background thread."""
        devs = detect_hardware_drivers()
        self.app.call_from_thread(self._apply_scan_results, devs)

    def _apply_scan_results(self, devs: List[HardwareDeviceDriver]) -> None:
        """Update TUI elements with detected hardware."""
        self.devices = devs
        missing_count = sum(1 for d in self.devices if d.needs_driver and "MISSING" in d.status_badge)
        outdated_count = sum(1 for d in self.devices if d.needs_driver and "MISSING" not in d.status_badge)
        optimal_count = len(self.devices) - missing_count - outdated_count

        banner = self.query_one("#summary-banner", Static)
        if missing_count > 0 or outdated_count > 0:
            badge = f"[bold red]⚠️ DRIVER BOOSTER: ATTENTION REQUIRED[/bold red]  •  [bold white]{len(self.devices)}[/bold white] Devices Scanned\n"
            stats = f"Found [bold red]{missing_count} Missing[/bold red] and [bold yellow]{outdated_count} Outdated/Generic[/bold yellow] driver(s)  |  [bold green]{optimal_count} Optimal[/bold green]\n"
            call_to_action = "Click [bold #00e676]'⚡ 1-Click Install All'[/] to automatically download and configure all drivers!"
            banner.update(badge + stats + call_to_action)
        else:
            badge = f"[bold #00e676]🛡️ DRIVER BOOSTER: ALL HARDWARE OPTIMAL & UP TO DATE[/bold #00e676]  •  [bold white]{len(self.devices)}[/bold white] Devices Scanned\n"
            desc = "[bold green]✅ All detected hardware devices are active with verified drivers and firmware.[/bold green]\nYour system is operating at peak hardware efficiency and stability."
            banner.update(badge + desc)

        table = self.query_one("#drivers-table", DataTable)
        table.clear()

        for idx, dev in enumerate(self.devices):
            cat_str = f"{dev.icon} {dev.category}"
            if "MISSING" in dev.status_badge:
                status_text = f"[bold red]{dev.status_badge}[/]"
            elif dev.needs_driver:
                status_text = f"[bold yellow]{dev.status_badge}[/]"
            else:
                status_text = f"[bold green]{dev.status_badge}[/]"

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

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        try:
            idx = int(key)
            self.selected_device = self.devices[idx]
        except (ValueError, IndexError):
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        try:
            idx = int(key)
            self.selected_device = self.devices[idx]
            self.action_install_selected()
        except (ValueError, IndexError):
            pass

    def action_install_all(self) -> None:
        """1-Click download and install all missing and outdated drivers."""
        pending = [
            d for d in self.devices
            if d.needs_driver and d.recommended_driver and not d.recommended_driver.endswith("(Active)")
        ]
        if not pending:
            self.notify("🎉 All hardware devices are already operating with optimal drivers!", severity="information", timeout=5)
            return

        packages = [d.recommended_driver for d in pending]

        def on_confirmed(proceed: bool) -> None:
            if proceed:
                with self.suspend():
                    success, msg = install_all_drivers(packages)
                if success:
                    self.notify("🎉 Drivers installed successfully! A system reboot is recommended.", severity="information", timeout=7)
                else:
                    self.notify("⚠️ Driver installation cancelled or encountered an error.", severity="warning", timeout=6)
                self.action_refresh_devices()

        self.push_screen(DriverBoosterInstallAllModal(pending, packages), on_confirmed)

    def action_install_selected(self) -> None:
        """Install driver for the highlighted device."""
        if not self.selected_device:
            return
        if (
            not self.selected_device.needs_driver
            or not self.selected_device.recommended_driver
            or self.selected_device.recommended_driver.endswith("(Active)")
        ):
            self.notify(f"ℹ️ {self.selected_device.model} is already using optimal drivers.", severity="information", timeout=4)
            return

        def on_confirmed(proceed: bool) -> None:
            if proceed and self.selected_device:
                with self.suspend():
                    success, msg = install_driver_package(self.selected_device.recommended_driver)
                if success:
                    self.notify(f"🎉 Installed {self.selected_device.recommended_driver}! Reboot recommended.", severity="information", timeout=6)
                else:
                    self.notify("⚠️ Installation cancelled or failed.", severity="warning", timeout=5)
                self.action_refresh_devices()

        self.push_screen(DriverSimulationModal(self.selected_device), on_confirmed)

    def action_simulate_selected(self) -> None:
        """Simulate driver package installation for selected device."""
        if not self.selected_device or not self.selected_device.recommended_driver:
            return

        def on_closed(_: bool) -> None:
            pass

        self.push_screen(DriverSimulationModal(self.selected_device), on_closed)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-install-all":
            self.action_install_all()
        elif event.button.id == "btn-install-sel":
            self.action_install_selected()
        elif event.button.id == "btn-simulate":
            self.action_simulate_selected()
        elif event.button.id == "btn-rescan":
            self.action_refresh_devices()
        elif event.button.id == "btn-close":
            self.exit()
