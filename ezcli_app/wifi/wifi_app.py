"""Modern in-terminal Wi-Fi Manager application with full mouse support for EasyCLI.

Provides:
- Visual list of nearby Wi-Fi networks with signal strength bars and security icons
- Active connection status banner with IP address
- Mouse support: click to select, double click to connect, clickable toolbar buttons
- Password entry modal with 'Show/Hide Password' toggle (👁️ / 🙈)
- Connect, Cancel, Refresh, Disconnect actions
"""

import glob
import os
import sys
from typing import List, Optional

# Ensure venv site-packages is accessible if textual is installed in user venv
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

from .wifi_engine import WifiManager, WifiNetwork


# ==============================================================================
# Password Entry Modal
# ==============================================================================

class WifiPasswordModal(ModalScreen[Optional[str]]):
    """Modal dialog for entering Wi-Fi network password with show/hide toggle."""

    DEFAULT_CSS = """
    WifiPasswordModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #pwd-dialog {
        width: 65;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    #pwd-title {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }
    #pwd-details {
        color: white;
        text-align: center;
        margin-bottom: 1;
    }
    #pwd-input {
        margin-bottom: 1;
        border: solid cyan;
    }
    #pwd-toggle-container {
        align: center middle;
        margin-bottom: 1;
    }
    #pwd-buttons {
        align: center middle;
        height: auto;
    }
    #pwd-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, network: WifiNetwork) -> None:
        super().__init__()
        self.network = network

    def compose(self) -> ComposeResult:
        with Vertical(id="pwd-dialog"):
            yield Label(f"🔒 Connect to '{self.network.ssid}'", id="pwd-title")
            yield Label(
                f"Security: [bold yellow]{self.network.security_display}[/bold yellow]  |  "
                f"Signal: [bold green]{self.network.bars}[/bold green]",
                id="pwd-details",
            )
            yield Input(
                placeholder="Enter Wi-Fi password...",
                password=True,
                id="pwd-input",
            )
            with Horizontal(id="pwd-toggle-container"):
                yield Button("👁️ Show Password", id="btn-toggle-pwd", variant="default")
            with Horizontal(id="pwd-buttons"):
                yield Button("🔗 Connect", variant="primary", id="btn-modal-connect")
                yield Button("❌ Cancel", variant="default", id="btn-modal-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-pwd":
            pwd_input = self.query_one("#pwd-input", Input)
            if pwd_input.password:
                pwd_input.password = False
                event.button.label = "🙈 Hide Password"
            else:
                pwd_input.password = True
                event.button.label = "👁️ Show Password"
        elif event.button.id == "btn-modal-connect":
            self.submit_password()
        elif event.button.id == "btn-modal-cancel":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "pwd-input":
            self.submit_password()

    def submit_password(self) -> None:
        pwd_input = self.query_one("#pwd-input", Input)
        password = pwd_input.value.strip()
        self.dismiss(password)


# ==============================================================================
# Main Wi-Fi Manager App
# ==============================================================================

class WifiApp(App[None]):
    """Textual interactive terminal Wi-Fi application."""

    TITLE = "EasyCLI Wi-Fi Manager"
    SUB_TITLE = "Visual Wi-Fi Scanner & Connector with Mouse Support"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("r", "refresh_networks", "🔄 Refresh", show=True),
        Binding("c", "connect_selected", "🔗 Connect", show=True),
        Binding("d", "disconnect_active", "🚫 Disconnect", show=True),
        Binding("/", "focus_search", "🔍 Search", show=True),
        Binding("escape", "cancel_action", "Back", show=False),
    ]

    CSS = """
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }

    #status-banner {
        height: 3;
        background: #161b22;
        border: round cyan;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
        text-style: bold;
    }

    #search-box {
        margin: 0 1 1 1;
        border: round #30363d;
    }

    #table-container {
        height: 1fr;
        margin: 0 1;
    }

    DataTable {
        height: 100%;
        border: round cyan;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #21262d;
        color: #58a6ff;
    }

    DataTable > .datatable--cursor {
        background: #1f6feb;
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

    def __init__(self, manager: Optional[WifiManager] = None) -> None:
        super().__init__()
        self.manager = manager or WifiManager()
        self.networks: List[WifiNetwork] = []
        self.filtered_networks: List[WifiNetwork] = []
        self.selected_network: Optional[WifiNetwork] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="status-banner")
        yield Input(placeholder="🔍 Search Wi-Fi networks (press '/' to filter)...", id="search-box")
        with Vertical(id="table-container"):
            yield DataTable(id="wifi-table", cursor_type="row")
        with Horizontal(id="action-bar"):
            yield Button("🔗 Connect", variant="primary", id="btn-connect")
            yield Button("🔄 Refresh", variant="default", id="btn-refresh")
            yield Button("🚫 Disconnect", variant="warning", id="btn-disconnect")
            yield Button("❌ Close", variant="error", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize table columns and load networks on startup."""
        table = self.query_one("#wifi-table", DataTable)
        table.add_column("State", width=14)
        table.add_column("📶 Network Name (SSID)", width=28)
        table.add_column("📊 Signal", width=16)
        table.add_column("🔒 Security", width=24)
        table.add_column("📡 Band & Channel", width=18)
        table.add_column("⚡ Rate", width=12)

        self.refresh_all()

    def update_status_banner(self) -> None:
        """Update top banner with active connection information."""
        banner = self.query_one("#status-banner", Static)
        active = self.manager.get_active_wifi()

        if active and active.get("ssid"):
            ssid = active["ssid"]
            ip = active.get("ip", "Configured")
            iface = active.get("interface", "wlan0")
            banner.update(
                f"[bold green]🟢 Connected to:[/bold green] [bold white]{ssid}[/bold white] "
                f"[dim]({iface})[/dim]  |  [bold cyan]IP:[/bold cyan] [bold white]{ip}[/bold white]"
            )
        else:
            banner.update(
                "[bold yellow]🔴 Wi-Fi Disconnected[/bold yellow] [dim]─ Select a network from the list below to connect[/dim]"
            )

    def refresh_all(self, rescan: bool = True) -> None:
        """Reload networks from backend and refresh display."""
        self.update_status_banner()
        self.networks = self.manager.scan_networks(rescan=rescan)
        self.apply_filter()

    def apply_filter(self) -> None:
        """Filter networks based on search input value."""
        search_input = self.query_one("#search-box", Input)
        query = search_input.value.strip().lower()

        if query:
            self.filtered_networks = [
                n for n in self.networks
                if query in n.ssid.lower() or query in n.security.lower()
            ]
        else:
            self.filtered_networks = list(self.networks)

        table = self.query_one("#wifi-table", DataTable)
        table.clear()

        for idx, net in enumerate(self.filtered_networks):
            state_disp = "🟢 [bold green]Connected[/bold green]" if net.in_use else " "
            ssid_disp = f"[bold white]{net.ssid}[/bold white]" if net.in_use else net.ssid

            table.add_row(
                state_disp,
                ssid_disp,
                net.bars,
                net.security_display,
                net.freq,
                net.rate or "—",
                key=str(idx),
            )

        # Update selection
        if self.filtered_networks:
            self.selected_network = self.filtered_networks[0]
        else:
            self.selected_network = None

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-box":
            self.apply_filter()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle mouse click selection of row."""
        try:
            row_idx = event.cursor_row
            if 0 <= row_idx < len(self.filtered_networks):
                self.selected_network = self.filtered_networks[row_idx]
                # Double click triggers connection
                self.action_connect_selected()
        except Exception:
            pass

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle single-click cursor row change."""
        try:
            row_idx = event.coordinate.row
            if 0 <= row_idx < len(self.filtered_networks):
                self.selected_network = self.filtered_networks[row_idx]
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks in the action toolbar."""
        btn_id = event.button.id
        if btn_id == "btn-connect":
            self.action_connect_selected()
        elif btn_id == "btn-refresh":
            self.action_refresh_networks()
        elif btn_id == "btn-disconnect":
            self.action_disconnect_active()
        elif btn_id == "btn-close":
            self.exit()

    # Keyboard Action Handlers
    def action_focus_search(self) -> None:
        self.query_one("#search-box", Input).focus()

    def action_refresh_networks(self) -> None:
        self.notify("Scanning nearby Wi-Fi networks...", title="🔄 Scanning", timeout=3.0)
        self.refresh_all(rescan=True)

    def action_cancel_action(self) -> None:
        search_input = self.query_one("#search-box", Input)
        if search_input.has_focus and search_input.value:
            search_input.value = ""
            self.query_one("#wifi-table", DataTable).focus()
        else:
            self.exit()

    def action_connect_selected(self) -> None:
        """Initiate connection to the currently selected network."""
        table = self.query_one("#wifi-table", DataTable)
        if table.cursor_row is not None and 0 <= table.cursor_row < len(self.filtered_networks):
            self.selected_network = self.filtered_networks[table.cursor_row]

        if not self.selected_network:
            self.notify("Please select a Wi-Fi network to connect.", severity="warning")
            return

        net = self.selected_network
        if net.in_use:
            self.notify(f"Already connected to '{net.ssid}'.", severity="information")
            return

        if not net.is_secured:
            # Open network: connect directly without password
            self.do_connect(net, password=None)
        else:
            # Secured network: prompt for password with show/hide toggle
            self.push_screen(WifiPasswordModal(net), self.on_password_modal_closed)

    def on_password_modal_closed(self, password: Optional[str]) -> None:
        if password is None:
            return  # User clicked cancel

        if not self.selected_network:
            return

        self.do_connect(self.selected_network, password=password)

    def do_connect(self, network: WifiNetwork, password: Optional[str]) -> None:
        """Perform network connection and provide immediate visual feedback."""
        self.notify(f"Connecting to '{network.ssid}'...", title="📶 Connecting", timeout=5.0)

        # Connect synchronously
        ok, msg = self.manager.connect_network(
            ssid=network.ssid,
            password=password,
            bssid=network.bssid if network.ssid == "[Hidden Network]" else None,
        )

        if ok:
            self.notify(f"Connected to '{network.ssid}'!", title="🎉 Connected", severity="information", timeout=5.0)
        else:
            self.notify(msg, title="❌ Connection Failed", severity="error", timeout=7.0)

        self.refresh_all(rescan=False)

    def action_disconnect_active(self) -> None:
        """Disconnect the currently active Wi-Fi connection."""
        active = self.manager.get_active_wifi()
        if not active:
            self.notify("No active Wi-Fi connection to disconnect.", severity="warning")
            return

        ok, msg = self.manager.disconnect_wifi()
        if ok:
            self.notify(msg, title="🚫 Disconnected", severity="information", timeout=4.0)
        else:
            self.notify(msg, title="❌ Disconnect Failed", severity="error", timeout=6.0)

        self.refresh_all(rescan=False)


def run_wifi_app() -> None:
    """Launch the interactive Textual Wi-Fi Manager."""
    app = WifiApp()
    app.run()
