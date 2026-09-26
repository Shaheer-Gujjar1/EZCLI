"""Visually distinct Textual TUI application for beginner-friendly chmod and chown editing."""

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
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll  # type: ignore
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
    explain_permissions,
    get_file_permissions,
    get_preset_name,
)


class ConfirmPermissionsModal(ModalScreen[bool]):
    """Confirmation modal before applying permission and ownership changes."""

    DEFAULT_CSS = """
    ConfirmPermissionsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #confirm-box {
        width: 72;
        height: auto;
        border: round #8b5cf6;
        background: #18112c;
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
    }
    #confirm-actions {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #confirm-actions Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        target_name: str,
        old_octal: str,
        new_octal: str,
        preset_title: str,
        owner_group: str,
        owner_changed: bool,
    ) -> None:
        super().__init__()
        self.target_name = target_name
        self.old_octal = old_octal
        self.new_octal = new_octal
        self.preset_title = preset_title
        self.owner_group = owner_group
        self.owner_changed = owner_changed

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("🔐 Confirm Permission Changes", id="confirm-title")
            owner_status = (
                f"[bold yellow]{self.owner_group}[/bold yellow] (Modified)"
                if self.owner_changed
                else f"[dim]{self.owner_group} (Unchanged)[/dim]"
            )
            info = (
                f"Target: [bold cyan]{self.target_name}[/bold cyan]\n\n"
                f"• Permission Setting: [bold yellow]{self.old_octal}[/bold yellow] ➔ [bold green]{self.new_octal}[/bold green] "
                f"({self.preset_title})\n"
                f"• Ownership: {owner_status}\n\n"
                "Apply these modifications to the filesystem now?"
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

    TITLE = "EasyCLI Permissions & Ownership Manager"
    SUB_TITLE = "Beginner-friendly visual permissions with 1-click presets and plain English guides"

    BINDINGS = [
        Binding("q", "quit", "❌ Exit", show=True),
        Binding("s", "apply_changes", "💾 Apply Changes", show=True),
        Binding("r", "reset_permissions", "🔄 Reset", show=True),
    ]

    CSS = """
    Screen {
        background: #0d0a1a;
        color: #ede9fe;
    }

    #main-scroll {
        height: 1fr;
        padding: 0 1;
    }

    .section-card {
        background: #16102b;
        border: round #7c3aed;
        margin: 0 0 1 0;
        padding: 1 2;
        height: auto;
    }

    #target-card {
        background: #1b1238;
        border: round #8b5cf6;
        padding: 1 2;
    }

    .card-title {
        text-style: bold;
        color: #c4b5fd;
        margin-bottom: 1;
    }

    .card-subtitle {
        color: #a78bfa;
        margin-bottom: 1;
    }

    #presets-container {
        height: auto;
        align: left middle;
    }

    #presets-container Button {
        margin-right: 1;
        margin-bottom: 1;
    }

    #summary-card {
        background: #1a1236;
        border: round #a855f7;
    }

    .summary-row {
        margin: 0 0 0 1;
        color: #f3e8ff;
    }

    #summary-mode-banner {
        margin-top: 1;
        padding: 0 1;
        background: #25164a;
        border: solid #6d28d9;
        text-align: center;
        text-style: bold;
    }

    #danger-banner {
        margin-top: 1;
        text-align: center;
        text-style: bold;
    }

    .role-row {
        height: auto;
        align: left middle;
        margin: 0 0 1 0;
        padding: 0 1;
        background: #1f173d;
        border: solid #4c1d95;
    }

    .role-header {
        width: 24;
        text-style: bold;
        color: #e9d5ff;
    }

    Checkbox {
        margin-right: 2;
    }

    .owner-grid {
        height: auto;
        align: left middle;
    }

    .owner-field {
        height: auto;
        margin-right: 2;
    }

    .owner-field Input {
        width: 28;
        border: solid #8b5cf6;
    }

    #action-bar {
        height: auto;
        dock: bottom;
        margin: 0 1 1 1;
        padding: 0 1;
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
        with VerticalScroll(id="main-scroll"):
            # 1. Target Card
            with Vertical(id="target-card", classes="section-card"):
                file_icon = "📁 Folder" if self.perms.is_dir else "📄 File"
                yield Label(f"[bold cyan]{file_icon}:[/bold cyan] [bold white]{self.perms.path}[/bold white]")
                yield Label(
                    f"Current Permissions: [bold yellow]{self.perms.octal}[/bold yellow] ([dim]{self.perms.symbolic}[/dim])  |  "
                    f"Current Owner: [bold cyan]{self.perms.owner_name}[/bold cyan]  |  "
                    f"Group: [bold magenta]{self.perms.group_name}[/bold magenta]"
                )

            # 2. Quick Presets Card
            with Vertical(id="presets-card", classes="section-card"):
                yield Label("⚡ [bold #c4b5fd]1-Click Quick Presets[/bold #c4b5fd] [dim](Choose a common safe configuration)[/dim]", classes="card-title")
                with Horizontal(id="presets-container"):
                    yield Button("🔒 Private (Only Me)", id="preset-private", variant="default")
                    yield Button("📄 Standard File", id="preset-standard", variant="primary")
                    yield Button("⚡ Runnable Script / App", id="preset-executable", variant="default")
                    yield Button("👥 Team Shared", id="preset-team", variant="default")
                    yield Button("🛡️ Read-Only Locked", id="preset-readonly", variant="default")
                    yield Button("⚠️ Full Access (777)", id="preset-full", variant="error")

            # 3. Plain English Summary Card
            with Vertical(id="summary-card", classes="section-card"):
                yield Label("📖 [bold #c4b5fd]What This Means (Plain English Summary)[/bold #c4b5fd]", classes="card-title")
                yield Static(id="summary-owner", classes="summary-row")
                yield Static(id="summary-group", classes="summary-row")
                yield Static(id="summary-others", classes="summary-row")
                yield Static(id="summary-mode-banner")
                yield Static(id="danger-banner")

            # 4. Detailed Permission Matrix
            with Vertical(id="matrix-card", classes="section-card"):
                action_r = "👁️ List Files" if self.perms.is_dir else "👁️ Can View / Read"
                action_w = "✏️ Add/Delete Files" if self.perms.is_dir else "✏️ Can Edit / Modify"
                action_x = "📂 Open Folder" if self.perms.is_dir else "⚡ Run as Program"

                yield Label("🛠️ [bold #c4b5fd]Permissions Matrix[/bold #c4b5fd] [dim](Fine-tune individual permissions below)[/dim]", classes="card-title")

                # Owner Row
                with Horizontal(classes="role-row"):
                    yield Label(f"👤 You (Owner: {self.perms.owner_name}):", classes="role-header")
                    yield Checkbox(action_r, value=self.perms.owner_r, id="cb_u_r")
                    yield Checkbox(action_w, value=self.perms.owner_w, id="cb_u_w")
                    yield Checkbox(action_x, value=self.perms.owner_x, id="cb_u_x")

                # Group Row
                with Horizontal(classes="role-row"):
                    yield Label(f"👥 Your Team ({self.perms.group_name}):", classes="role-header")
                    yield Checkbox(action_r, value=self.perms.group_r, id="cb_g_r")
                    yield Checkbox(action_w, value=self.perms.group_w, id="cb_g_w")
                    yield Checkbox(action_x, value=self.perms.group_x, id="cb_g_x")

                # Others Row
                with Horizontal(classes="role-row"):
                    yield Label("🌐 Everyone Else (Public):", classes="role-header")
                    yield Checkbox(action_r, value=self.perms.other_r, id="cb_o_r")
                    yield Checkbox(action_w, value=self.perms.other_w, id="cb_o_w")
                    yield Checkbox(action_x, value=self.perms.other_x, id="cb_o_x")

            # 5. Ownership Card
            with Vertical(id="owner-card", classes="section-card"):
                yield Label("🔑 [bold #c4b5fd]Ownership Settings (chown)[/bold #c4b5fd]", classes="card-title")
                yield Label("[dim]Leave as current unless transferring ownership to a different user or team account.[/dim]", classes="card-subtitle")
                with Horizontal(classes="owner-grid"):
                    with Vertical(classes="owner-field"):
                        yield Label("File Owner (User):")
                        yield Input(value=self.perms.owner_name, id="inp-owner", placeholder="Username")
                    with Vertical(classes="owner-field"):
                        yield Label("Assigned Group:")
                        yield Input(value=self.perms.group_name, id="inp-group", placeholder="Group name")

        with Horizontal(id="action-bar"):
            yield Button("💾 Save & Apply Changes", variant="primary", id="btn-apply")
            yield Button("🔄 Reset to Original", variant="default", id="btn-reset")
            yield Button("❌ Cancel / Exit", variant="default", id="btn-cancel")
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

    def set_checkboxes(
        self,
        u_r: bool, u_w: bool, u_x: bool,
        g_r: bool, g_w: bool, g_x: bool,
        o_r: bool, o_w: bool, o_x: bool,
    ) -> None:
        self.query_one("#cb_u_r", Checkbox).value = u_r
        self.query_one("#cb_u_w", Checkbox).value = u_w
        self.query_one("#cb_u_x", Checkbox).value = u_x
        self.query_one("#cb_g_r", Checkbox).value = g_r
        self.query_one("#cb_g_w", Checkbox).value = g_w
        self.query_one("#cb_g_x", Checkbox).value = g_x
        self.query_one("#cb_o_r", Checkbox).value = o_r
        self.query_one("#cb_o_w", Checkbox).value = o_w
        self.query_one("#cb_o_x", Checkbox).value = o_x
        self.update_preview()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self.update_preview()

    def update_preview(self) -> None:
        u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x = self.get_current_checkbox_values()
        octal = calculate_octal(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        symbolic = calculate_symbolic(self.perms.is_dir, u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        is_dang, reason = check_dangerous_permissions(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x, self.perms.is_dir)
        preset_name = get_preset_name(octal, self.perms.is_dir)

        owner_exp, group_exp, others_exp = explain_permissions(
            self.perms.is_dir, u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x, group_name=self.perms.group_name
        )

        self.query_one("#summary-owner", Static).update(
            f"• [bold green]👤 You (Owner):[/bold green] {owner_exp}"
        )
        self.query_one("#summary-group", Static).update(
            f"• [bold cyan]👥 Your Team ({self.perms.group_name}):[/bold cyan] {group_exp}"
        )
        self.query_one("#summary-others", Static).update(
            f"• [bold magenta]🌐 Everyone Else:[/bold magenta] {others_exp}"
        )

        mode_banner = self.query_one("#summary-mode-banner", Static)
        mode_banner.update(
            f"⚙️ Config: [bold yellow]{preset_name}[/bold yellow]  |  "
            f"Octal: [bold green]{octal}[/bold green]  |  "
            f"Symbolic: [bold cyan]{symbolic}[/bold cyan]"
        )

        danger_banner = self.query_one("#danger-banner", Static)
        if is_dang:
            danger_banner.update(f"[bold red]{reason}[/bold red]")
        else:
            danger_banner.update("[dim green]✓ Safe and standard permission configuration[/dim green]")

    def apply_preset(self, preset_key: str) -> None:
        is_dir = self.perms.is_dir
        if preset_key == "private":
            if is_dir:
                self.set_checkboxes(True, True, True, False, False, False, False, False, False)
            else:
                self.set_checkboxes(True, True, False, False, False, False, False, False, False)
            self.notify("Applied 'Private (Only Me)' preset", severity="information")
        elif preset_key == "standard":
            if is_dir:
                self.set_checkboxes(True, True, True, True, False, True, True, False, True)
            else:
                self.set_checkboxes(True, True, False, True, False, False, True, False, False)
            self.notify("Applied 'Standard' file preset", severity="information")
        elif preset_key == "executable":
            self.set_checkboxes(True, True, True, True, False, True, True, False, True)
            self.notify("Applied 'Runnable Script / Program' preset", severity="information")
        elif preset_key == "team":
            if is_dir:
                self.set_checkboxes(True, True, True, True, True, True, True, False, True)
            else:
                self.set_checkboxes(True, True, False, True, True, False, True, False, False)
            self.notify("Applied 'Team Shared' preset", severity="information")
        elif preset_key == "readonly":
            if is_dir:
                self.set_checkboxes(True, False, True, True, False, True, True, False, True)
            else:
                self.set_checkboxes(True, False, False, True, False, False, True, False, False)
            self.notify("Applied 'Read-Only Locked' preset", severity="information")
        elif preset_key == "full":
            self.set_checkboxes(True, True, True, True, True, True, True, True, True)
            self.notify("Applied 'Full Access (777)' preset", severity="warning")

    def action_apply_changes(self) -> None:
        u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x = self.get_current_checkbox_values()
        new_octal = calculate_octal(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
        preset_title = get_preset_name(new_octal, self.perms.is_dir)
        new_owner = self.query_one("#inp-owner", Input).value.strip()
        new_group = self.query_one("#inp-group", Input).value.strip()

        owner_changed = (new_owner != self.perms.owner_name) or (new_group != self.perms.group_name)
        owner_group_str = f"{new_owner}:{new_group}"

        def on_confirmed(proceed: bool) -> None:
            if proceed:
                with self.suspend():
                    ok, msg = apply_permissions(
                        path=self.perms.path,
                        octal=new_octal,
                        new_owner=new_owner if new_owner != self.perms.owner_name else None,
                        new_group=new_group if new_group != self.perms.group_name else None,
                    )
                if ok:
                    self.exit()
                else:
                    self.notify(f"Update failed: {msg}", title="Error", severity="error")

        self.push_screen(
            ConfirmPermissionsModal(
                target_name=self.perms.name,
                old_octal=self.perms.octal,
                new_octal=new_octal,
                preset_title=preset_title,
                owner_group=owner_group_str,
                owner_changed=owner_changed,
            ),
            on_confirmed,
        )

    def action_reset_permissions(self) -> None:
        self.set_checkboxes(
            self.perms.owner_r,
            self.perms.owner_w,
            self.perms.owner_x,
            self.perms.group_r,
            self.perms.group_w,
            self.perms.group_x,
            self.perms.other_r,
            self.perms.other_w,
            self.perms.other_x,
        )
        self.query_one("#inp-owner", Input).value = self.perms.owner_name
        self.query_one("#inp-group", Input).value = self.perms.group_name
        self.notify("Reset all permissions and ownership to original", severity="information")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "btn-apply":
            self.action_apply_changes()
        elif button_id == "btn-reset":
            self.action_reset_permissions()
        elif button_id == "btn-cancel":
            self.exit()
        elif button_id.startswith("preset-"):
            preset_key = button_id.replace("preset-", "")
            self.apply_preset(preset_key)
