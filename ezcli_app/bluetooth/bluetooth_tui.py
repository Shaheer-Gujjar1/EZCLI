"""Visually distinct Textual TUI application for Bluetooth device management.

Modeled on the ez connect-wifi interface:
- Visual list of nearby and paired Bluetooth devices with signal strength bars and category icons
- Controller power and discovery status banner
- Interactive search/filter input
- Actions: Scan/Refresh, Connect, Disconnect, Pair, Remove, Power Toggle
"""

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
    Input,
    Label,
    Static,
)

from .bluetooth_engine import BluetoothController, BluetoothDevice, BluetoothManager


class ConfirmRemoveModal(ModalScreen[bool]):
    """Confirmation modal before unpairing or removing a Bluetooth device."""

    DEFAULT_CSS = """
    ConfirmRemoveModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #remove-box {
        width: 60;
        height: auto;
        border: round red;
        background: #111827;
        padding: 1 2;
    }
    #remove-title {
        text-style: bold;
        color: #ef4444;
        text-align: center;
        margin-bottom: 1;
    }
    #remove-desc {
        color: white;
        text-align: center;
        margin-bottom: 1;
    }
    #remove-actions {
        align: center middle;
        height: auto;
    }
    #remove-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, device: BluetoothDevice) -> None:
        super().__init__()
        self.device = device

    def compose(self) -> ComposeResult:
        with Vertical(id="remove-box"):
            yield Label("🗑️ Remove Bluetooth Device", id="remove-title")
            yield Label(
                f"Remove and unpair [bold yellow]{self.device.icon} {self.device.name}[/bold yellow]?\n\n"
                f"MAC: [dim]{self.device.mac}[/dim]\n"
                "The device will be forgotten and must be paired again to reconnect.",
                id="remove-desc",
            )
            with Horizontal(id="remove-actions"):
                yield Button("🗑️ Remove", variant="error", id="btn-confirm-remove")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-remove":
            self.dismiss(True)
        else:
            self.dismiss(False)


class BluetoothApp(App[None]):
    """Textual interactive terminal Bluetooth application."""

    TITLE = "EasyCLI Bluetooth Manager"
    SUB_TITLE = "Visual Wireless Device Scanner & Manager with Mouse Support"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("r", "refresh_devices", "🔄 Scan/Refresh", show=True),
        Binding("c", "connect_device", "🔗 Connect", show=True),
        Binding("p", "pair_device", "🔒 Pair", show=True),
        Binding("d", "disconnect_device", "🚫 Disconnect", show=True),
        Binding("x", "remove_device", "🗑️ Remove", show=True),
        Binding("t", "toggle_power", "⚡ Power Toggle", show=True),
        Binding("/", "focus_search", "🔍 Filter", show=True),
    ]

    CSS = """
    Screen {
        background: #0b132b;
        color: #e0e1dd;
    }

    #controller-banner {
        height: 3;
        background: #1c2541;
        border: round #3a86ff;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
    }

    #search-box {
        margin: 0 1 1 1;
        border: round #48cae4;
        background: #1c2541;
    }

    #table-container {
        height: 1fr;
        margin: 0 1;
    }

    DataTable {
        height: 100%;
        border: round #3a86ff;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #1e3a8a;
        color: #93c5fd;
    }

    DataTable > .datatable--cursor {
        background: #2563eb;
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

    def __init__(self, manager: Optional[BluetoothManager] = None) -> None:
        super().__init__()
        self.manager = manager or BluetoothManager()
        self.controller = BluetoothController(available=False)
        self.devices: List[BluetoothDevice] = []
        self.filtered_devices: List[BluetoothDevice] = []
        self.selected_device: Optional[BluetoothDevice] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="controller-banner")
        yield Input(placeholder="🔍 Filter Bluetooth devices (press '/' to focus)...", id="search-box")
        with Vertical(id="table-container"):
            yield DataTable(id="bt-table", cursor_type="row")
        with Horizontal(id="action-bar"):
            yield Button("🔗 Connect", variant="primary", id="btn-connect")
            yield Button("🔒 Pair", variant="success", id="btn-pair")
            yield Button("🚫 Disconnect", variant="warning", id="btn-disconnect")
            yield Button("🗑️ Remove", variant="error", id="btn-remove")
            yield Button("🔄 Scan", variant="default", id="btn-scan")
            yield Button("⚡ Power", variant="default", id="btn-power")
            yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#bt-table", DataTable)
        table.add_column("State", width=14)
        table.add_column("📡 Device Name", width=28)
        table.add_column("MAC Address", width=20)
        table.add_column("Type", width=20)
        table.add_column("Signal", width=14)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.controller = self.manager.get_controller()
        banner = self.query_one("#controller-banner", Static)

        if not self.controller.available:
            banner.update("[bold red]⚠️ No Bluetooth Adapter Detected or Controller Offline[/bold red]")
        else:
            power_badge = "[bold green]ON ⚡[/bold green]" if self.controller.powered else "[bold red]OFF[/bold red]"
            disc_badge = "Active" if self.controller.discovering else "Idle"
            banner.update(
                f"📡 Controller: [bold cyan]{self.controller.name}[/bold cyan] ({self.controller.mac})  |  "
                f"Power: {power_badge}  |  "
                f"Scan: [bold]{disc_badge}[/bold]"
            )

        self.devices = self.manager.list_devices()
        self.apply_filter()

    def apply_filter(self) -> None:
        search_query = self.query_one("#search-box", Input).value.strip().lower()
        if not search_query:
            self.filtered_devices = list(self.devices)
        else:
            self.filtered_devices = [
                d for d in self.devices
                if search_query in d.name.lower() or search_query in d.mac.lower() or search_query in d.device_type.lower()
            ]

        table = self.query_one("#bt-table", DataTable)
        table.clear()

        for dev in self.filtered_devices:
            if dev.connected:
                state_badge = "[bold green]🔗 Connected[/bold green]"
            elif dev.paired:
                state_badge = "[bold cyan]🔒 Paired[/bold cyan]"
            else:
                state_badge = "[dim]📡 Available[/dim]"

            name_col = f"{dev.icon} {dev.name}"
            sig_col = f"[green]{dev.bars}[/green]"

            table.add_row(
                state_badge,
                name_col,
                dev.mac,
                dev.device_type,
                sig_col,
                key=dev.mac,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-box":
            self.apply_filter()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        self.selected_device = next((d for d in self.devices if d.mac == key), None)

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_refresh_devices(self) -> None:
        # Trigger short background scan
        self.manager.scan_devices(timeout=3)
        self.refresh_all()

    def action_connect_device(self) -> None:
        if not self.selected_device:
            if self.filtered_devices:
                self.selected_device = self.filtered_devices[0]
            else:
                return
        self.manager.connect(self.selected_device.mac)
        self.refresh_all()

    def action_disconnect_device(self) -> None:
        if not self.selected_device:
            if self.filtered_devices:
                self.selected_device = self.filtered_devices[0]
            else:
                return
        self.manager.disconnect(self.selected_device.mac)
        self.refresh_all()

    def action_pair_device(self) -> None:
        if not self.selected_device:
            if self.filtered_devices:
                self.selected_device = self.filtered_devices[0]
            else:
                return
        self.manager.pair(self.selected_device.mac)
        self.refresh_all()

    def action_remove_device(self) -> None:
        if not self.selected_device:
            if self.filtered_devices:
                self.selected_device = self.filtered_devices[0]
            else:
                return

        def on_confirmed(confirmed: bool) -> None:
            if confirmed and self.selected_device:
                self.manager.remove(self.selected_device.mac)
                self.selected_device = None
                self.refresh_all()

        self.push_screen(ConfirmRemoveModal(self.selected_device), on_confirmed)

    def action_toggle_power(self) -> None:
        new_power = not self.controller.powered
        self.manager.toggle_power(new_power)
        self.refresh_all()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-connect":
            self.action_connect_device()
        elif event.button.id == "btn-pair":
            self.action_pair_device()
        elif event.button.id == "btn-disconnect":
            self.action_disconnect_device()
        elif event.button.id == "btn-remove":
            self.action_remove_device()
        elif event.button.id == "btn-scan":
            self.action_refresh_devices()
        elif event.button.id == "btn-power":
            self.action_toggle_power()
        elif event.button.id == "btn-close":
            self.exit()
