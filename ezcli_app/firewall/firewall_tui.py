"""Visually distinct Textual TUI application for EasyCLI UFW Firewall Management.

Features:
- Live status card with Shield icon, active/inactive state, and default incoming/outgoing policies
- Rules DataTable with color-coded ALLOW / DENY badges and port details
- One-key toggle with SSH lockout guard modal if port 22 is not allowed
- Add Rule modal (allow/deny, port/service, protocol)
- Delete Rule modal with confirmation
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
from textual.containers import Container, Horizontal, Vertical  # type: ignore
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

from .firewall_engine import (
    FirewallRule,
    FirewallStatus,
    add_firewall_rule,
    delete_firewall_rule,
    get_firewall_status,
    toggle_firewall,
)


class SshWarningModal(ModalScreen[bool]):
    """Modal displayed when attempting to enable the firewall without an SSH rule."""

    DEFAULT_CSS = """
    SshWarningModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #warning-box {
        width: 70;
        height: auto;
        border: thick red;
        background: #1c0a0a;
        padding: 1 2;
    }
    #warning-title {
        text-style: bold;
        color: #ef4444;
        text-align: center;
        margin-bottom: 1;
    }
    #warning-text {
        color: #fca5a5;
        margin-bottom: 1;
        text-align: center;
    }
    #warning-actions {
        align: center middle;
        height: auto;
    }
    #warning-actions Button {
        margin: 0 1;
    }
    #btn-cancel {
        background: #334155;
        color: #f8fafc;
        border: tall #1e293b;
    }
    #btn-cancel:hover {
        background: #475569;
        border: tall #334155;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="warning-box"):
            yield Label("⚠️ REMOTE LOCKOUT WARNING (NO SSH RULE)", id="warning-title")
            yield Label(
                "No rule allowing incoming SSH traffic (port 22) was detected.\n\n"
                "If you are currently connected via SSH, enabling the firewall now "
                "will [bold yellow]immediately sever your connection and lock you out[/bold yellow].\n\n"
                "Are you sure you want to enable the firewall without SSH protection?",
                id="warning-text",
            )
            with Horizontal(id="warning-actions"):
                yield Button("🛡 Add SSH (22) Rule First", variant="success", id="btn-add-ssh")
                yield Button("⚠️ Enable Anyway", variant="error", id="btn-force-enable")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add-ssh":
            with self.app.suspend():
                add_firewall_rule("allow", "22", "tcp")
            self.dismiss(True)
        elif event.button.id == "btn-force-enable":
            self.dismiss(True)
        else:
            self.dismiss(False)


class AddRuleModal(ModalScreen[Optional[dict]]):
    """Modal dialog to specify and add a new firewall rule."""

    DEFAULT_CSS = """
    AddRuleModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #add-dialog {
        width: 65;
        height: auto;
        border: round #d97706;
        background: #1e1b18;
        padding: 1 2;
    }
    #add-title {
        text-style: bold;
        color: #f59e0b;
        text-align: center;
        margin-bottom: 1;
    }
    #action-row {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    #action-row Button {
        margin: 0 1;
    }
    .field-label {
        color: #fef3c7;
        margin-top: 1;
    }
    #port-input, #proto-input {
        border: solid #d97706;
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
    #btn-cancel {
        background: #334155;
        color: #f8fafc;
        border: tall #1e293b;
    }
    #btn-cancel:hover {
        background: #475569;
        border: tall #334155;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.chosen_action = "allow"

    def compose(self) -> ComposeResult:
        with Vertical(id="add-dialog"):
            yield Label("➕ Add New Firewall Rule", id="add-title")
            with Horizontal(id="action-row"):
                yield Button("✅ ALLOW", variant="success", id="btn-act-allow")
                yield Button("🚫 DENY", variant="default", id="btn-act-deny")
            yield Label("Port or Service (e.g. 80, 443, 22, or http):", classes="field-label")
            yield Input(placeholder="e.g. 80 or 443", id="port-input")
            yield Label("Protocol (optional: tcp, udp, or leave blank for any):", classes="field-label")
            yield Input(placeholder="any, tcp, or udp", id="proto-input")
            with Horizontal(id="dialog-actions"):
                yield Button("➕ Create Rule", variant="primary", id="btn-submit")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-act-allow":
            self.chosen_action = "allow"
            self.query_one("#btn-act-allow", Button).variant = "success"
            self.query_one("#btn-act-deny", Button).variant = "default"
        elif event.button.id == "btn-act-deny":
            self.chosen_action = "deny"
            self.query_one("#btn-act-deny", Button).variant = "error"
            self.query_one("#btn-act-allow", Button).variant = "default"
        elif event.button.id == "btn-submit":
            port = self.query_one("#port-input", Input).value.strip()
            proto = self.query_one("#proto-input", Input).value.strip().lower()
            if not port:
                return
            self.dismiss({"action": self.chosen_action, "port": port, "proto": proto})
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


class DeleteRuleModal(ModalScreen[bool]):
    """Confirmation modal for deleting an existing firewall rule."""

    DEFAULT_CSS = """
    DeleteRuleModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #del-dialog {
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
    #del-text {
        text-align: center;
        color: white;
        margin-bottom: 1;
    }
    #del-actions {
        align: center middle;
        height: auto;
    }
    #del-actions Button {
        margin: 0 1;
    }
    #btn-cancel {
        background: #334155;
        color: #f8fafc;
        border: tall #1e293b;
    }
    #btn-cancel:hover {
        background: #475569;
        border: tall #334155;
    }
    """

    def __init__(self, rule: FirewallRule) -> None:
        super().__init__()
        self.rule = rule

    def compose(self) -> ComposeResult:
        with Vertical(id="del-dialog"):
            yield Label("🗑 Confirm Rule Deletion", id="del-title")
            yield Label(
                f"Delete Rule #{self.rule.index}?\n\n"
                f"Target: [bold yellow]{self.rule.to_port}[/bold yellow] ({self.rule.action} from {self.rule.from_ip})",
                id="del-text",
            )
            with Horizontal(id="del-actions"):
                yield Button("🗑 Delete", variant="error", id="btn-confirm-del")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-del":
            self.dismiss(True)
        else:
            self.dismiss(False)


class FirewallApp(App[None]):
    """Dedicated Textual TUI for UFW Firewall Management."""

    TITLE = "EasyCLI Firewall Manager"
    SUB_TITLE = "Visual Frontend for UFW (Uncomplicated Firewall) with Safety Guards"

    BINDINGS = [
        Binding("t", "toggle_firewall", "⚡ Toggle ON/OFF", show=True),
        Binding("a", "add_rule", "➕ Add Rule", show=True),
        Binding("d", "delete_rule", "🗑 Delete Rule", show=True),
        Binding("r", "refresh_status", "🔄 Refresh", show=True),
        Binding("q", "quit", "❌ Close", show=True),
    ]

    CSS = """
    Screen {
        background: #0f141c;
        color: #e2e8f0;
    }

    #status-card {
        height: auto;
        min-height: 4;
        background: #1a2234;
        border: round #f59e0b;
        margin: 0 1 1 1;
        padding: 1 2;
        overflow: hidden hidden;
    }

    #status-state {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    #status-meta {
        text-align: center;
        color: #94a3b8;
    }

    #table-container {
        height: 1fr;
        margin: 0 1;
    }

    DataTable {
        height: 100%;
        border: round #d97706;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #282015;
        color: #fbbf24;
    }

    DataTable > .datatable--cursor {
        background: #b45309;
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
        self.status: FirewallStatus = FirewallStatus(installed=True, active=False)
        self.selected_rule: Optional[FirewallRule] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="status-card"):
            yield Static(id="status-state")
            yield Static(id="status-meta")
        with Vertical(id="table-container"):
            yield DataTable(id="rules-table", cursor_type="row")
        with Horizontal(id="action-bar"):
            yield Button("⚡ Toggle ON/OFF", variant="primary", id="btn-toggle")
            yield Button("➕ Add Rule", variant="success", id="btn-add")
            yield Button("🗑 Delete Rule", variant="error", id="btn-delete")
            yield Button("🔄 Refresh", variant="warning", id="btn-refresh")
            yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.add_column("#", width=6)
        table.add_column("Action", width=12)
        table.add_column("To Port / Service", width=24)
        table.add_column("Direction", width=12)
        table.add_column("From", width=22)
        table.add_column("IP Ver", width=10)

        self.refresh_firewall_status()

    def refresh_firewall_status(self) -> None:
        self.status = get_firewall_status()

        state_widget = self.query_one("#status-state", Static)
        meta_widget = self.query_one("#status-meta", Static)

        if self.status.active:
            state_widget.update("[bold green]🛡️ FIREWALL STATUS: ACTIVE & ENFORCING RULES[/bold green]")
        else:
            state_widget.update("[bold red]⚠️ FIREWALL STATUS: INACTIVE (All traffic unfiltered)[/bold red]")

        ssh_badge = (
            "[bold green]SSH Guard: Protected (Port 22 Allowed) ✅[/bold green]"
            if self.status.has_ssh_rule
            else "[bold yellow]SSH Guard: Not Detected (Lockout Risk) ⚠️[/bold yellow]"
        )
        meta_widget.update(
            f"Incoming: [bold]{self.status.default_incoming.upper()}[/bold]  |  "
            f"Outgoing: [bold]{self.status.default_outgoing.upper()}[/bold]  |  "
            f"{ssh_badge}"
        )

        table = self.query_one("#rules-table", DataTable)
        table.clear()

        for rule in self.status.rules:
            action_badge = (
                "[bold green]ALLOW[/bold green]"
                if rule.action == "ALLOW"
                else f"[bold red]{rule.action}[/bold red]"
            )
            v6_str = "IPv6" if rule.v6 else "IPv4"
            table.add_row(
                str(rule.index),
                action_badge,
                rule.to_port,
                rule.direction,
                rule.from_ip,
                v6_str,
                key=str(rule.index),
            )

    def get_current_selected_rule(self) -> Optional[FirewallRule]:
        try:
            table = self.query_one("#rules-table", DataTable)
            if 0 <= table.cursor_row < len(self.status.rules):
                return self.status.rules[table.cursor_row]
        except Exception:
            pass
        if self.selected_rule:
            return self.selected_rule
        if self.status.rules:
            return self.status.rules[0]
        return None

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            row_idx = event.cursor_row
            if 0 <= row_idx < len(self.status.rules):
                self.selected_rule = self.status.rules[row_idx]
        except Exception:
            pass

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        try:
            row_idx = event.coordinate.row
            if 0 <= row_idx < len(self.status.rules):
                self.selected_rule = self.status.rules[row_idx]
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
        self.selected_rule = next((r for r in self.status.rules if str(r.index) == key), None)

    def action_toggle_firewall(self) -> None:
        # Check SSH safety if we are about to enable
        if not self.status.active and not self.status.has_ssh_rule:
            def on_ssh_confirmed(proceed: bool) -> None:
                if proceed:
                    with self.suspend():
                        toggle_firewall(True)
                    self.refresh_firewall_status()

            self.push_screen(SshWarningModal(), on_ssh_confirmed)
            return

        with self.suspend():
            toggle_firewall(not self.status.active)
        self.refresh_firewall_status()

    def action_add_rule(self) -> None:
        def on_rule_added(data: Optional[dict]) -> None:
            if data:
                with self.suspend():
                    add_firewall_rule(data["action"], data["port"], data.get("proto", ""))
                self.refresh_firewall_status()

        self.push_screen(AddRuleModal(), on_rule_added)

    def action_delete_rule(self) -> None:
        rule = self.get_current_selected_rule()
        if not rule:
            return

        def on_del_confirmed(confirmed: bool) -> None:
            if confirmed and rule:
                with self.suspend():
                    delete_firewall_rule(rule.index)
                self.selected_rule = None
                self.refresh_firewall_status()

        self.push_screen(DeleteRuleModal(rule), on_del_confirmed)

    def action_refresh_status(self) -> None:
        self.refresh_firewall_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle":
            self.action_toggle_firewall()
        elif event.button.id == "btn-add":
            self.action_add_rule()
        elif event.button.id == "btn-delete":
            self.action_delete_rule()
        elif event.button.id == "btn-refresh":
            self.action_refresh_status()
        elif event.button.id == "btn-close":
            self.exit()
