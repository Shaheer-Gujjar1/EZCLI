"""Visually distinct Textual TUI application for visual chmod and chown editing."""

import glob
import os
import sys
from typing import Optional

venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Grid, Horizontal, Vertical  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from .permissions_engine import (
    FilePermissions,
    apply_permissions,
    calculate_octal,
    calculate_symbolic,
    check_dangerous_permissions,
    get_file_permissions,
)


class ConfirmPermissionsModal(ModalScreen[bool]):
    """Confirmation modal before applying permission and ownership changes."""

    DEFAULT_CSS = """
    ConfirmPermissionsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #confirm-box {
        width: 65;
        height: auto;
        border: round #8b5cf6;
        background: #1e1b4b;
        padding: 1 2;
    }
    #confirm-title {
        text-style: bold;
        color: #c4b5fd;
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-details {
        color: #ede9fe;
        margin-bottom: 1;
        text-align: center;
    }
    #confirm-actions {
        align: center middle;
        height: auto;
    }
    #confirm-actions Button {
        margin: 0 1;
    }
    """

    def __init__(self, target_name: str, old_octal: str, new_octal: str, owner_group: str) -> None:
        super().__init__()
        self.target_name = target_name
        self.old_octal = old_octal
        self.new_octal = new_octal
        self.owner_group = owner_group

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("🔐 Confirm Permission Changes", id="confirm-title")
            info = (
                f"Target: [bold yellow]{self.target_name}[/bold yellow]\n\n"
                f"• Permission Mode: [bold cyan]{self.old_octal}[/bold cyan] ➔ [bold green]{self.new_octal}[/bold green]\n"
                f"• Ownership: [bold]{self.owner_group}[/bold]\n\n"
                "Apply these modifications now?"
            )
            yield Label(info, id="confirm-details")
            with Horizontal(id="confirm-actions"):
                yield Button("✅ Apply Changes", variant="primary", id="btn-confirm-apply")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-apply":
            self.dismiss(True)
        else:
            self.dismiss(False)


class PermissionsApp(App[None]):
    """Textual interactive terminal visual permissions and ownership editor."""

    TITLE = "EasyCLI Permissions & Ownership Editor"
    SUB_TITLE = "Visual chmod & chown with Live Octal Preview and Safety Guards"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("s", "apply_changes", "💾 Apply Changes", show=True),
        Binding("r", "reset_permissions", "🔄 Reset", show=True),
    ]

    CSS = """
    Screen {
        background: #0f0a1c;
        color: #e9d5ff;
    }

    #file-card {
        height: 4;
        background: #1e1035;
        border: round #8b5cf6;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
    }

    #preview-card {
        height: 4;
        background: #2e1065;
        border: round #a855f7;
        margin: 0 1 1 1;
        padding: 0 1;
        content-align: center middle;
    }

    #grid-container {
        height: auto;
        border: round #7c3aed;
        background: #180d2e;
        margin: 0 1 1 1;
        padding: 1 2;
    }

    .grid-row {
        height: 3;
        align: left middle;
    }

    .row-header {
        width: 14;
        text-style: bold;
        color: #d8b4fe;
    }

    Checkbox {
        margin-right: 4;
    }

    #owner-box {
        height: auto;
        border: round #6366f1;
        background: #130e26;
        margin: 0 1 1 1;
        padding: 1 2;
    }

    .owner-inputs {
        height: auto;
        align: left middle;
    }

    .owner-inputs Input {
        width: 25;
        margin-right: 2;
        border: solid #8b5cf6;
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

    def __init__(self, target_path: str) -> None:
        super().__init__()
        self.target_path = os.path.abspath(os.path.expanduser(target_path))
        self.perms = get_file_permissions(self.target_path)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="file-card"):
            file_type = "📁 Directory" if self.perms.is_dir else "📄 File"
            yield Label(
                f"[bold cyan]{file_type}:[/bold cyan] [bold white]{self.perms.path}[/bold white]  |  "
                f"Current: [bold yellow]{self.perms.octal}[/bold yellow] ([dim]{self.perms.symbolic}[/dim])  |  "
                f"Owner: [bold]{self.perms.owner_name}:{self.perms.group_name}[/bold]"
            )
        with Vertical(id="preview-card"):
            yield Static(id="live-mode-preview")
            yield Static(id="danger-banner")
        with Vertical(id="grid-container"):
            yield Label("[bold #f3e8ff]Permission Matrix (Owner / Group / Others)[/bold #f3e8ff]")
            with Horizontal(classes="grid-row"):
                yield Label("👤 Owner (User):", classes="row-header")
                yield Checkbox("Read (r/4)", value=self.perms.owner_r, id="cb_u_r")
                yield Checkbox("Write (w/2)", value=self.perms.owner_w, id="cb_u_w")
                yield Checkbox("Execute (x/1)", value=self.perms.owner_x, id="cb_u_x")
            with Horizontal(classes="grid-row"):
                yield Label("👥 Group:", classes="row-header")
                yield Checkbox("Read (r/4)", value=self.perms.group_r, id="cb_g_r")
                yield Checkbox("Write (w/2)", value=self.perms.group_w, id="cb_g_w")
                yield Checkbox("Execute (x/1)", value=self.perms.group_x, id="cb_g_x")
            with Horizontal(classes="grid-row"):
                yield Label("🌐 Others:", classes="row-header")
                yield Checkbox("Read (r/4)", value=self.perms.other_r, id="cb_o_r")
                yield Checkbox("Write (w/2)", value=self.perms.other_w, id="cb_o_w")
                yield Checkbox("Execute (x/1)", value=self.perms.other_x, id="cb_o_x")
        with Vertical(id="owner-box"):
            yield Label("[bold #f3e8ff]Ownership Settings (chown)[/bold #f3e8ff]")
            with Horizontal(classes="owner-inputs"):
                yield Label("Owner User: ", classes="row-header")
                yield Input(value=self.perms.owner_name, id="inp-owner")
                yield Label("Group: ", classes="row-header")
                yield Input(value=self.perms.group_name, id="inp-group")
        with Horizontal(id="action-bar"):
            yield Button("💾 Apply Changes", variant="primary", id="btn-apply")
            yield Button("🔄 Reset", variant="default", id="btn-reset")
            yield Button("❌ Cancel", variant="default", id="btn-cancel")
        yield Footer()

    def on_mount(self) -> None:
        self.update_preview()

    def get_current_checkbox_values(self):
        return (
            self.query_one("#cb_u_r", Checkbox).value,
            self.query_one("#cb_u_w", Checkbox).value,
            self.query_one("#cb_u_x", Checkbox).value,
            self.query_one("#cb_g_r", Checkbox).value,
            self.query_one("#cb_g_w", Checkbox).value,
            self.query_one("#cb_g_x", Checkbox).value,
            self.query_one("#cb_o_r", Checkbox).value,
            self.query_one("#cb_o_w", Checkbox).value,
            self.query_one("#cb_o_x", Checkbox).value,
        )

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self.update_preview()

    def update_preview(self) -> None:
        u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x = self.get_current_checkbox_values()
        octal = calculate_octal(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        symbolic = calculate_symbolic(self.perms.is_dir, u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        is_dang, reason = check_dangerous_permissions(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x, self.perms.is_dir)

        preview_label = self.query_one("#live-mode-preview", Static)
        danger_label = self.query_one("#danger-banner", Static)

        preview_label.update(
            f"Preview: Mode [bold green]{octal}[/bold green]  |  "
            f"Symbolic: [bold cyan]{symbolic}[/bold cyan]"
        )

        if is_dang:
            danger_label.update(f"[bold red]{reason}[/bold red]")
        else:
            danger_label.update("[dim green]✓ Safe permission configuration[/dim green]")

    def action_apply_changes(self) -> None:
        u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x = self.get_current_checkbox_values()
        new_octal = calculate_octal(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        new_owner = self.query_one("#inp-owner", Input).value.strip()
        new_group = self.query_one("#inp-group", Input).value.strip()

        owner_group_str = f"{new_owner}:{new_group}"

        def on_confirmed(proceed: bool) -> None:
            if proceed:
                apply_permissions(
                    path=self.perms.path,
                    octal=new_octal,
                    new_owner=new_owner if new_owner != self.perms.owner_name else None,
                    new_group=new_group if new_group != self.perms.group_name else None,
                )
                self.exit()

        self.push_screen(
            ConfirmPermissionsModal(
                target_name=self.perms.name,
                old_octal=self.perms.octal,
                new_octal=new_octal,
                owner_group=owner_group_str,
            ),
            on_confirmed,
        )

    def action_reset_permissions(self) -> None:
        self.query_one("#cb_u_r", Checkbox).value = self.perms.owner_r
        self.query_one("#cb_u_w", Checkbox).value = self.perms.owner_w
        self.query_one("#cb_u_x", Checkbox).value = self.perms.owner_x
        self.query_one("#cb_g_r", Checkbox).value = self.perms.group_r
        self.query_one("#cb_g_w", Checkbox).value = self.perms.group_w
        self.query_one("#cb_g_x", Checkbox).value = self.perms.group_x
        self.query_one("#cb_o_r", Checkbox).value = self.perms.other_r
        self.query_one("#cb_o_w", Checkbox).value = self.perms.other_w
        self.query_one("#cb_o_x", Checkbox).value = self.perms.other_x
        self.query_one("#inp-owner", Input).value = self.perms.owner_name
        self.query_one("#inp-group", Input).value = self.perms.group_name
        self.update_preview()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-apply":
            self.action_apply_changes()
        elif event.button.id == "btn-reset":
            self.action_reset_permissions()
        elif event.button.id == "btn-cancel":
            self.exit()
