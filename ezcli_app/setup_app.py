"""Modern Windows-style Setup & Management Wizard for EasyCLI.
Built with Textual for a full-screen, mouse-supported, responsive installer experience.
"""

import glob
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

# Ensure venv site-packages is accessible if textual is installed in user venv
venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual import work  # type: ignore
from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Horizontal, Vertical, VerticalScroll  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Checkbox,
    ContentSwitcher,
    Log,
    ProgressBar,
    RadioButton,
    RadioSet,
    Static,
)

EZ_HOME = Path.home() / ".local" / "share" / "ez"
APP_DIR = EZ_HOME / "app"
VENV_DIR = EZ_HOME / "venv"
SYS_BIN_DIR = Path("/usr/local/bin")
USER_BIN_DIR = Path.home() / ".local" / "bin"
EMOJI_CONF = Path.home() / ".config" / "fontconfig" / "conf.d" / "99-noto-color-emoji.conf"
APP_VERSION = "0.6.0"


def get_distro_info() -> str:
    """Detect the Linux distribution name and version."""
    os_release = Path("/etc/os-release")
    if os_release.exists():
        try:
            with open(os_release, "r", encoding="utf-8") as f:
                data = {}
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        data[k] = v.strip('"')
                name = data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
                return f"{name} ({platform.machine()})"
        except Exception:
            pass
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def detect_installation() -> Tuple[bool, str]:
    """Check whether EasyCLI is currently installed."""
    for loc in [SYS_BIN_DIR / "ez", USER_BIN_DIR / "ez"]:
        if loc.exists() or loc.is_symlink():
            try:
                real = os.path.realpath(str(loc))
                return True, f"{loc} -> {real}"
            except Exception:
                return True, str(loc)
    which_ez = shutil.which("ez")
    if which_ez:
        return True, which_ez
    return False, "Not Installed"


class SetupWizardApp(App[None]):
    """Modern Windows-style setup wizard for EasyCLI with full mouse click and keyboard support."""

    TITLE = "EasyCLI Setup Wizard"
    SUB_TITLE = f"Version {APP_VERSION}"

    CSS = """
    Screen {
        background: #0d1117;
        align: center middle;
        overflow: hidden;
    }

    #wizard-window {
        width: 82;
        max-width: 98%;
        height: 22;
        max-height: 98%;
        border: round #388bfd;
        background: #161b22;
        padding: 0;
    }

    #wizard-header {
        height: 1;
        background: #1f6feb;
        color: white;
        text-style: bold;
        padding: 0 1;
        content-align: center middle;
    }

    #wizard-body {
        height: 1fr;
    }

    #sidebar {
        width: 21;
        background: #0d1117;
        border-right: solid #30363d;
        padding: 1 1;
    }

    .step-item {
        color: #8b949e;
        margin-bottom: 1;
        padding: 0 1;
    }

    .step-active {
        color: #58a6ff;
        text-style: bold;
        background: #1f6feb33;
    }

    .step-done {
        color: #3fb950;
    }

    #content-area {
        width: 1fr;
        padding: 0 1;
        background: #161b22;
    }

    ContentSwitcher {
        height: 100%;
        width: 100%;
    }

    .wizard-page {
        height: 100%;
        width: 100%;
        padding: 0 1;
    }

    .screen-title {
        color: #f0f6fc;
        text-style: bold;
        margin-top: 0;
        margin-bottom: 0;
    }

    .screen-subtitle {
        color: #8b949e;
        margin-bottom: 1;
    }

    #system-card {
        background: #21262d;
        border: round #30363d;
        padding: 0 1;
        margin-bottom: 1;
        height: auto;
    }

    .card-line {
        color: #c9d1d9;
    }

    .status-installed {
        color: #3fb950;
        text-style: bold;
    }

    .status-not-installed {
        color: #d29922;
        text-style: bold;
    }

    RadioSet {
        background: transparent;
        border: none;
        margin: 0;
        padding: 0;
        height: auto;
    }

    RadioButton {
        background: transparent;
        color: #c9d1d9;
        padding: 0;
        margin: 0;
    }

    Checkbox {
        background: transparent;
        color: #c9d1d9;
        margin: 0;
        padding: 0;
    }

    ProgressBar {
        margin: 0;
        tint: #1f6feb;
    }

    #progress-log {
        height: 8;
        background: #0d1117;
        border: solid #30363d;
        color: #c9d1d9;
        margin-top: 1;
    }

    #diag-log {
        height: 11;
        background: #0d1117;
        border: solid #30363d;
        color: #c9d1d9;
        padding: 0 1;
        margin-top: 1;
    }

    #wizard-footer {
        height: 4;
        border-top: solid #30363d;
        background: #161b22;
        padding: 0 1;
        align: right middle;
    }

    #wizard-footer Button {
        margin-left: 2;
        min-width: 14;
        height: 3;
    }

    .primary-btn {
        background: #238636;
        color: #ffffff;
        text-style: bold;
    }

    .danger-btn {
        background: #da3633;
        color: #ffffff;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Exit"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.is_installed, self.install_location = detect_installation()
        self.distro_name = get_distro_info()
        self.selected_action = "install"  # install, custom, uninstall, diagnostics
        self.target_scope = "system"  # system, user
        self.enable_emoji = True
        self.remove_user_data = False
        self.remove_fonts = False
        self.launch_after = True

    def compose(self) -> ComposeResult:
        status_str = f"● Installed in {self.install_location}" if self.is_installed else "○ Not Installed"
        status_cls = "status-installed" if self.is_installed else "status-not-installed"

        with Container(id="wizard-window"):
            yield Static(
                f"💻 EasyCLI Setup & Management Wizard  │  v{APP_VERSION}",
                id="wizard-header",
            )
            with Horizontal(id="wizard-body"):
                with Vertical(id="sidebar"):
                    yield Static("1. Action Select", classes="step-item step-active", id="step-1")
                    yield Static("2. Configuration", classes="step-item", id="step-2")
                    yield Static("3. Execution", classes="step-item", id="step-3")
                    yield Static("4. Complete", classes="step-item", id="step-4")

                with Vertical(id="content-area"):
                    with ContentSwitcher(initial="page-welcome", id="wizard-switcher"):
                        # Page 1: Welcome & Action Select
                        with Vertical(id="page-welcome", classes="wizard-page"):
                            yield Static("Welcome to EasyCLI Setup Wizard", classes="screen-title")
                            yield Static("Choose an installation or management task below:", classes="screen-subtitle")
                            with Vertical(id="system-card"):
                                yield Static(f"Platform:  [bold]{self.distro_name}[/bold]", classes="card-line")
                                yield Static(f"Python:    [bold]{platform.python_version()}[/bold]", classes="card-line")
                                yield Static(f"Status:    [{status_cls}]{status_str}[/{status_cls}]", classes="card-line")

                            if self.is_installed:
                                with RadioSet(id="action-radios"):
                                    yield RadioButton("🔄 Reinstall / Update EasyCLI (Recommended)", id="act-reinstall", value=True)
                                    yield RadioButton("⚙️ Custom Reinstallation & Scope", id="act-custom")
                                    yield RadioButton("🗑️ Uninstall EasyCLI completely", id="act-uninstall")
                                    yield RadioButton("🩺 System Diagnostics & Verification", id="act-diagnostics")
                            else:
                                with RadioSet(id="action-radios"):
                                    yield RadioButton("🚀 Express Install (Recommended system-wide)", id="act-express", value=True)
                                    yield RadioButton("⚙️ Custom Installation (Choose scope & fonts)", id="act-custom")
                                    yield RadioButton("🗑️ Clean / Uninstall Previous Residuals", id="act-uninstall")
                                    yield RadioButton("🩺 System Diagnostics & Verification", id="act-diagnostics")

                        # Page 2: Custom Options
                        with Vertical(id="page-custom", classes="wizard-page"):
                            yield Static("Custom Installation Options", classes="screen-title")
                            yield Static("Configure destination directory scope and components:", classes="screen-subtitle")
                            yield Static("1. Installation Scope:", classes="card-line")
                            with RadioSet(id="scope-radios"):
                                yield RadioButton("System-Wide (/usr/local/bin/ez) - Available to all users (sudo)", id="scope-sys", value=True)
                                yield RadioButton("User-Only (~/.local/bin/ez) - No administrator/sudo required", id="scope-user")
                            yield Static("2. Components & Enhancements:", classes="card-line")
                            yield Checkbox("Core EasyCLI Binaries & Wrappers", value=True, disabled=True)
                            yield Checkbox("Noto Color Emoji font prioritization for 3D icons", value=True, id="chk-emoji")
                            yield Checkbox("Setup Manager shortcut ('ez-setup')", value=True, disabled=True)

                        # Page 3: Uninstall Options
                        with Vertical(id="page-uninstall", classes="wizard-page"):
                            yield Static("Uninstall EasyCLI", classes="screen-title")
                            yield Static("Select which components should be safely removed:", classes="screen-subtitle")
                            yield Checkbox("Command shortcuts (/usr/local/bin/ez, ez-setup)", value=True, disabled=True)
                            yield Checkbox("Application files and virtual environment (~/.local/share/ez)", value=True, disabled=True)
                            yield Checkbox("Remove user bookmarks, history, and preferences", value=False, id="chk-data")
                            yield Checkbox("Revert Noto Color Emoji font prioritization", value=False, id="chk-fonts")

                        # Page 4: Diagnostics View
                        with Vertical(id="page-diagnostics", classes="wizard-page"):
                            yield Static("System & Runtime Diagnostics", classes="screen-title")
                            with VerticalScroll(id="diag-log"):
                                yield Static(f"• OS Platform:    {self.distro_name}")
                                yield Static(f"• Python Runtime: {sys.version.split()[0]} ({sys.executable})")
                                yield Static(f"• EasyCLI Home:   {EZ_HOME}")
                                yield Static(f"• Installed Bin:  {self.install_location}")
                                yield Static(f"• Emoji Override: {'Present' if EMOJI_CONF.exists() else 'System Default'}")
                                which_ez = shutil.which("ez")
                                yield Static(f"• PATH Status:    {'Found: ' + which_ez if which_ez else 'Not currently in PATH'}")

                        # Page 5: Progress View
                        with Vertical(id="page-progress", classes="wizard-page"):
                            yield Static("Executing Operation...", classes="screen-title", id="progress-title")
                            yield ProgressBar(total=100, show_eta=False, id="prog-bar")
                            yield Static("Preparing task...", id="prog-status")
                            yield Log(id="progress-log")

                        # Page 6: Finish View
                        with Vertical(id="page-finish", classes="wizard-page"):
                            yield Static("Operation Complete!", classes="screen-title", id="finish-title")
                            yield Static("EasyCLI operation completed successfully.", classes="screen-subtitle", id="finish-subtitle")
                            with Vertical(id="finish-card"):
                                yield Static("Command Launcher:  [bold cyan]ez[/bold cyan]", classes="card-line")
                                yield Static("Setup Manager:     [bold cyan]ez-setup[/bold cyan]", classes="card-line")
                                yield Static("Help & Manual:     [bold cyan]ez help[/bold cyan]", classes="card-line")
                                yield Static("Diagnostics:       [bold cyan]ez system-info[/bold cyan]", classes="card-line")
                            yield Checkbox("Launch EasyCLI now", value=True, id="chk-launch")

            with Horizontal(id="wizard-footer"):
                yield Button("< Back", id="btn-back", disabled=True)
                yield Button("Next >", id="btn-next", classes="primary-btn")
                yield Button("Cancel", id="btn-cancel")

    def update_sidebar(self, step: int) -> None:
        for i in range(1, 5):
            w = self.query_one(f"#step-{i}", Static)
            w.remove_class("step-active")
            w.remove_class("step-done")
            if i < step:
                w.add_class("step-done")
            elif i == step:
                w.add_class("step-active")

    def switch_page(self, page_id: str) -> None:
        switcher = self.query_one("#wizard-switcher", ContentSwitcher)
        switcher.current = page_id

        btn_back = self.query_one("#btn-back", Button)
        btn_next = self.query_one("#btn-next", Button)

        if page_id == "page-welcome":
            self.update_sidebar(1)
            btn_back.disabled = True
            btn_next.disabled = False
            btn_next.label = "Next >"
            btn_next.classes = "primary-btn"

        elif page_id == "page-custom":
            self.update_sidebar(2)
            btn_back.disabled = False
            btn_next.disabled = False
            btn_next.label = "Install Now"
            btn_next.classes = "primary-btn"

        elif page_id == "page-uninstall":
            self.update_sidebar(2)
            btn_back.disabled = False
            btn_next.disabled = False
            btn_next.label = "Uninstall Now"
            btn_next.classes = "danger-btn"

        elif page_id == "page-diagnostics":
            self.update_sidebar(2)
            btn_back.disabled = False
            btn_next.disabled = False
            btn_next.label = "Back to Menu"
            btn_next.classes = "primary-btn"

        elif page_id == "page-progress":
            self.update_sidebar(3)
            btn_back.disabled = True
            btn_next.disabled = True
            btn_next.label = "Working..."

            title_w = self.query_one("#progress-title", Static)
            if self.selected_action == "uninstall":
                title_w.update("Uninstalling EasyCLI...")
                self.run_uninstall_worker()
            else:
                title_w.update("Installing EasyCLI...")
                self.run_install_worker()

        elif page_id == "page-finish":
            self.update_sidebar(4)
            btn_back.disabled = True
            btn_next.disabled = False
            btn_next.label = "Finish"
            btn_next.classes = "primary-btn"

            f_title = self.query_one("#finish-title", Static)
            f_sub = self.query_one("#finish-subtitle", Static)
            f_card = self.query_one("#finish-card", Vertical)
            chk_launch = self.query_one("#chk-launch", Checkbox)

            if self.selected_action == "uninstall":
                f_title.update("🎉 EasyCLI Has Been Removed")
                f_sub.update("EasyCLI and its components were successfully removed from your computer.")
                f_card.display = False
                chk_launch.display = False
            else:
                f_title.update("🎉 EasyCLI Setup Completed Successfully!")
                f_sub.update("EasyCLI has been installed and is ready to use in your terminal.")
                f_card.display = True
                chk_launch.display = True

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "action-radios":
            val_id = event.pressed.id
            if val_id in ["act-express", "act-reinstall"]:
                self.selected_action = "install"
            elif val_id == "act-custom":
                self.selected_action = "custom"
            elif val_id == "act-uninstall":
                self.selected_action = "uninstall"
            elif val_id == "act-diagnostics":
                self.selected_action = "diagnostics"
        elif event.radio_set.id == "scope-radios":
            if event.pressed.id == "scope-user":
                self.target_scope = "user"
            else:
                self.target_scope = "system"

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "chk-emoji":
            self.enable_emoji = event.value
        elif event.checkbox.id == "chk-data":
            self.remove_user_data = event.value
        elif event.checkbox.id == "chk-fonts":
            self.remove_fonts = event.value
        elif event.checkbox.id == "chk-launch":
            self.launch_after = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        switcher = self.query_one("#wizard-switcher", ContentSwitcher)
        cur = switcher.current

        if bid == "btn-cancel":
            self.exit()
        elif bid == "btn-back":
            if cur in ["page-custom", "page-uninstall", "page-diagnostics"]:
                self.switch_page("page-welcome")
        elif bid == "btn-next":
            if cur == "page-welcome":
                if self.selected_action == "custom":
                    self.switch_page("page-custom")
                elif self.selected_action == "uninstall":
                    self.switch_page("page-uninstall")
                elif self.selected_action == "diagnostics":
                    self.switch_page("page-diagnostics")
                else:
                    self.switch_page("page-progress")
            elif cur in ["page-custom", "page-uninstall"]:
                self.switch_page("page-progress")
            elif cur == "page-diagnostics":
                self.switch_page("page-welcome")
            elif cur == "page-finish":
                self.exit()
                if self.launch_after and self.selected_action != "uninstall":
                    os.system("ez || true")

    def action_cancel(self) -> None:
        self.exit()

    @work(thread=True)
    def run_install_worker(self) -> None:
        log_w = self.query_one("#progress-log", Log)
        prog_w = self.query_one("#prog-bar", ProgressBar)
        stat_w = self.query_one("#prog-status", Static)

        def step(pct: float, msg: str) -> None:
            self.call_from_thread(prog_w.update, progress=pct)
            self.call_from_thread(stat_w.update, msg)
            self.call_from_thread(log_w.write_line, f"[{time.strftime('%H:%M:%S')}] {msg}")
            time.sleep(0.15)

        try:
            step(15, "Verifying Python 3 runtime...")
            py_ver = platform.python_version()
            step(25, f"Python {py_ver} verified")

            step(40, f"Configuring virtual environment at {VENV_DIR}...")
            EZ_HOME.mkdir(parents=True, exist_ok=True)
            if not VENV_DIR.exists():
                subprocess.run(["python3", "-m", "venv", str(VENV_DIR)], check=True)
            step(50, "Virtual environment active")

            step(65, "Verifying core dependencies (rich, textual)...")
            pip_bin = VENV_DIR / "bin" / "pip"
            subprocess.run([str(pip_bin), "install", "--upgrade", "--quiet", "rich", "textual"], check=False)

            step(75, "Deploying application core files...")
            APP_DIR.mkdir(parents=True, exist_ok=True)

            # Locate source files (local repo or extracted location)
            src_dir = Path(__file__).resolve().parent.parent
            if (src_dir / "ezcli_app").exists() and (src_dir / "ez").exists():
                dest_ezcli = APP_DIR / "ezcli_app"
                if dest_ezcli.exists():
                    shutil.rmtree(dest_ezcli, ignore_errors=True)
                shutil.copytree(src_dir / "ezcli_app", dest_ezcli)
                shutil.copy2(src_dir / "ez", APP_DIR / "ez")
                os.chmod(str(APP_DIR / "ez"), 0o755)

                if (src_dir / "ez-setup.sh").exists():
                    shutil.copy2(src_dir / "ez-setup.sh", EZ_HOME / "ez-setup.sh")
                    os.chmod(str(EZ_HOME / "ez-setup.sh"), 0o755)

            step(85, "Configuring Noto Color Emoji font priorities...")
            if self.enable_emoji:
                user_font_dir = Path.home() / ".config" / "fontconfig" / "conf.d"
                user_font_dir.mkdir(parents=True, exist_ok=True)
                emoji_xml = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <match target="pattern">
    <edit name="family" mode="append" binding="strong">
      <string>Noto Color Emoji</string>
    </edit>
  </match>
  <alias>
    <family>emoji</family>
    <prefer>
      <family>Noto Color Emoji</family>
    </prefer>
  </alias>
</fontconfig>"""
                with open(EMOJI_CONF, "w", encoding="utf-8") as f:
                    f.write(emoji_xml)
                subprocess.run(["fc-cache", "-f", str(user_font_dir)], capture_output=True)

            step(95, "Creating command shortcuts in PATH...")
            target_dir = USER_BIN_DIR if self.target_scope == "user" else SYS_BIN_DIR
            target_dir.mkdir(parents=True, exist_ok=True)

            ez_link = target_dir / "ez"
            setup_link = target_dir / "ez-setup"

            if os.access(str(target_dir), os.W_OK):
                if ez_link.exists() or ez_link.is_symlink():
                    ez_link.unlink(missing_ok=True)
                ez_link.symlink_to(APP_DIR / "ez")
                if (EZ_HOME / "ez-setup.sh").exists():
                    if setup_link.exists() or setup_link.is_symlink():
                        setup_link.unlink(missing_ok=True)
                    setup_link.symlink_to(EZ_HOME / "ez-setup.sh")
            else:
                subprocess.run(["sudo", "ln", "-sf", str(APP_DIR / "ez"), str(ez_link)], check=False)
                if (EZ_HOME / "ez-setup.sh").exists():
                    subprocess.run(["sudo", "ln", "-sf", str(EZ_HOME / "ez-setup.sh"), str(setup_link)], check=False)

            step(100, "Installation finished successfully!")
            time.sleep(0.5)

            self.call_from_thread(self._finish_operation)

        except Exception as e:
            self.call_from_thread(log_w.write_line, f"[bold red]Error: {e}[/bold red]")
            self.call_from_thread(stat_w.update, f"Error: {e}")

    @work(thread=True)
    def run_uninstall_worker(self) -> None:
        log_w = self.query_one("#progress-log", Log)
        prog_w = self.query_one("#prog-bar", ProgressBar)
        stat_w = self.query_one("#prog-status", Static)

        def step(pct: float, msg: str) -> None:
            self.call_from_thread(prog_w.update, progress=pct)
            self.call_from_thread(stat_w.update, msg)
            self.call_from_thread(log_w.write_line, f"[{time.strftime('%H:%M:%S')}] {msg}")
            time.sleep(0.15)

        try:
            step(25, "Removing command symlinks...")
            for bin_dir in [SYS_BIN_DIR, USER_BIN_DIR]:
                for name in ["ez", "ezcli", "ez-setup"]:
                    link = bin_dir / name
                    if link.exists() or link.is_symlink():
                        if os.access(str(bin_dir), os.W_OK):
                            link.unlink(missing_ok=True)
                        else:
                            subprocess.run(["sudo", "rm", "-f", str(link)], check=False)
            step(45, "Command shortcuts removed")

            step(65, "Removing application files...")
            if self.remove_user_data:
                shutil.rmtree(EZ_HOME, ignore_errors=True)
                shutil.rmtree(Path.home() / ".local" / "share" / "ezcli", ignore_errors=True)
                step(85, "Application files and user data wiped")
            else:
                shutil.rmtree(APP_DIR, ignore_errors=True)
                step(85, "Application binaries removed (user history preserved)")

            if self.remove_fonts and EMOJI_CONF.exists():
                EMOJI_CONF.unlink(missing_ok=True)
                subprocess.run(["fc-cache", "-fv", str(EMOJI_CONF.parent)], capture_output=True)
                step(95, "Reverted font configuration")

            step(100, "Uninstallation completed cleanly.")
            time.sleep(0.5)

            self.call_from_thread(self._finish_operation)

        except Exception as e:
            self.call_from_thread(log_w.write_line, f"[bold red]Error: {e}[/bold red]")
            self.call_from_thread(stat_w.update, f"Error: {e}")

    def _finish_operation(self) -> None:
        self.is_installed, self.install_location = detect_installation()
        self.switch_page("page-finish")


def run_setup_app() -> None:
    """Launch the Setup Wizard Textual application."""
    app = SetupWizardApp()
    app.run()


if __name__ == "__main__":
    run_setup_app()
