"""Interactive Textual TUI for managing startup apps and boot services."""

from typing import List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, TabbedContent, TabPane

from .startup_engine import (
    StartupItem,
    scan_boot_services,
    scan_login_apps,
    toggle_boot_service,
    toggle_login_app,
)


class CriticalConfirmModal(ModalScreen[bool]):
    """Modal requiring typed confirmation before disabling a critical service."""

    DEFAULT_CSS = """
    CriticalConfirmModal {
        align: center middle;
    }
    #crit-dialog {
        width: 60;
        height: auto;
        border: thick red;
        background: $surface;
        padding: 1 2;
    }
    #crit-title {
        text-align: center;
        text-style: bold;
        color: red;
        margin-bottom: 1;
    }
    #crit-input {
        margin-top: 1;
        margin-bottom: 1;
        border: solid red;
    }
    #crit-buttons {
        align: center middle;
        height: auto;
    }
    #crit-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, item_name: str) -> None:
        super().__init__()
        self.item_name = item_name

    def compose(self) -> ComposeResult:
        with Vertical(id="crit-dialog"):
            yield Label(f"⚠️ LOCKED CRITICAL SERVICE: {self.item_name}", id="crit-title")
            yield Label(
                f"Disabling '[bold]{self.item_name}[/bold]' may cause network, login, or system failure!\n\n"
                "To proceed, type [bold red]DISABLE[/bold red] below:"
            )
            yield Input(placeholder="Type DISABLE to confirm...", id="crit-input")
            with Horizontal(id="crit-buttons"):
                yield Button("❌ Cancel", variant="default", id="btn-crit-cancel")
                yield Button("⚠️ Disable Anyway", variant="error", id="btn-crit-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-crit-confirm":
            val = self.query_one("#crit-input", Input).value.strip()
            if val == "DISABLE":
                self.dismiss(True)
            else:
                self.notify("Type DISABLE exactly to proceed.", severity="warning")
        elif event.button.id == "btn-crit-cancel":
            self.dismiss(False)


class StartupAppsApp(App[None]):
    """Interactive TUI for managing Login Apps & Boot Services."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #preview-card {
        height: 4;
        border: solid cyan;
        background: $surface;
        padding: 0 1;
        margin: 1 1;
    }
    #preview-text {
        color: white;
    }
    #preview-subtext {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_item", "Toggle", priority=True),
        Binding("enter", "toggle_item", "Toggle", priority=True),
        Binding("r", "refresh_items", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.login_items: List[StartupItem] = []
        self.service_items: List[StartupItem] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("🚀 Login Apps", id="pane-login"):
                yield DataTable(id="table-login", cursor_type="row")
            with TabPane("⚙️ Boot Services", id="pane-services"):
                yield DataTable(id="table-services", cursor_type="row")

        with Vertical(id="preview-card"):
            yield Label("Select an item to view details and toggle status.", id="preview-text")
            yield Label("Press [Space] or [Enter] to toggle · [Tab] to switch views", id="preview-subtext")

        yield Footer()

    def on_mount(self) -> None:
        self.title = "🚀 EasyCLI Startup & Boot Manager"
        self.sub_title = "Manage Login Applications & Systemd Boot Services"

        # Setup Login Table
        t_login = self.query_one("#table-login", DataTable)
        t_login.add_column("Status", width=12)
        t_login.add_column("Application Name", width=28)
        t_login.add_column("Command / File", width=40)

        # Setup Services Table
        t_services = self.query_one("#table-services", DataTable)
        t_services.add_column("Status", width=12)
        t_services.add_column("Service Unit", width=28)
        t_services.add_column("Type / Protection", width=24)

        self.action_refresh_items()

    def action_refresh_items(self) -> None:
        self.login_items = scan_login_apps()
        self.service_items = scan_boot_services()

        # Populate login table
        t_login = self.query_one("#table-login", DataTable)
        t_login.clear()
        for idx, item in enumerate(self.login_items):
            status_badge = "[bold green]✔ Enabled[/bold green]" if item.state == "Enabled" else "[dim]✖ Disabled[/dim]"
            cmd_display = item.exec_cmd or item.file_path
            t_login.add_row(status_badge, item.name, cmd_display, key=str(idx))

        # Populate services table
        t_services = self.query_one("#table-services", DataTable)
        t_services.clear()
        for idx, item in enumerate(self.service_items):
            status_badge = "[bold green]✔ Enabled[/bold green]" if item.state == "Enabled" else "[dim]✖ Disabled[/dim]"
            prot_badge = "[bold red]🔒 Critical[/bold red]" if item.is_critical else "[dim]Standard[/dim]"
            t_services.add_row(status_badge, item.name, prot_badge, key=str(idx))

        self.update_preview()

    def get_current_selected(self) -> Optional[StartupItem]:
        tabs = self.query_one("#tabs", TabbedContent)
        active = tabs.active
        if active == "pane-login":
            t = self.query_one("#table-login", DataTable)
            if t.cursor_row is not None and 0 <= t.cursor_row < len(self.login_items):
                return self.login_items[t.cursor_row]
        else:
            t = self.query_one("#table-services", DataTable)
            if t.cursor_row is not None and 0 <= t.cursor_row < len(self.service_items):
                return self.service_items[t.cursor_row]
        return None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.update_preview()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self.update_preview()

    def update_preview(self) -> None:
        item = self.get_current_selected()
        lbl_text = self.query_one("#preview-text", Label)
        lbl_sub = self.query_one("#preview-subtext", Label)

        if not item:
            lbl_text.update("No item selected.")
            lbl_sub.update("")
            return

        if item.item_type == "login":
            next_effect = "will NOT start automatically at login" if item.state == "Enabled" else "will start automatically at login"
            lbl_text.update(f"[bold cyan]{item.name}[/bold cyan] ({item.state}) — [yellow]Next boot:[/yellow] This app {next_effect}.")
            lbl_sub.update(f"Path: {item.file_path}")
        else:
            next_effect = "will NOT start automatically at boot" if item.state == "Enabled" else "will start automatically at boot"
            crit_warning = " [bold red]⚠️ CRITICAL SERVICE[/bold red]" if item.is_critical else ""
            lbl_text.update(f"[bold cyan]{item.name}[/bold cyan] ({item.state}){crit_warning} — [yellow]Next boot:[/yellow] Service {next_effect}.")
            lbl_sub.update(f"Unit: {item.id} · Press [Space] to toggle")

    def action_toggle_item(self) -> None:
        item = self.get_current_selected()
        if not item:
            return

        if item.item_type == "login":
            ok, msg = toggle_login_app(item)
            if ok:
                self.notify(msg, severity="information")
                self.action_refresh_items()
            else:
                self.notify(msg, severity="error")
        else:
            # Boot service
            if item.state == "Enabled" and item.is_critical:
                def on_confirm(confirmed: bool) -> None:
                    if confirmed:
                        self.do_service_toggle(item)
                    else:
                        self.notify("Action cancelled.", severity="warning")

                self.push_screen(CriticalConfirmModal(item.name), on_confirm)
            else:
                self.do_service_toggle(item)

    def do_service_toggle(self, item: StartupItem) -> None:
        ok, msg = toggle_boot_service(item)
        if ok:
            self.notify(msg, severity="information")
            self.action_refresh_items()
        else:
            self.notify(msg, severity="error")
