"""Dedicated Textual TUI Application for Unified Package & Software Information.

Provides a rich App-Store experience with:
- Dual-pane master-detail layout (Software Catalog on left, Deep Specifications on right).
- High-depth inspection: full descriptions, licenses, sizes, categories, dependencies, and official homepages.
- Multi-repository support: inspect and install across APT, Flatpak (Flathub), and Snap.
- Native In-TUI Admin Password Modal (like ez-setup.sh) for seamless elevated installations and removals.
"""

import glob
import os
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual import work  # type: ignore
from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from .collectors import collect_available_updates, collect_installed_packages, run_command_safe
from .elevation import ElevationSession, elevated_package_install, elevated_package_uninstall, is_root
from .package_info import (
    PackageCandidate,
    PackageSourceInfo,
    preview_apt_removal_impact,
    resolve_package_info,
)


def fetch_deep_package_details(candidate: PackageCandidate) -> Dict[str, Any]:
    """Fetch extended metadata (description, license, size, dependencies, category) for a candidate."""
    details: Dict[str, Any] = {
        "version": candidate.primary_version or "N/A",
        "description": candidate.summary or "",
        "license": "Open Source",
        "download_size": "",
        "installed_size": "",
        "category": candidate.nature,
        "maintainer": "",
        "homepage": "",
        "architecture": "all",
        "dependencies": [],
        "commands": [],
        "sources": [],
    }

    # 1. Inspect Flatpak remote or local details if available
    flatpak_source = next((s for s in candidate.sources if s.source_type in ("flathub", "flatpak")), None)
    if flatpak_source and shutil.which("flatpak"):
        app_id = flatpak_source.app_id or candidate.name
        cmd = ["flatpak", "info", app_id] if flatpak_source.is_installed else ["flatpak", "remote-info", "flathub", f"{app_id}//stable"]
        rc, out, _ = run_command_safe(cmd, timeout=3)
        if rc != 0 and not flatpak_source.is_installed:
            rc, out, _ = run_command_safe(["flatpak", "remote-info", "flathub", app_id], timeout=3)

        if rc == 0 and out:
            for line in out.splitlines():
                line_str = line.strip()
                if line_str.startswith("Version:"):
                    details["version"] = line_str.replace("Version:", "").strip()
                elif line_str.startswith("License:"):
                    details["license"] = line_str.replace("License:", "").strip()
                elif line_str.startswith("Download:"):
                    details["download_size"] = line_str.replace("Download:", "").strip()
                elif line_str.startswith("Installed:"):
                    details["installed_size"] = line_str.replace("Installed:", "").strip()
                elif line_str.startswith("Runtime:"):
                    details["dependencies"].append(f"Runtime: {line_str.replace('Runtime:', '').strip()}")
                elif line_str.startswith("Arch:"):
                    details["architecture"] = line_str.replace("Arch:", "").strip()

    # 2. Inspect APT cache / DPKG details if available
    apt_source = next((s for s in candidate.sources if s.source_type in ("dpkg", "apt_store", "apt")), None)
    if apt_source:
        pkg_name = apt_source.name or candidate.name
        rc, out, _ = run_command_safe(["dpkg", "-s", pkg_name] if apt_source.is_installed else ["apt-cache", "show", pkg_name], timeout=2)
        if rc == 0 and out:
            in_desc = False
            desc_lines: List[str] = []
            for line in out.splitlines():
                if line.startswith("Description:"):
                    in_desc = True
                    desc_lines.append(line.replace("Description:", "").strip())
                elif in_desc:
                    if line.startswith(" ") or line.startswith("\t"):
                        desc_lines.append(line.strip().lstrip("."))
                    else:
                        in_desc = False

                if line.startswith("Homepage:"):
                    details["homepage"] = line.replace("Homepage:", "").strip()
                elif line.startswith("Maintainer:"):
                    details["maintainer"] = line.replace("Maintainer:", "").strip()
                elif line.startswith("Section:"):
                    details["category"] = line.replace("Section:", "").strip().title()
                elif line.startswith("Installed-Size:"):
                    size_kb = line.replace("Installed-Size:", "").strip()
                    try:
                        details["installed_size"] = f"{int(size_kb) / 1024:.1f} MB"
                    except ValueError:
                        details["installed_size"] = f"{size_kb} KB"
                elif line.startswith("Size:"):
                    size_b = line.replace("Size:", "").strip()
                    try:
                        details["download_size"] = f"{int(size_b) / (1024 * 1024):.1f} MB"
                    except ValueError:
                        pass
                elif line.startswith("Architecture:"):
                    details["architecture"] = line.replace("Architecture:", "").strip()
                elif line.startswith("Depends:"):
                    dep_raw = line.replace("Depends:", "").strip()
                    for d in dep_raw.split(",")[:8]:
                        clean_d = d.strip().split("(")[0].strip()
                        if clean_d and clean_d not in details["dependencies"]:
                            details["dependencies"].append(clean_d)

            if desc_lines:
                details["description"] = "\n".join(d for d in desc_lines if d).strip()

    # 3. Check desktop file for GUI apps
    desktop_file = next((s.desktop_file for s in candidate.sources if s.desktop_file), "")
    if desktop_file and os.path.isfile(desktop_file):
        try:
            with open(desktop_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("Categories=") and not details["category"]:
                        details["category"] = line.replace("Categories=", "").strip().replace(";", ", ").strip(", ")
                    elif line.startswith("Comment=") and not details["description"]:
                        details["description"] = line.replace("Comment=", "").strip()
        except Exception:
            pass

    # Fallback description
    if not details["description"]:
        details["description"] = candidate.summary or f"{candidate.name} is a software package for Linux systems."

    return details


# ==============================================================================
# In-TUI Elevation Modal Screen
# ==============================================================================

class AdminPasswordModal(ModalScreen[Optional[str]]):
    """Modal dialog for securely requesting sudo password inside the TUI."""

    DEFAULT_CSS = """
    AdminPasswordModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #admin-dialog {
        width: 70;
        max-width: 90%;
        height: auto;
        border: round #388bfd;
        background: #161b22;
        padding: 1 2;
    }
    #admin-title {
        text-style: bold;
        color: #58a6ff;
        text-align: center;
        margin-bottom: 1;
    }
    #admin-desc {
        color: #c9d1d9;
        text-align: center;
        margin-bottom: 1;
    }
    #admin-input {
        margin-bottom: 1;
        border: solid #388bfd;
    }
    #admin-err {
        color: #f85149;
        text-align: center;
        margin-bottom: 1;
        height: 1;
    }
    #admin-toggle-box {
        align: center middle;
        margin-bottom: 1;
        height: 3;
    }
    #admin-toggle-box Button {
        height: 3;
        min-width: 18;
        border: round #30363d;
    }
    #admin-buttons {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #admin-buttons Button {
        margin: 0 1;
        min-width: 16;
        height: 3;
        border: round;
    }
    """

    def __init__(self, action_name: str = "package management") -> None:
        super().__init__()
        self.action_name = action_name

    def compose(self) -> ComposeResult:
        with Vertical(id="admin-dialog"):
            yield Label("🔐 Administrator Rights Required", id="admin-title")
            yield Label(
                f"Administrator privileges are required to perform {self.action_name}.\n"
                "Please enter your sudo password below:",
                id="admin-desc",
            )
            yield Input(placeholder="Enter sudo password...", password=True, id="admin-input")
            yield Label("", id="admin-err")
            with Horizontal(id="admin-toggle-box"):
                yield Button("👁️ Show Password", id="btn-toggle-pwd", variant="default")
            with Horizontal(id="admin-buttons"):
                yield Button("🔐 Authenticate", variant="primary", id="btn-auth")
                yield Button("❌ Cancel", variant="default", id="btn-cancel-auth")

    def on_mount(self) -> None:
        self.query_one("#admin-input", Input).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-toggle-pwd":
            inp = self.query_one("#admin-input", Input)
            if inp.password:
                inp.password = False
                event.button.label = "🙈 Hide Password"
            else:
                inp.password = True
                event.button.label = "👁️ Show Password"
        elif event.button.id == "btn-auth":
            self.submit()
        elif event.button.id == "btn-cancel-auth":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "admin-input":
            self.submit()

    def submit(self) -> None:
        inp = self.query_one("#admin-input", Input)
        pwd = inp.value
        err_lbl = self.query_one("#admin-err", Label)

        if not pwd:
            err_lbl.update("Password cannot be empty.")
            return

        try:
            # Validate with sudo -S -p "" -v (reads password from stdin, no terminal hijacking)
            res = subprocess.run(
                ["sudo", "-S", "-p", "", "-v"],
                input=pwd.encode() + b"\n",
                capture_output=True,
                timeout=10,
            )
            if res.returncode == 0:
                self.dismiss(pwd)
            else:
                err_lbl.update("❌ Incorrect password. Please try again.")
                inp.value = ""
                inp.focus()
        except FileNotFoundError:
            err_lbl.update("❌ 'sudo' command is not available on this system.")
        except Exception as e:
            err_lbl.update(f"❌ Error: {e}")


# ==============================================================================
# Confirmation Modals
# ==============================================================================

class ConfirmUninstallModal(ModalScreen[bool]):
    """Confirmation modal for safely uninstalling an application or package."""

    DEFAULT_CSS = """
    ConfirmUninstallModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #uninstall-dialog {
        width: 74;
        max-width: 90%;
        height: auto;
        border: round #ef4444;
        background: #180d0d;
        padding: 1 2;
    }
    #uninstall-title {
        text-style: bold;
        color: #ef4444;
        text-align: center;
        margin-bottom: 1;
    }
    #uninstall-details {
        color: #f8fafc;
        margin-bottom: 1;
    }
    #uninstall-impact {
        background: #2a1212;
        border: solid #b91c1c;
        padding: 1;
        margin-bottom: 1;
        color: #fca5a5;
    }
    #uninstall-actions {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #uninstall-actions Button {
        margin: 0 1;
        min-width: 18;
        height: 3;
        border: round;
    }
    """

    def __init__(self, candidate: PackageCandidate) -> None:
        super().__init__()
        self.candidate = candidate
        self.source = next((s for s in candidate.sources if s.is_installed), None)

    def compose(self) -> ComposeResult:
        with Vertical(id="uninstall-dialog"):
            yield Label(f"🗑️ Confirm Uninstallation: {self.candidate.name}", id="uninstall-title")
            src_desc = f"{self.source.source_icon} {self.source.source_name}" if self.source else "Local System"
            ver_desc = f"v{self.source.version}" if (self.source and self.source.version) else ""
            details = (
                f"Target Software: [bold white]{self.candidate.name}[/bold white] ({self.candidate.nature})\n"
                f"Source: [bold cyan]{src_desc}[/bold cyan] {ver_desc}\n\n"
                "Personal documents in your home directory will be kept intact.\n"
                "Administrator privileges will be verified before removal."
            )
            yield Label(details, id="uninstall-details")

            impact_text = "• Removes binary executables, desktop icons, and service files."
            if self.source and self.source.source_type == "dpkg":
                try:
                    prev = preview_apt_removal_impact(self.candidate.name)
                    if prev.get("packages_to_remove"):
                        rem = ", ".join(prev["packages_to_remove"][:6])
                        impact_text += f"\n• Packages to remove: [bold]{rem}[/bold]"
                    if prev.get("autoremove_packages"):
                        impact_text += f"\n• Unused dependencies to clean: {len(prev['autoremove_packages'])} packages"
                except Exception:
                    pass

            yield Static(impact_text, id="uninstall-impact")

            with Horizontal(id="uninstall-actions"):
                yield Button("🗑️ Confirm Uninstall", variant="error", id="btn-confirm-uninstall")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-uninstall":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ConfirmInstallModal(ModalScreen[Optional[PackageSourceInfo]]):
    """Confirmation modal for installing an application with repository source selection."""

    DEFAULT_CSS = """
    ConfirmInstallModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #install-dialog {
        width: 76;
        max-width: 90%;
        height: auto;
        border: round #0284c7;
        background: #0c192c;
        padding: 1 2;
    }
    #install-title {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 1;
    }
    #install-details {
        color: #f0f9ff;
        margin-bottom: 1;
    }
    #source-radios {
        background: #112240;
        border: solid #1e3a8a;
        padding: 1;
        margin-bottom: 1;
    }
    #install-actions {
        align: center middle;
        height: auto;
        margin-top: 1;
    }
    #install-actions Button {
        margin: 0 1;
        min-width: 18;
        height: 3;
        border: round;
    }
    """

    def __init__(self, candidate: PackageCandidate, sources: List[PackageSourceInfo]) -> None:
        super().__init__()
        self.candidate = candidate
        self.sources = [s for s in sources if not s.is_installed] or sources

    def compose(self) -> ComposeResult:
        with Vertical(id="install-dialog"):
            yield Label(f"⬇️ Install Software: {self.candidate.name}", id="install-title")
            info = (
                f"Application: [bold white]{self.candidate.name}[/bold white] ({self.candidate.nature})\n"
                f"Choose your preferred software source and format below:"
            )
            yield Label(info, id="install-details")

            with RadioSet(id="source-radios"):
                for idx, src in enumerate(self.sources):
                    label = f"{src.source_icon} {src.source_name} (v{src.version or 'Latest'})"
                    if src.download_size:
                        label += f" - {src.download_size}"
                    yield RadioButton(label, value=(idx == 0), id=f"rad-src-{idx}")

            with Horizontal(id="install-actions"):
                yield Button("⬇️ Install Selected", variant="primary", id="btn-confirm-install")
                yield Button("❌ Cancel", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-install":
            radioset = self.query_one("#source-radios", RadioSet)
            chosen_idx = radioset.pressed_index if radioset.pressed_index is not None and 0 <= radioset.pressed_index < len(self.sources) else 0
            self.dismiss(self.sources[chosen_idx])
        else:
            self.dismiss(None)


# ==============================================================================
# Main Package Info Explorer App
# ==============================================================================

class PackageInfoApp(App[None]):
    """Full-featured interactive TUI application for software inspection and package management."""

    TITLE = "EasyCLI Software & Package Explorer"
    SUB_TITLE = "Visual software catalog, deep specifications, and app store"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("/", "focus_search", "🔍 Search", show=True),
        Binding("l", "action_launch", "🚀 Launch", show=True),
        Binding("i", "action_install", "⬇️ Install", show=True),
        Binding("u", "action_uninstall", "🗑️ Uninstall", show=True),
        Binding("r", "refresh_catalog", "🔄 Refresh", show=True),
    ]

    CSS = """
    Screen {
        background: #090d16;
        color: #e2e8f0;
    }

    #header-area {
        height: auto;
        margin: 0 1 1 1;
        background: #0d1527;
        border: round #1e3a8a;
        padding: 1 1;
    }

    #search-input {
        margin-bottom: 1;
        border: round #38bdf8;
        background: #111e38;
    }

    #filter-bar {
        height: 3;
        align: left middle;
    }

    #filter-bar Button {
        height: 3;
        min-width: 15;
        margin-right: 1;
        border: round #334155;
    }

    .filter-active {
        background: #0284c7;
        color: #ffffff;
        border: round #38bdf8 !important;
        text-style: bold;
    }

    .filter-inactive {
        background: #111e38;
        color: #94a3b8;
        border: round #1e293b !important;
    }

    #main-content {
        height: 1fr;
        margin: 0 1;
    }

    /* Broad, generous Results Div */
    #catalog-pane {
        width: 48%;
        min-width: 44;
        height: 100%;
        margin-right: 1;
        border: round #1e293b;
        background: #0c1220;
        padding: 0 1;
    }

    #catalog-header {
        height: 3;
        content-align: left middle;
        text-style: bold;
        color: #38bdf8;
        border-bottom: solid #334155;
    }

    DataTable {
        height: 1fr;
        border: none;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: #1e293b;
        color: #38bdf8;
    }

    DataTable > .datatable--cursor {
        background: #0369a1;
        color: white;
        text-style: bold;
    }

    /* Deep Details Div */
    #detail-pane {
        width: 52%;
        min-width: 34;
        height: 100%;
        border: round #0284c7;
        background: #0b1120;
        padding: 0 1;
    }

    #detail-scroll {
        height: 100%;
    }

    .detail-card {
        height: auto;
        background: #111a2e;
        border: round #1e293b;
        margin: 0 0 1 0;
        padding: 1 2;
    }

    #hero-card {
        background: #0e1e38;
        border: round #2563eb;
        margin-top: 1;
    }

    #hero-header-row {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }

    #hero-icon {
        margin-right: 1;
        text-style: bold;
    }

    #hero-title {
        text-style: bold;
        color: #60a5fa;
    }

    .card-title {
        text-style: bold;
        color: #60a5fa;
        margin-bottom: 1;
    }

    .card-text {
        color: #f1f5f9;
    }

    #metrics-grid {
        height: auto;
        grid-size: 2 2;
        grid-gutter: 1;
        margin: 0 0 1 0;
    }

    .metric-box {
        background: #111e38;
        border: round #1e3a8a;
        padding: 0 1;
        height: 3;
        content-align: left middle;
    }

    /* Bottom Action Bar with isolated rounded buttons */
    #action-bar {
        height: 4;
        dock: bottom;
        margin: 1 1 0 1;
        padding: 0 1;
        align: center middle;
    }

    #action-bar Button {
        margin: 0 1;
        min-width: 13;
        height: 3;
        border: round;
    }

    #action-bar Button:disabled {
        opacity: 0.4;
        border: round #334155;
    }
    """

    def __init__(self, initial_query: Optional[str] = None) -> None:
        super().__init__()
        self.initial_query = (initial_query or "").strip()
        self.current_filter: str = "all"
        self.candidates: List[PackageCandidate] = []
        self.selected_candidate: Optional[PackageCandidate] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="header-area"):
            yield Input(
                placeholder="🔍 Search software, packages, libraries, or flatpaks (e.g. wine, vlc, git, blender, curl)...",
                id="search-input",
                value=self.initial_query,
            )
            with Horizontal(id="filter-bar"):
                yield Button("🌐 All Items", id="tab-all", classes="filter-active")
                yield Button("📱 Installed Apps", id="tab-installed", classes="filter-inactive")
                yield Button("🏪 Store Catalogs", id="tab-store", classes="filter-inactive")
                yield Button("🔄 Available Updates", id="tab-updates", classes="filter-inactive")

        with Horizontal(id="main-content"):
            with Vertical(id="catalog-pane"):
                yield Label("📦 Software Catalog", id="catalog-header")
                yield DataTable(id="package-table", cursor_type="row")

            with Vertical(id="detail-pane"):
                with VerticalScroll(id="detail-scroll"):
                    # 1. Hero Showcase
                    with Vertical(id="hero-card", classes="detail-card"):
                        with Horizontal(id="hero-header-row"):
                            yield Label("📦", id="hero-icon")
                            yield Label("Select an item to inspect", id="hero-title")
                        yield Static(id="hero-badge")

                    # 2. Key Metrics Grid
                    with Grid(id="metrics-grid"):
                        yield Static("🏷️ Version: [bold]--[/bold]", id="metric-version", classes="metric-box")
                        yield Static("💾 Size: [bold]--[/bold]", id="metric-size", classes="metric-box")
                        yield Static("⚖️ License: [bold]--[/bold]", id="metric-license", classes="metric-box")
                        yield Static("📂 Category: [bold]--[/bold]", id="metric-category", classes="metric-box")

                    # 3. Overview Description
                    with Vertical(id="summary-card", classes="detail-card"):
                        yield Label("📝 About & Overview", classes="card-title")
                        yield Static(id="summary-body", classes="card-text")

                    # 4. Sources & Repositories
                    with Vertical(id="sources-card", classes="detail-card"):
                        yield Label("📦 Available Installation Formats & Repositories", classes="card-title")
                        yield Static(id="sources-body", classes="card-text")

                    # 5. Technical Specifications
                    with Vertical(id="meta-card", classes="detail-card"):
                        yield Label("📋 Technical Specifications", classes="card-title")
                        yield Static(id="meta-body", classes="card-text")

                    # 6. Dependencies
                    with Vertical(id="deps-card", classes="detail-card"):
                        yield Label("🔗 System Dependencies & Runtime", classes="card-title")
                        yield Static(id="deps-body", classes="card-text")

        with Horizontal(id="action-bar"):
            yield Button("🚀 Launch App", variant="success", id="btn-launch")
            yield Button("⬇️ Install Software", variant="primary", id="btn-install")
            yield Button("🗑️ Uninstall", variant="error", id="btn-uninstall")
            yield Button("🔄 Refresh", variant="default", id="btn-refresh")
            yield Button("❌ Close", variant="default", id="btn-close")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#package-table", DataTable)
        table.add_column("Package / App", width=26)
        table.add_column("Status", width=15)
        table.add_column("Source", width=16)

        if self.initial_query:
            self.execute_search(self.initial_query)
        else:
            self.load_default_catalog()

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if q:
            self.execute_search(q)
        else:
            self.load_default_catalog()

    @work(thread=True)
    def load_default_catalog(self) -> None:
        """Load default installed applications and local catalog."""
        self.app.call_from_thread(self._set_catalog_status, "🔄 Scanning local software catalog...")
        try:
            res = collect_installed_packages(filter_term="", category="both")
            matches = res.get("matches", [])
            candidates: List[PackageCandidate] = []
            for m in matches:
                nature, n_icon = ("Desktop App", "🖥️") if m.get("is_app") else ("CLI Tool", "⌨️")
                source_type = m.get("source", "apt").lower()
                source_icon = "📦" if "apt" in source_type else ("🟣" if "flatpak" in source_type else "🟢")
                src_info = PackageSourceInfo(
                    source_type=source_type,
                    source_name=m.get("source", "APT"),
                    source_icon=source_icon,
                    is_installed=True,
                    name=m.get("name", ""),
                    version=m.get("version", ""),
                    summary=m.get("summary", ""),
                    location=m.get("location", ""),
                    desktop_file=m.get("desktop_file", ""),
                )
                candidates.append(
                    PackageCandidate(
                        name=m.get("name", ""),
                        nature=nature,
                        nature_icon=n_icon,
                        is_installed=True,
                        sources=[src_info],
                        summary=m.get("summary", "") or f"{m.get('name')} application",
                        primary_version=m.get("version", ""),
                        match_score=100,
                    )
                )
            self.app.call_from_thread(self._populate_catalog, candidates, "📦 Software Catalog")
        except Exception as e:
            self.app.call_from_thread(self._set_catalog_status, f"Error: {e}")

    @work(thread=True)
    def execute_search(self, query: str) -> None:
        """Perform a multi-source search across local machine and remote stores."""
        self.app.call_from_thread(self._set_catalog_status, f"🔍 Searching catalogs for '{query}'...")
        try:
            candidates, _, _ = resolve_package_info(query)
            self.app.call_from_thread(self._populate_catalog, candidates, f"🔍 Results for '{query}'")
        except Exception as e:
            self.app.call_from_thread(self._set_catalog_status, f"Search failed: {e}")

    @work(thread=True)
    def load_available_updates(self) -> None:
        """Collect and display pending package updates."""
        self.app.call_from_thread(self._set_catalog_status, "🔄 Checking repositories for pending updates...")
        try:
            res = collect_available_updates()
            up_list = res.get("updates", [])
            candidates: List[PackageCandidate] = []
            for u in up_list:
                src_info = PackageSourceInfo(
                    source_type="apt",
                    source_name="APT Update",
                    source_icon="🔄",
                    is_installed=True,
                    name=u.get("package", ""),
                    version=u.get("current_version", ""),
                    download_size=u.get("size", ""),
                )
                candidates.append(
                    PackageCandidate(
                        name=u.get("package", ""),
                        nature="System Update",
                        nature_icon="🔄",
                        is_installed=True,
                        sources=[src_info],
                        summary=f"Update available: {u.get('current_version')} ➔ {u.get('candidate_version')}",
                        primary_version=u.get("candidate_version", ""),
                        match_score=100,
                    )
                )
            self.app.call_from_thread(self._populate_catalog, candidates, "🔄 Available Software Updates")
        except Exception as e:
            self.app.call_from_thread(self._set_catalog_status, f"Updates check failed: {e}")

    def _set_catalog_status(self, text: str) -> None:
        self.query_one("#catalog-header", Label).update(text)

    def _populate_catalog(self, candidates: List[PackageCandidate], header_title: str) -> None:
        seen_names = set()
        deduped: List[PackageCandidate] = []
        for c in candidates:
            if c.name not in seen_names:
                seen_names.add(c.name)
                deduped.append(c)

        self.candidates = deduped
        table = self.query_one("#package-table", DataTable)
        table.clear()

        filtered = self._apply_filter(self.candidates)
        header_lbl = self.query_one("#catalog-header", Label)
        header_lbl.update(f"{header_title} ({len(filtered)} items)")

        for idx, c in enumerate(filtered):
            status_chip = "[bold green]✅ Installed[/bold green]" if c.is_installed else "[bold cyan]🏪 Store[/bold cyan]"
            src_name = c.sources[0].source_name if c.sources else "Local"
            src_chip = f"{c.sources[0].source_icon} {src_name}" if c.sources else "📦 System"
            table.add_row(
                f"{c.nature_icon} {c.name}",
                status_chip,
                src_chip,
                key=str(idx),
            )

        if filtered:
            self.selected_candidate = filtered[0]
            self.update_detail_view(self.selected_candidate)
        else:
            self.clear_detail_view()

    def _apply_filter(self, candidates: List[PackageCandidate]) -> List[PackageCandidate]:
        if self.current_filter == "installed":
            return [c for c in candidates if c.is_installed]
        elif self.current_filter == "store":
            return [c for c in candidates if not c.is_installed]
        return candidates

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is not None:
            key_val = event.row_key.value if hasattr(event.row_key, "value") else str(event.row_key)
            try:
                idx = int(key_val)
                filtered = self._apply_filter(self.candidates)
                if 0 <= idx < len(filtered):
                    self.selected_candidate = filtered[idx]
                    self.update_detail_view(self.selected_candidate)
                    return
            except (ValueError, TypeError):
                pass
            match = next((c for c in self.candidates if c.name == key_val), None)
            if match:
                self.selected_candidate = match
                self.update_detail_view(match)

    def update_detail_view(self, candidate: PackageCandidate) -> None:
        details = fetch_deep_package_details(candidate)

        # 1. Hero Showcase
        self.query_one("#hero-icon", Label).update(candidate.nature_icon)
        self.query_one("#hero-title", Label).update(candidate.name)

        status_text = (
            "[bold green]✅ Currently Installed on System[/bold green]"
            if candidate.is_installed
            else "[bold cyan]🏪 Available in Software Store[/bold cyan]"
        )
        badge_static = self.query_one("#hero-badge", Static)
        badge_static.update(
            f"Nature: [bold yellow]{candidate.nature}[/bold yellow]  •  "
            f"Status: {status_text}  •  "
            f"Version: [bold green]{details['version']}[/bold green]"
        )

        # 2. Metrics Grid
        size_display = details["installed_size"] or details["download_size"] or "Standard"
        self.query_one("#metric-version", Static).update(f"🏷️ Version: [bold cyan]{details['version']}[/bold cyan]")
        self.query_one("#metric-size", Static).update(f"💾 Size: [bold green]{size_display}[/bold green]")
        self.query_one("#metric-license", Static).update(f"⚖️ License: [bold yellow]{details['license']}[/bold yellow]")
        self.query_one("#metric-category", Static).update(f"📂 Category: [bold magenta]{details['category']}[/bold magenta]")

        # 3. Overview Description
        self.query_one("#summary-body", Static).update(details["description"])

        # 4. Sources & Formats Card
        src_blocks = []
        for s in candidate.sources:
            st = "[bold green]Installed[/bold green]" if s.is_installed else "[bold cyan]Store Available[/bold cyan]"
            ver = f"v{s.version}" if s.version else ""
            app_id_info = f" (ID: [dim]{s.app_id}[/dim])" if s.app_id else ""
            src_blocks.append(f"• [bold]{s.source_icon} {s.source_name}[/bold] ({st}) {ver}{app_id_info}")

        self.query_one("#sources-body", Static).update("\n".join(src_blocks) if src_blocks else "[dim]Standard system repository.[/dim]")

        # 5. Technical Specifications
        tech_lines = []
        loc = next((s.location for s in candidate.sources if s.location), "")
        if loc:
            tech_lines.append(f"• [bold cyan]Executable Binary:[/bold cyan] {loc}")
        desktop = next((s.desktop_file for s in candidate.sources if s.desktop_file), "")
        if desktop:
            tech_lines.append(f"• [bold cyan]Desktop Launcher:[/bold cyan] {desktop}")
        if details["architecture"]:
            tech_lines.append(f"• [bold cyan]Architecture:[/bold cyan] {details['architecture']}")
        if details["maintainer"]:
            tech_lines.append(f"• [bold cyan]Maintainer / Packager:[/bold cyan] {details['maintainer']}")
        if details["homepage"]:
            tech_lines.append(f"• [bold cyan]Official Homepage:[/bold cyan] [underline]{details['homepage']}[/underline]")

        self.query_one("#meta-body", Static).update("\n".join(tech_lines) if tech_lines else "[dim]Standard system package.[/dim]")

        # 6. Dependencies
        if details["dependencies"]:
            deps_str = ", ".join(details["dependencies"][:12])
            self.query_one("#deps-body", Static).update(f"[cyan]{deps_str}[/cyan]")
        else:
            self.query_one("#deps-body", Static).update("[dim]Self-contained or base system dependencies.[/dim]")

        # Update action buttons state
        btn_launch = self.query_one("#btn-launch", Button)
        btn_install = self.query_one("#btn-install", Button)
        btn_uninstall = self.query_one("#btn-uninstall", Button)

        btn_launch.disabled = not (candidate.is_installed and candidate.nature in ("Desktop App", "CLI Tool"))
        btn_uninstall.disabled = not candidate.is_installed
        btn_install.disabled = candidate.is_installed

    def clear_detail_view(self) -> None:
        self.query_one("#hero-icon", Label).update("📦")
        self.query_one("#hero-title", Label).update("No Software Item Selected")
        self.query_one("#hero-badge", Static).update("[dim]Type above to search software catalogs or select an item from the left.[/dim]")
        self.query_one("#metric-version", Static).update("🏷️ Version: --")
        self.query_one("#metric-size", Static).update("💾 Size: --")
        self.query_one("#metric-license", Static).update("⚖️ License: --")
        self.query_one("#metric-category", Static).update("📂 Category: --")
        self.query_one("#summary-body", Static).update("")
        self.query_one("#sources-body", Static).update("")
        self.query_one("#meta-body", Static).update("")
        self.query_one("#deps-body", Static).update("")
        self.query_one("#btn-launch", Button).disabled = True
        self.query_one("#btn-install", Button).disabled = True
        self.query_one("#btn-uninstall", Button).disabled = True

    def set_filter_tab(self, filter_name: str) -> None:
        self.current_filter = filter_name
        for tid in ("all", "installed", "store", "updates"):
            btn = self.query_one(f"#tab-{tid}", Button)
            if tid == filter_name:
                btn.remove_class("filter-inactive")
                btn.add_class("filter-active")
            else:
                btn.remove_class("filter-active")
                btn.add_class("filter-inactive")

        if filter_name == "updates":
            self.load_available_updates()
        else:
            self._populate_catalog(self.candidates, "📦 Software Catalog")

    def check_or_request_admin(self, action_name: str, callback: Callable[[Optional[str]], None]) -> None:
        """Verify if admin privileges are available, or present the In-TUI AdminPasswordModal."""
        if is_root() or os.geteuid() == 0:
            callback("")
            return

        res = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        if res.returncode == 0:
            callback("")
            return

        # Prompt password inside TUI modal
        self.push_screen(AdminPasswordModal(action_name), callback)

    def action_launch(self) -> None:
        if not self.selected_candidate or not self.selected_candidate.is_installed:
            self.notify("Selected item is not installed or runnable.", severity="warning")
            return

        name = self.selected_candidate.name
        desktop_file = next((s.desktop_file for s in self.selected_candidate.sources if s.desktop_file), None)
        try:
            if desktop_file and shutil.which("gtk-launch"):
                base_name = os.path.basename(desktop_file).replace(".desktop", "")
                subprocess.Popen(["gtk-launch", base_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                self.notify(f"Launched '{name}' successfully!", severity="information")
                return

            if shutil.which(name):
                subprocess.Popen([name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                self.notify(f"Launched executable '{name}'!", severity="information")
                return

            self.notify(f"Executable for '{name}' was not found on system PATH.", severity="error")
        except Exception as e:
            self.notify(f"Failed to launch '{name}': {e}", severity="error")

    def action_install(self) -> None:
        if not self.selected_candidate:
            return

        candidate = self.selected_candidate
        sources = candidate.sources

        def on_source_chosen(chosen_source: Optional[PackageSourceInfo]) -> None:
            if not chosen_source:
                return

            raw_plat = chosen_source.source_type.lower()
            if raw_plat in ("flathub", "flatpak"):
                plat = "flatpak"
                target_pkg = chosen_source.app_id or candidate.name
            elif raw_plat in ("snap_store", "snap"):
                plat = "snap"
                target_pkg = chosen_source.name
            else:
                plat = "apt"
                target_pkg = chosen_source.name or candidate.name

            def on_admin_ready(pwd: Optional[str]) -> None:
                if pwd is None:
                    self.notify("Installation cancelled: Admin rights were not granted.", title="Cancelled", severity="warning")
                    return
                self.run_install_worker(target_pkg, plat, candidate.name, pwd)

            self.check_or_request_admin(f"installation of '{candidate.name}'", on_admin_ready)

        self.push_screen(ConfirmInstallModal(candidate, sources), on_source_chosen)

    @work(thread=True)
    def run_install_worker(self, target_pkg: str, plat: str, candidate_name: str, pwd: str) -> None:
        self.app.call_from_thread(
            self.notify,
            f"Installing '{candidate_name}' via {plat.upper()}... Please wait.",
            title="Installation In Progress",
            severity="information",
            timeout=8.0,
        )
        self.app.call_from_thread(self._set_catalog_status, f"⏳ Installing '{candidate_name}' ({plat.upper()})...")

        try:
            with ElevationSession(password=pwd):
                ok = elevated_package_install(
                    platform=plat,
                    package=target_pkg,
                    skip_explanation=True,
                )

            if ok:
                self.app.call_from_thread(
                    self.notify,
                    f"Successfully installed '{candidate_name}'!",
                    title="Installation Complete",
                    severity="information",
                )
                self.app.call_from_thread(self.action_refresh_catalog)
            else:
                self.app.call_from_thread(
                    self.notify,
                    f"Installation failed: could not install '{target_pkg}'.",
                    title="Install Failed",
                    severity="error",
                )
                self.app.call_from_thread(self._set_catalog_status, f"❌ Install failed for '{candidate_name}'.")
        except Exception as e:
            self.app.call_from_thread(
                self.notify,
                f"Error installing '{target_pkg}': {e}",
                title="Error",
                severity="error",
            )
            self.app.call_from_thread(self._set_catalog_status, f"Error: {e}")

    def action_uninstall(self) -> None:
        if not self.selected_candidate or not self.selected_candidate.is_installed:
            return

        candidate = self.selected_candidate

        def on_uninstall_confirmed(proceed: bool) -> None:
            if not proceed:
                return

            inst_src = next((s for s in candidate.sources if s.is_installed), None)
            raw_plat = (inst_src.source_type if inst_src else "apt").lower()
            if raw_plat in ("flathub", "flatpak"):
                plat = "flatpak"
                target_pkg = (inst_src.app_id if inst_src else None) or candidate.name
            elif raw_plat in ("snap_store", "snap"):
                plat = "snap"
                target_pkg = (inst_src.name if inst_src else None) or candidate.name
            else:
                plat = "apt"
                target_pkg = (inst_src.name if inst_src else None) or candidate.name

            def on_admin_ready(pwd: Optional[str]) -> None:
                if pwd is None:
                    self.notify("Uninstallation cancelled: Admin rights were not granted.", title="Cancelled", severity="warning")
                    return
                self.run_uninstall_worker(target_pkg, plat, candidate.name, pwd)

            self.check_or_request_admin(f"uninstallation of '{candidate.name}'", on_admin_ready)

        self.push_screen(ConfirmUninstallModal(candidate), on_uninstall_confirmed)

    @work(thread=True)
    def run_uninstall_worker(self, target_pkg: str, plat: str, candidate_name: str, pwd: str) -> None:
        self.app.call_from_thread(
            self.notify,
            f"Uninstalling '{candidate_name}'... Please wait.",
            title="Uninstall In Progress",
            severity="information",
            timeout=8.0,
        )
        self.app.call_from_thread(self._set_catalog_status, f"⏳ Removing '{candidate_name}'...")

        try:
            with ElevationSession(password=pwd):
                ok, _, err = elevated_package_uninstall(
                    platform=plat,
                    package=target_pkg,
                    skip_explanation=True,
                )

            if ok:
                self.app.call_from_thread(
                    self.notify,
                    f"Successfully uninstalled '{candidate_name}'!",
                    title="Uninstall Complete",
                    severity="information",
                )
                self.app.call_from_thread(self.action_refresh_catalog)
            else:
                self.app.call_from_thread(
                    self.notify,
                    f"Uninstallation failed: {err}",
                    title="Uninstall Failed",
                    severity="error",
                )
                self.app.call_from_thread(self._set_catalog_status, f"❌ Removal failed: {err}")
        except Exception as e:
            self.app.call_from_thread(
                self.notify,
                f"Error uninstalling '{target_pkg}': {e}",
                title="Error",
                severity="error",
            )
            self.app.call_from_thread(self._set_catalog_status, f"Error: {e}")

    def action_refresh_catalog(self) -> None:
        q = self.query_one("#search-input", Input).value.strip()
        if q:
            self.execute_search(q)
        else:
            self.load_default_catalog()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "tab-all":
            self.set_filter_tab("all")
        elif btn_id == "tab-installed":
            self.set_filter_tab("installed")
        elif btn_id == "tab-store":
            self.set_filter_tab("store")
        elif btn_id == "tab-updates":
            self.set_filter_tab("updates")
        elif btn_id == "btn-launch":
            self.action_launch()
        elif btn_id == "btn-install":
            self.action_install()
        elif btn_id == "btn-uninstall":
            self.action_uninstall()
        elif btn_id == "btn-refresh":
            self.action_refresh_catalog()
        elif btn_id == "btn-close":
            self.exit()
