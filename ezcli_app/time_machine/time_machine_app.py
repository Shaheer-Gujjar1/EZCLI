"""
Interactive Textual TUI for EasyCLI Time Machine ('ez time-machine').

Provides a mini Timeshift-like visual system restore point manager:
- Timeline DataTable of snapshots with profile badges, human sizes, and comments
- Create restore point modal ('c') with System Configs vs Full Root options
- Safe restore modal ('r') with pre-flight simulation and explicit confirmation
- Delete restore point modal ('d')
- Browse snapshot files ('b')
- Comprehensive inspector modal ('Enter' / 'i')
- Live storage usage stats and system metrics
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Horizontal, Vertical, VerticalScroll  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    RadioSet,
    RadioButton,
    Static,
)

from .snapshot_engine import (
    SnapshotMetadata,
    format_human_size,
    get_base_dir,
    get_snapshots_dir,
    list_local_snapshots,
    get_storage_stats,
)


# ==============================================================================
# Modal Dialogs
# ==============================================================================

class CreateSnapshotModal(ModalScreen[Optional[Dict[str, str]]]):
    """Modal dialog to create a new system restore point."""

    DEFAULT_CSS = """
    CreateSnapshotModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #create-dialog {
        width: 72;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $accent;
        padding: 1 2;
    }
    .modal-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .modal-desc {
        color: $text-muted;
        margin-bottom: 1;
    }
    #comment-input {
        margin-bottom: 1;
    }
    #profile-radioset {
        margin-bottom: 1;
        background: transparent;
        border: none;
    }
    #btn-bar {
        margin-top: 1;
        align: right middle;
        height: 4;
    }
    #btn-bar Button {
        margin-left: 1;
        height: 3;
    }
    """

    def on_mount(self) -> None:
        self.query_one("#comment-input", Input).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Container(id="create-dialog"):
            yield Label("🕒 Create System Restore Point", classes="modal-title")
            yield Label(
                "Time Machine uses rsync hardlinks to snapshot your system with minimal disk space.",
                classes="modal-desc",
            )
            yield Label("Restore Point Description / Comment:")
            yield Input(
                placeholder="e.g., Before installing graphics driver or system update",
                id="comment-input",
            )
            yield Label("Snapshot Scope & Profile:")
            with RadioSet(id="profile-radioset"):
                yield RadioButton(
                    "⚡ System Configs & State (Fast, ~50MB: /etc, /usr/local, dpkg, grub)",
                    value=True,
                    id="radio-config",
                )
                yield RadioButton(
                    "🖥️ Full System Root (Complete filesystem snapshot, excluding /home)",
                    value=False,
                    id="radio-system",
                )
            with Horizontal(id="btn-bar"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Create Restore Point", variant="primary", id="btn-submit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-submit":
            comment_input = self.query_one("#comment-input", Input)
            radio_config = self.query_one("#radio-config", RadioButton)
            comment = comment_input.value.strip()
            profile = "config" if radio_config.value else "system"
            self.dismiss({"comment": comment, "profile": profile})

    def on_input_submitted(self, event: Input.Submitted) -> None:
        radio_config = self.query_one("#radio-config", RadioButton)
        comment = event.value.strip()
        profile = "config" if radio_config.value else "system"
        self.dismiss({"comment": comment, "profile": profile})


class RestoreSnapshotModal(ModalScreen[bool]):
    """High-contrast safety modal to confirm system rollback."""

    DEFAULT_CSS = """
    RestoreSnapshotModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }
    #restore-dialog {
        width: 76;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $error;
        padding: 1 2;
    }
    .warn-title {
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    .warn-box {
        background: rgba(255, 0, 0, 0.1);
        border: round $error;
        padding: 1 2;
        margin-bottom: 1;
    }
    #btn-bar {
        margin-top: 1;
        align: right middle;
        height: 4;
    }
    #btn-bar Button {
        margin-left: 1;
        height: 3;
    }
    """

    def __init__(self, snapshot: SnapshotMetadata) -> None:
        super().__init__()
        self.snapshot = snapshot

    def on_mount(self) -> None:
        self.query_one("#btn-cancel", Button).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)

    def compose(self) -> ComposeResult:
        with Container(id="restore-dialog"):
            yield Label("⚠️ System Restore Confirmation", classes="warn-title")
            with Container(classes="warn-box"):
                yield Label(f"Target Restore Point: [bold cyan]{self.snapshot.id}[/bold cyan]")
                yield Label(f"Profile: [bold yellow]{self.snapshot.profile.upper()}[/bold yellow] · Created: [dim]{self.snapshot.created_at}[/dim]")
                yield Label(f"Comment: {self.snapshot.comment or '(none)'}\n")
                yield Label(
                    "[bold red]WARNING:[/bold red] Restoring will overwrite current system files with this snapshot's state."
                )
                yield Label(
                    "✔ [green]Your personal files in /home are completely safe and untouched.[/green]"
                )
            with Horizontal(id="btn-bar"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Proceed with Restore", variant="error", id="btn-confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class DeleteSnapshotModal(ModalScreen[bool]):
    """Modal to confirm snapshot deletion."""

    DEFAULT_CSS = """
    DeleteSnapshotModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #delete-dialog {
        width: 65;
        height: auto;
        background: $surface;
        border: round $warning;
        padding: 1 2;
    }
    .modal-title {
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    #btn-bar {
        margin-top: 1;
        align: right middle;
        height: 4;
    }
    #btn-bar Button {
        margin-left: 1;
        height: 3;
    }
    """

    def __init__(self, snapshot: SnapshotMetadata) -> None:
        super().__init__()
        self.snapshot = snapshot

    def on_mount(self) -> None:
        self.query_one("#btn-cancel", Button).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)

    def compose(self) -> ComposeResult:
        with Container(id="delete-dialog"):
            yield Label("🗑️ Delete Restore Point", classes="modal-title")
            yield Label(
                f"Are you sure you want to delete restore point [bold cyan]{self.snapshot.id}[/bold cyan]?"
            )
            yield Label(f"[dim]{self.snapshot.comment}[/dim]\n")
            yield Label(
                "[dim]Thanks to hardlinks, deleting this snapshot will free unique data while keeping all other restore points safe.[/dim]"
            )
            with Horizontal(id="btn-bar"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Delete Restore Point", variant="error", id="btn-delete")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-delete":
            self.dismiss(True)
        else:
            self.dismiss(False)


class SnapshotDetailsModal(ModalScreen[Optional[str]]):
    """Modal showing comprehensive restore point inspection card."""

    DEFAULT_CSS = """
    SnapshotDetailsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    #details-dialog {
        width: 74;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: round $primary;
        padding: 1 2;
    }
    .modal-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    .detail-row {
        margin-bottom: 1;
    }
    #btn-bar {
        margin-top: 1;
        align: right middle;
        height: 4;
    }
    #btn-bar Button {
        margin-left: 1;
        height: 3;
    }
    """

    def __init__(self, snapshot: SnapshotMetadata) -> None:
        super().__init__()
        self.snapshot = snapshot

    def on_mount(self) -> None:
        self.query_one("#btn-close", Button).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Container(id="details-dialog"):
            yield Label(f"🕒 Restore Point Details: {self.snapshot.id}", classes="modal-title")
            with Vertical(classes="detail-row"):
                yield Label(f"[bold]Timestamp:[/bold] {self.snapshot.created_at}")
                yield Label(f"[bold]Profile:[/bold] {'⚡ System Configs & State' if self.snapshot.profile == 'config' else '🖥️ Full System Root'}")
                yield Label(f"[bold]Description:[/bold] {self.snapshot.comment or 'Manual restore point'}")
                yield Label(f"[bold]Size:[/bold] {format_human_size(self.snapshot.size_bytes)} ({self.snapshot.size_bytes:,} bytes)")
                yield Label(f"[bold]Distribution:[/bold] {self.snapshot.distro}")
                yield Label(f"[bold]Kernel:[/bold] {self.snapshot.kernel}")
                yield Label(f"[bold]Installed Packages:[/bold] {self.snapshot.packages_count:,} packages")
                yield Label(f"[bold]Storage Path:[/bold] {get_snapshots_dir() / self.snapshot.id}")
            with Horizontal(id="btn-bar"):
                yield Button("⏪ Restore This Point", variant="warning", id="btn-details-restore")
                yield Button("Close", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-details-restore":
            self.dismiss("restore")
        else:
            self.dismiss(None)


# ==============================================================================
# Main Time Machine Application
# ==============================================================================

class TimeMachineApp(App[None]):
    """Textual TUI for EasyCLI Time Machine."""

    TITLE = "EasyCLI Time Machine"
    SUB_TITLE = "System Restore Points & Snapshot Manager"

    BINDINGS = [
        Binding("c", "action_create", "Create", show=True),
        Binding("r", "action_restore", "Restore", show=True),
        Binding("d", "action_delete", "Delete", show=True),
        Binding("b", "action_browse", "Browse", show=True),
        Binding("enter", "action_details", "Details", show=True),
        Binding("i", "action_details", "Details", show=False),
        Binding("f5", "action_refresh", "Refresh", show=True),
        Binding("q", "action_quit", "Quit", show=True),
        Binding("escape", "action_quit", "Quit", show=False),
    ]

    DEFAULT_CSS = """
    Screen {
        background: $surface;
        layout: vertical;
    }
    #top-bar {
        height: 4;
        background: $surface-darken-1;
        border-bottom: solid $primary;
        padding: 0 1;
        layout: horizontal;
    }
    .stat-card {
        width: 1fr;
        height: 100%;
        align: center middle;
        padding: 0 1;
    }
    .stat-label {
        color: $text-muted;
        text-align: center;
        text-style: bold;
    }
    .stat-value {
        color: $accent;
        text-align: center;
        text-style: bold;
    }
    #main-container {
        height: 1fr;
        padding: 1;
    }
    #snapshots-table {
        height: 100%;
        border: round $primary-darken-2;
    }
    #status-banner {
        height: 1;
        background: $surface-darken-2;
        color: $text-muted;
        padding: 0 1;
    }
    #empty-state {
        height: 100%;
        align: center middle;
        padding: 2;
    }
    .empty-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #btn-create-first {
        margin-top: 1;
        height: 3;
    }
    #action-bar {
        height: 4;
        background: $surface-darken-1;
        border-top: solid $primary-darken-2;
        padding: 0 1;
        align: left middle;
        overflow-x: auto;
        overflow-y: hidden;
    }
    #action-bar Button {
        margin-right: 1;
        height: 3;
        min-width: 4;
        padding: 0 1;
    }
    """

    def __init__(self, snapshots_dir: Optional[Path] = None) -> None:
        super().__init__()
        self.snapshots_dir = snapshots_dir or get_snapshots_dir()
        self.snapshots: List[SnapshotMetadata] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="top-bar"):
            with Vertical(classes="stat-card"):
                yield Label("STORAGE BACKUP", classes="stat-label")
                yield Label(str(self.snapshots_dir), id="lbl-storage", classes="stat-value")
            with Vertical(classes="stat-card"):
                yield Label("FREE DISK SPACE", classes="stat-label")
                yield Label("Checking...", id="lbl-free-space", classes="stat-value")
            with Vertical(classes="stat-card"):
                yield Label("RESTORE POINTS", classes="stat-label")
                yield Label("0 snapshots", id="lbl-total-count", classes="stat-value")
            with Vertical(classes="stat-card"):
                yield Label("LATEST BACKUP", classes="stat-label")
                yield Label("None", id="lbl-latest-date", classes="stat-value")
        with Container(id="main-container"):
            yield DataTable(id="snapshots-table", cursor_type="row")
            with Container(id="empty-state"):
                yield Label("🕒 No Restore Points Found", classes="empty-title")
                yield Label(
                    "You have not created any system restore points yet.\nClick below or press [bold cyan]c[/bold cyan] to create your first safe restore point.",
                )
                yield Button("➕ Create System Restore Point", variant="primary", id="btn-create-first")
        with Horizontal(id="action-bar"):
            yield Button("➕ Create (c)", variant="primary", id="btn-create")
            yield Button("⏪ Restore (r)", variant="warning", id="btn-restore")
            yield Button("🗑️ Delete (d)", variant="error", id="btn-delete")
            yield Button("📂 Browse (b)", variant="default", id="btn-browse")
            yield Button("📄 Details (Enter)", variant="default", id="btn-details")
            yield Button("🔄 Refresh (F5)", variant="default", id="btn-refresh")
            yield Button("❌ Quit (q)", variant="default", id="btn-quit")
        yield Static(
            "Ready · Click any action button or press hotkeys...",
            id="status-banner",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#snapshots-table", DataTable)
        table.add_columns("Tag", "Restore Point ID", "Scope / Type", "Description / Comment", "Size")
        self.refresh_snapshots()

    def update_status(self, text: str) -> None:
        banner = self.query_one("#status-banner", Static)
        banner.update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid in ["btn-create", "btn-create-first"]:
            self.action_create()
        elif bid == "btn-restore":
            self.action_restore()
        elif bid == "btn-delete":
            self.action_delete()
        elif bid == "btn-browse":
            self.action_browse()
        elif bid == "btn-details":
            self.action_details()
        elif bid == "btn-refresh":
            self.action_refresh()
        elif bid == "btn-quit":
            self.action_quit()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Double-clicking or pressing Enter on a row opens details modal."""
        self.action_details()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update status line when navigating or clicking on a row."""
        selected = self.get_selected_snapshot()
        if selected:
            self.update_status(f"Selected restore point: {selected.id} · {selected.comment or '(no description)'}")

    def refresh_snapshots(self) -> None:
        """Reload snapshots list from disk and update top stats."""
        from .snapshot_engine import list_local_snapshots, get_storage_stats
        self.snapshots = list_local_snapshots(self.snapshots_dir)

        # Update table
        table = self.query_one("#snapshots-table", DataTable)
        empty_box = self.query_one("#empty-state", Container)
        table.clear()

        has_items = bool(self.snapshots)
        if has_items:
            empty_box.display = False
            table.display = True
            for s in self.snapshots:
                tag = "⚡ Configs" if s.profile == "config" else "🖥️ Full Root"
                table.add_row(
                    tag,
                    s.id,
                    s.profile.upper(),
                    s.comment or "Restore point",
                    format_human_size(s.size_bytes),
                    key=s.id,
                )
        else:
            table.display = False
            empty_box.display = True

        # Update buttons enabled/disabled state based on whether items exist
        for btn_id in ["#btn-restore", "#btn-delete", "#btn-browse", "#btn-details"]:
            try:
                self.query_one(btn_id, Button).disabled = not has_items
            except Exception:
                pass

        # Update stats
        stats = get_storage_stats(get_base_dir())
        self.query_one("#lbl-free-space", Label).update(f"{stats.get('avail_human', '-')} available")
        self.query_one("#lbl-total-count", Label).update(f"{len(self.snapshots)} snapshot{'s' if len(self.snapshots) != 1 else ''}")
        latest_date = self.snapshots[0].created_at if self.snapshots else "None"
        self.query_one("#lbl-latest-date", Label).update(latest_date)

    def get_selected_snapshot(self) -> Optional[SnapshotMetadata]:
        table = self.query_one("#snapshots-table", DataTable)
        if not self.snapshots or table.cursor_row is None:
            return None
        idx = table.cursor_row
        if 0 <= idx < len(self.snapshots):
            return self.snapshots[idx]
        return None

    def action_create(self) -> None:
        """Open create restore point modal."""
        def handle_create(res: Optional[Dict[str, str]]) -> None:
            if not res:
                return
            comment = res.get("comment", "")
            profile = res.get("profile", "config")
            self.update_status(f"Creating restore point ({profile})...")
            
            from ..elevation import elevated_tm_create
            from rich.console import Console
            c = Console()
            ok, meta, err = elevated_tm_create(comment=comment, profile=profile, console=c)
            if ok:
                self.update_status(f"✔ Restore point created successfully!")
            else:
                self.update_status(f"❌ Failed creating restore point: {err}")
            self.refresh_snapshots()

        self.push_screen(CreateSnapshotModal(), handle_create)

    def action_restore(self) -> None:
        """Open restore modal for selected snapshot."""
        selected = self.get_selected_snapshot()
        if not selected:
            self.update_status("No restore point selected to restore.")
            return

        def handle_restore(confirmed: bool) -> None:
            if not confirmed:
                self.update_status("Restore cancelled.")
                return
            self.update_status(f"Restoring system to {selected.id}...")
            from ..elevation import elevated_tm_restore
            from rich.console import Console
            c = Console()
            ok, msg = elevated_tm_restore(snapshot_id=selected.id, console=c)
            if ok:
                self.update_status(f"✔ {msg}")
            else:
                self.update_status(f"❌ Restore failed: {msg}")

        self.push_screen(RestoreSnapshotModal(selected), handle_restore)

    def action_delete(self) -> None:
        """Open delete confirmation modal."""
        selected = self.get_selected_snapshot()
        if not selected:
            self.update_status("No restore point selected to delete.")
            return

        def handle_delete(confirmed: bool) -> None:
            if not confirmed:
                return
            self.update_status(f"Deleting restore point {selected.id}...")
            from ..elevation import elevated_tm_delete
            from rich.console import Console
            c = Console()
            ok, msg = elevated_tm_delete(snapshot_id=selected.id, console=c)
            if ok:
                self.update_status(f"✔ {msg}")
            else:
                self.update_status(f"❌ Delete failed: {msg}")
            self.refresh_snapshots()

        self.push_screen(DeleteSnapshotModal(selected), handle_delete)

    def action_browse(self) -> None:
        """Browse files inside the selected snapshot."""
        selected = self.get_selected_snapshot()
        if not selected:
            self.update_status("No restore point selected to browse.")
            return
        snapshot_data_dir = self.snapshots_dir / selected.id / "data"
        if not snapshot_data_dir.exists():
            self.update_status(f"Snapshot data directory '{snapshot_data_dir}' not found.")
            return

        # Launch file explorer inside snapshot data directory
        self.exit(str(snapshot_data_dir))

    def action_details(self) -> None:
        """Show details modal for selected snapshot."""
        selected = self.get_selected_snapshot()
        if not selected:
            return

        def handle_details_result(res: Optional[str]) -> None:
            if res == "restore":
                self.action_restore()

        self.push_screen(SnapshotDetailsModal(selected), handle_details_result)

    def action_refresh(self) -> None:
        self.refresh_snapshots()
        self.update_status("Refreshed restore points list.")

    def action_quit(self) -> None:
        self.exit(None)


def run_time_machine_app(snapshots_dir: Optional[Path] = None) -> Optional[str]:
    """Launch the Time Machine TUI application."""
    app = TimeMachineApp(snapshots_dir=snapshots_dir)
    browse_target = app.run()
    return browse_target if isinstance(browse_target, str) else None
