"""Visually distinct Textual TUI application for Shell Command Shortcuts.

CRITICAL REQUIREMENT: User-facing text must NEVER use the word 'aliases'.
All concepts are strictly presented as 'Shortcuts' or 'Command Shortcuts'.
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

from .shortcuts_engine import (
    ShortcutItem,
    add_or_update_shortcut,
    delete_shortcut,
    get_shell_rc_path,
    parse_shortcuts,
)


class AddEditShortcutModal(ModalScreen[Optional[dict]]):
    """Modal dialog for creating or editing a command shortcut."""

    DEFAULT_CSS = """
    AddEditShortcutModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #shortcut-dialog {
        width: 65;
        height: auto;
        border: round #22c55e;
        background: #052e16;
        padding: 1 2;
    }
    #dialog-title {
        text-style: bold;
        color: #4ade80;
        text-align: center;
        margin-bottom: 1;
    }
    .field-lbl {
        color: #bbf7d0;
        margin-top: 1;
    }
    #inp-name, #inp-cmd {
        border: solid #16a34a;
        margin-bottom: 1;
    }
    #dialog-actions {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #dialog-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, existing: Optional[ShortcutItem] = None) -> None:
        super().__init__()
        self.existing = existing

    def compose(self) -> ComposeResult:
        with Vertical(id="shortcut-dialog"):
            title = "✏️ Edit Command Shortcut" if self.existing else "➕ Add New Command Shortcut"
            yield Label(title, id="dialog-title")
            yield Label("Shortcut Trigger Name (e.g. 'c' or 'update-all'):", classes="field-lbl")
            yield Input(
                value=self.existing.name if self.existing else "",
                placeholder="Short command name...",
                id="inp-name",
            )
            yield Label("Full Command To Execute (e.g. 'clear' or 'ez update && ez upgrade'):", classes="field-lbl")
            yield Input(
                value=self.existing.command if self.existing else "",
                placeholder="Full terminal command...",
                id="inp-cmd",
            )
            with Horizontal(id="dialog-actions"):
                yield Button("💾 Save Shortcut", variant="success", id="btn-save")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            name = self.query_one("#inp-name", Input).value.strip()
            cmd = self.query_one("#inp-cmd", Input).value.strip()
            if not name or not cmd:
                return
            self.dismiss({"name": name, "command": cmd})
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class DeleteShortcutModal(ModalScreen[bool]):
    """Confirmation modal for removing a command shortcut."""

    DEFAULT_CSS = """
    DeleteShortcutModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #del-box {
        width: 60;
        height: auto;
        border: round red;
        background: #181111;
        padding: 1 2;
    }
    #del-title {
        text-style: bold;
        color: #ef4444;
        text-align: center;
        margin-bottom: 1;
    }
    #del-desc {
        color: white;
        text-align: center;
        margin-bottom: 1;
    }
    #del-actions {
        align: center middle;
        height: auto;
    }
    #del-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, shortcut: ShortcutItem) -> None:
        super().__init__()
        self.shortcut = shortcut

    def compose(self) -> ComposeResult:
        with Vertical(id="del-box"):
            yield Label("🗑️ Remove Command Shortcut", id="del-title")
            yield Label(
                f"Are you sure you want to remove the shortcut '[bold yellow]{self.shortcut.name}[/bold yellow]'?\n\n"
                f"Runs command: [dim]{self.shortcut.command}[/dim]",
                id="del-desc",
            )
            with Horizontal(id="del-actions"):
                yield Button("🗑️ Remove", variant="error", id="btn-confirm-delete")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-delete":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ShortcutsApp(App[None]):
    """Textual interactive terminal Command Shortcuts application."""

    TITLE = "EasyCLI Command Shortcuts Manager"
    SUB_TITLE = "Create & Manage Custom Quick Terminal Commands"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("a", "add_shortcut", "➕ Add", show=True),
        Binding("e", "edit_shortcut", "✏️ Edit", show=True),
        Binding("d", "delete_shortcut", "🗑️ Delete", show=True),
        Binding("r", "refresh_shortcuts", "🔄 Refresh", show=True),
    ]

    CSS = """
    Screen {
        background: #022c22;
        color: #f0fdf4;
    }

    #info-banner {
        height: 3;
        background: #064e3b;
        border: round #22c55e;
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
        border: round #16a34a;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #065f46;
        color: #86efac;
    }

    DataTable > .datatable--cursor {
        background: #15803d;
        color: white;
        text-style: bold;
    }

    #tip-banner {
        height: 2;
        background: #0f172a;
        margin: 0 1;
        color: #94a3b8;
        content-align: center middle;
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
        self.rc_path = get_shell_rc_path()
        self.shortcuts: List[ShortcutItem] = []
        self.selected_item: Optional[ShortcutItem] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="info-banner")
        with Vertical(id="table-container"):
            yield DataTable(id="shortcuts-table", cursor_type="row")
        yield Static(
            "💡 Run 'source ~/.bashrc' or restart your terminal to activate new shortcuts in current sessions.",
            id="tip-banner",
        )
        with Horizontal(id="action-bar"):
            yield Button("➕ Add Shortcut", variant="success", id="btn-add")
            yield Button("✏️ Edit Shortcut", variant="primary", id="btn-edit")
            yield Button("🗑️ Delete", variant="error", id="btn-delete")
            yield Button("🔄 Refresh", variant="default", id="btn-refresh")
            yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#shortcuts-table", DataTable)
        table.add_column("Shortcut Trigger", width=22)
        table.add_column("Runs Terminal Command", width=45)
        table.add_column("Source", width=22)

        self.refresh_shortcuts_list()

    def refresh_shortcuts_list(self) -> None:
        self.shortcuts = parse_shortcuts(self.rc_path)
        banner = self.query_one("#info-banner", Static)
        short_rc = os.path.basename(self.rc_path)
        backup_name = f"{short_rc}.ezcli.bak"

        banner.update(
            f"Config File: [bold cyan]~/{short_rc}[/bold cyan]  |  "
            f"Backup: [bold green]~/{backup_name} ✅[/bold green]  |  "
            f"Total Active Shortcuts: [bold yellow]{len(self.shortcuts)}[/bold yellow]"
        )

        table = self.query_one("#shortcuts-table", DataTable)
        table.clear()

        for s in self.shortcuts:
            table.add_row(
                f"[bold green]{s.name}[/bold green]",
                f"[cyan]{s.command}[/cyan]",
                s.source,
                key=s.name,
            )

        if self.shortcuts:
            self.selected_item = self.shortcuts[0]

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        self.selected_item = next((s for s in self.shortcuts if s.name == key), None)

    def action_add_shortcut(self) -> None:
        def on_added(data: Optional[dict]) -> None:
            if data:
                add_or_update_shortcut(self.rc_path, data["name"], data["command"])
                self.refresh_shortcuts_list()

        self.push_screen(AddEditShortcutModal(), on_added)

    def action_edit_shortcut(self) -> None:
        if not self.selected_item:
            if self.shortcuts:
                self.selected_item = self.shortcuts[0]
            else:
                return

        def on_edited(data: Optional[dict]) -> None:
            if data:
                add_or_update_shortcut(self.rc_path, data["name"], data["command"])
                self.refresh_shortcuts_list()

        self.push_screen(AddEditShortcutModal(existing=self.selected_item), on_edited)

    def action_delete_shortcut(self) -> None:
        if not self.selected_item:
            if self.shortcuts:
                self.selected_item = self.shortcuts[0]
            else:
                return

        def on_confirmed(confirmed: bool) -> None:
            if confirmed and self.selected_item:
                delete_shortcut(self.rc_path, self.selected_item.name)
                self.selected_item = None
                self.refresh_shortcuts_list()

        self.push_screen(DeleteShortcutModal(self.selected_item), on_confirmed)

    def action_refresh_shortcuts(self) -> None:
        self.refresh_shortcuts_list()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add":
            self.action_add_shortcut()
        elif event.button.id == "btn-edit":
            self.action_edit_shortcut()
        elif event.button.id == "btn-delete":
            self.action_delete_shortcut()
        elif event.button.id == "btn-refresh":
            self.action_refresh_shortcuts()
        elif event.button.id == "btn-close":
            self.exit()
