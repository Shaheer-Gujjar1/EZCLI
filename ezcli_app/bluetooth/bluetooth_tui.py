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
            yield Label("🗑 Remove Bluetooth Device", id="remove-title")
            yield Label(
                f"Remove and unpair [bold yellow]{self.device.icon} {self.device.name}[/bold yellow]?\n\n"
                f"MAC: [dim]{self.device.mac}[/dim]\n"
                "The device will be forgotten and must be paired again to reconnect.",
                id="remove-desc",
            )
            with Horizontal(id="remove-actions"):
                yield Button("🗑 Remove", variant="error", id="btn-confirm-remove")
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
        Binding("x", "remove_device", "🗑 Remove", show=True),
        Binding("t", "toggle_power", "⚡ Power Toggle", show=True),
        Binding("/", "focus_search", "🔍 Filter", show=True),
    ]

    CSS = """
    Screen {
        background: #0b132b;
        color: #e0e1dd;
    }

    #controller-banner {
        height: auto;
        min-height: 3;
        background: #1c2541;
        border: round #3a86ff;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
        overflow: hidden hidden;
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
        self.status_msg: str = ""

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
            yield Button("🗑 Remove", variant="error", id="btn-remove")
            yield Button("🔄 Scan", id="btn-scan")
            yield Button("⚡ Power", id="btn-power")
            yield Button("❌ Close", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#bt-table", DataTable)
        table.add_column("State", width=14)
        table.add_column("📡 Device Name", width=28)
        table.add_column("MAC Address", width=20)
        table.add_column("Type", width=20)
        table.add_column("Signal", width=14)

        self.refresh_all()

    def set_status(self, msg: str) -> None:
        self.status_msg = msg
        self.update_banner()

    def update_banner(self) -> None:
        banner = self.query_one("#controller-banner", Static)
        if not self.controller.available:
            banner.update("[bold red]⚠️ No Bluetooth Adapter Detected or Controller Offline[/bold red]")
            return

        if self.status_msg:
            banner.update(self.status_msg)
            return

        power_badge = "[bold green]ON ⚡[/bold green]" if self.controller.powered else "[bold red]OFF[/bold red]"
        disc_badge = "[bold yellow]Active 🔍[/bold yellow]" if self.controller.discovering else "[dim]Idle[/dim]"
        banner.update(
            f"📡 Controller: [bold cyan]{self.controller.name}[/bold cyan] ({self.controller.mac})  |  "
            f"Power: {power_badge}  |  "
            f"Scan: {disc_badge}"
        )

    def refresh_all(self) -> None:
        self.controller = self.manager.get_controller()
        self.devices = self.manager.list_devices()
        self.update_banner()
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

    def get_current_selected_device(self) -> Optional[BluetoothDevice]:
        try:
            table = self.query_one("#bt-table", DataTable)
            if 0 <= table.cursor_row < len(self.filtered_devices):
                return self.filtered_devices[table.cursor_row]
        except Exception:
            pass
        if self.selected_device:
            return self.selected_device
        if self.filtered_devices:
            return self.filtered_devices[0]
        return None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            row_idx = event.cursor_row
            if 0 <= row_idx < len(self.filtered_devices):
                self.selected_device = self.filtered_devices[row_idx]
        except Exception:
            pass

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        try:
            row_idx = event.coordinate.row
            if 0 <= row_idx < len(self.filtered_devices):
                self.selected_device = self.filtered_devices[row_idx]
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            row_idx = event.cursor_row
            if 0 <= row_idx < len(self.filtered_devices):
                self.selected_device = self.filtered_devices[row_idx]
                if self.selected_device.connected:
                    self.action_disconnect_device()
                else:
                    self.action_connect_device()
        except Exception:
            pass

    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    @work(thread=True)
    def action_refresh_devices(self) -> None:
        self.call_from_thread(self.set_status, "[bold yellow]🔍 Scanning for nearby Bluetooth devices... (3s)[/bold yellow]")
        self.manager.scan_devices(timeout=3)
        self.call_from_thread(self.set_status, "")
        self.call_from_thread(self.refresh_all)

    @work(thread=True)
    def action_connect_device(self) -> None:
        dev = self.get_current_selected_device()
        if not dev:
            return
        self.call_from_thread(self.set_status, f"[bold cyan]⏳ Connecting to {dev.name} ({dev.mac})...[/bold cyan]")
        ok, msg = self.manager.connect(dev.mac)
        if ok:
            self.call_from_thread(self.set_status, f"[bold green]✓ Connected to {dev.name} successfully![/bold green]")
        else:
            self.call_from_thread(self.set_status, f"[bold red]❌ Connection failed: {msg}[/bold red]")
        self.call_from_thread(self.refresh_all)

    @work(thread=True)
    def action_disconnect_device(self) -> None:
        dev = self.get_current_selected_device()
        if not dev:
            return
        self.call_from_thread(self.set_status, f"[bold yellow]⏳ Disconnecting {dev.name}...[/bold yellow]")
        self.manager.disconnect(dev.mac)
        self.call_from_thread(self.set_status, f"[bold green]✓ Disconnected {dev.name}.[/bold green]")
        self.call_from_thread(self.refresh_all)

    @work(thread=True)
    def action_pair_device(self) -> None:
        dev = self.get_current_selected_device()
        if not dev:
            return
        self.call_from_thread(self.set_status, f"[bold cyan]⏳ Pairing with {dev.name}... (confirm prompt on device if required)[/bold cyan]")
        ok, msg = self.manager.pair(dev.mac)
        if ok:
            self.call_from_thread(self.set_status, f"[bold green]✓ Paired with {dev.name} successfully![/bold green]")
        else:
            self.call_from_thread(self.set_status, f"[bold red]❌ Pairing failed: {msg}[/bold red]")
        self.call_from_thread(self.refresh_all)

    def action_remove_device(self) -> None:
        dev = self.get_current_selected_device()
        if not dev:
            return

        def on_confirmed(confirmed: bool) -> None:
            if confirmed:
                self.do_remove(dev)

        self.push_screen(ConfirmRemoveModal(dev), on_confirmed)

    @work(thread=True)
    def do_remove(self, dev: BluetoothDevice) -> None:
        self.call_from_thread(self.set_status, f"[bold yellow]⏳ Removing {dev.name}...[/bold yellow]")
        self.manager.remove(dev.mac)
        self.selected_device = None
        self.call_from_thread(self.set_status, f"[bold green]✓ Removed {dev.name}.[/bold green]")
        self.call_from_thread(self.refresh_all)

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
