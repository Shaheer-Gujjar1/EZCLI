"""User profile and secure password management for EasyCLI."""

import getpass
import grp
import os
import pwd
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from .elevation import elevated_user_chpasswd, prompt_password_dots


def get_user_profile_data() -> Dict[str, Any]:
    """Collect current user details."""
    username = getpass.getuser()
    try:
        pw_record = pwd.getpwnam(username)
        full_name = pw_record.pw_gecos.split(",")[0] if pw_record.pw_gecos else username
        home_dir = pw_record.pw_dir
        shell = pw_record.pw_shell
        uid = pw_record.pw_uid
        gid = pw_record.pw_gid
    except KeyError:
        full_name = username
        home_dir = str(Path.home())
        shell = os.environ.get("SHELL", "/bin/bash")
        uid = os.getuid()
        gid = os.getgid()

    # Groups
    groups = set()
    try:
        for g in grp.getgrall():
            if username in g.gr_mem:
                groups.add(g.gr_name)
        primary_group = grp.getgrgid(gid).gr_name
        groups.add(primary_group)
    except Exception:
        pass

    # Sudo status check
    is_sudo = False
    sudo_label = "Standard User"
    if uid == 0:
        is_sudo = True
        sudo_label = "Administrator (root)"
    elif any(g in ["sudo", "wheel", "admin"] for g in groups):
        is_sudo = True
        # Check if passwordless
        try:
            res = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=2)
            if res.returncode == 0:
                sudo_label = "Administrator (Passwordless sudo)"
            else:
                sudo_label = "Administrator (Sudo group)"
        except Exception:
            sudo_label = "Administrator (Sudo group)"
    else:
        try:
            res = subprocess.run(["sudo", "-n", "-l"], capture_output=True, timeout=2)
            if res.returncode == 0:
                is_sudo = True
                sudo_label = "Administrator (Authorized in sudoers)"
        except Exception:
            pass

    return {
        "username": username,
        "full_name": full_name,
        "uid": uid,
        "gid": gid,
        "home_dir": home_dir,
        "shell": shell,
        "groups": sorted(list(groups)),
        "is_sudo": is_sudo,
        "sudo_label": sudo_label,
    }


def render_user_profile_card(data: Dict[str, Any], console: Console) -> None:
    """Render the user profile card."""
    sudo_badge = f"[bold green]{data['sudo_label']}[/bold green]" if data["is_sudo"] else f"[dim]{data['sudo_label']}[/dim]"
    groups_str = ", ".join(data["groups"][:12])
    if len(data["groups"]) > 12:
        groups_str += f" [dim](+{len(data['groups']) - 12} more)[/dim]"

    content = (
        f"[bold cyan]Username:[/bold cyan]    {data['username']} (UID {data['uid']})\n"
        f"[bold cyan]Full Name:[/bold cyan]   {data['full_name']}\n"
        f"[bold cyan]Account Type:[/bold cyan] {sudo_badge}\n"
        f"[bold cyan]Home Dir:[/bold cyan]    {data['home_dir']}\n"
        f"[bold cyan]Login Shell:[/bold cyan] {data['shell']}\n"
        f"[bold cyan]Groups:[/bold cyan]       {groups_str}\n"
    )

    console.print(
        Panel(
            content,
            title=f"👤 User Profile: [bold white]{data['username']}[/bold white]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


class PasswordChangeModal(ModalScreen[Optional[Tuple[str, str]]]):
    """Textual modal dialog for changing user password with show/hide toggle."""

    DEFAULT_CSS = """
    PasswordChangeModal {
        align: center middle;
    }
    #pwd-dialog {
        width: 58;
        height: auto;
        border: thick cyan;
        background: $surface;
        padding: 1 2;
    }
    #pwd-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: cyan;
    }
    #pwd-status {
        text-align: center;
        margin-bottom: 1;
        color: red;
    }
    .pwd-field {
        margin-bottom: 1;
    }
    #pwd-toggle-container {
        align: center middle;
        margin-bottom: 1;
    }
    #pwd-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #pwd-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, username: str, is_passwordless: bool = False) -> None:
        super().__init__()
        self.username = username
        self.is_passwordless = is_passwordless

    def compose(self) -> ComposeResult:
        with Vertical(id="pwd-dialog"):
            yield Label(f"🔒 Change Password for '{self.username}'", id="pwd-title")
            yield Label("", id="pwd-status")

            if not self.is_passwordless:
                yield Label("Current Password:")
                yield Input(
                    placeholder="Enter current password...",
                    password=True,
                    id="input-curr-pwd",
                    classes="pwd-field",
                )

            yield Label("New Password:")
            yield Input(
                placeholder="Enter new password (any length)...",
                password=True,
                id="input-new-pwd",
                classes="pwd-field",
            )

            with Horizontal(id="pwd-toggle-container"):
                yield Button("👁️ Show Password", id="btn-toggle-pwd", variant="default")

            yield Label("Confirm New Password:")
            yield Input(
                placeholder="Re-enter new password...",
                password=True,
                id="input-confirm-pwd",
                classes="pwd-field",
            )

            with Horizontal(id="pwd-buttons"):
                yield Button("💾 Update Password", variant="primary", id="btn-save")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-pwd":
            inp_new = self.query_one("#input-new-pwd", Input)
            inp_confirm = self.query_one("#input-confirm-pwd", Input)
            if inp_new.password:
                inp_new.password = False
                inp_confirm.password = False
                event.button.label = "🙈 Hide Password"
            else:
                inp_new.password = True
                inp_confirm.password = True
                event.button.label = "👁️ Show Password"
        elif event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            curr_pwd = ""
            if not self.is_passwordless:
                curr_inp = self.query_one("#input-curr-pwd", Input)
                curr_pwd = curr_inp.value

            new_pwd = self.query_one("#input-new-pwd", Input).value
            confirm_pwd = self.query_one("#input-confirm-pwd", Input).value

            status_label = self.query_one("#pwd-status", Label)
            if not new_pwd:
                status_label.update("[bold red]New password cannot be empty.[/bold red]")
                return
            if new_pwd != confirm_pwd:
                status_label.update("[bold red]New passwords do not match![/bold red]")
                return

            self.dismiss((curr_pwd, new_pwd))


class ProfilePasswordApp(App[Optional[Tuple[str, str]]]):
    """Lightweight runner app for password modal."""

    def __init__(self, username: str, is_passwordless: bool = False) -> None:
        super().__init__()
        self.username = username
        self.is_passwordless = is_passwordless

    def on_mount(self) -> None:
        def handle_result(res: Optional[Tuple[str, str]]) -> None:
            self.exit(res)

        self.push_screen(PasswordChangeModal(self.username, self.is_passwordless), handle_result)


def execute_password_change(username: str, is_passwordless: bool, console: Console) -> None:
    """Prompt for password change and update using chpasswd over stdin."""
    creds: Optional[Tuple[str, str]] = None

    if sys.stdin.isatty():
        try:
            app = ProfilePasswordApp(username, is_passwordless)
            creds = app.run()
        except Exception:
            creds = None

    if creds is None:
        # Fallback or terminal mode
        if not sys.stdin.isatty():
            console.print("[yellow]Password change requires an interactive terminal.[/yellow]")
            return

        console.print("\n[bold cyan]🔑 Password Change[/bold cyan]")
        curr_pwd = ""
        if not is_passwordless:
            curr_pwd = prompt_password_dots("Current password: ") or ""
        new_pwd = prompt_password_dots("New password: ") or ""
        confirm_pwd = prompt_password_dots("Confirm new password: ") or ""

        if not new_pwd:
            console.print("[dim]Cancelled. Password was not changed.[/dim]")
            return
        if new_pwd != confirm_pwd:
            console.print("[bold red]Error: New passwords do not match![/bold red]")
            return
        creds = (curr_pwd, new_pwd)

    curr_pwd, new_pwd = creds
    console.print("[dim]Updating login password...[/dim]")
    ok, err = elevated_user_chpasswd(username, new_pwd, console=console)
    if ok:
        console.print(
            Panel(
                f"✨ [bold green]Password updated successfully for user '{username}'![/bold green]\n\n"
                "Your new login credentials are now active.",
                title="[bold green]Success[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]Failed to update password:[/bold red]\n\n{err or 'Permission denied or invalid credentials.'}",
                title="[bold red]Error[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


def run_profile_cli(console: Optional[Console] = None) -> None:
    """Run ez profile: show user details and offer password change."""
    if console is None:
        console = Console()

    data = get_user_profile_data()
    render_user_profile_card(data, console)

    console.print("\n[bold]Options:[/bold]")
    console.print("  • Press [bold cyan]p[/bold cyan] to change your login password")
    console.print("  • Press [bold green]Enter[/bold green] to return to shell\n")

    choice = Prompt.ask("Action", choices=["p", "P", ""], default="", console=console).strip().lower()
    if choice == "p":
        is_passwordless = "Passwordless" in data["sudo_label"]
        execute_password_change(data["username"], is_passwordless, console)
