"""
Interactive TUI Directory Inspector for 'ez list choose-directory'.

Features:
- 't': Toggle between Flat List view (DataTable) and Tree view (Tree)
- 's': Cycle sorting by Name (A-Z) -> Size (largest first) -> Date (newest first)
- 'h': Toggle hidden files on/off
- 'Enter': Open details card modal (stat replacement with plain English permissions)
- Empty folder friendly message
- Loading status indicator
"""

import datetime
import grp
import os
import pwd
import stat
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
    Label,
    LoadingIndicator,
    Static,
    Tree,
)

from .explorer.file_icons import get_file_icon
from .list_cli import (
    calculate_dir_size,
    format_human_size,
    format_permissions_english,
    format_timestamp,
    scan_directory_entries,
)


# ==============================================================================
# Item Details Modal (Stat Replacement)
# ==============================================================================

class ItemDetailsModal(ModalScreen[None]):
    """Modal dialog displaying comprehensive stat details for an entry."""

    DEFAULT_CSS = """
    ItemDetailsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #details-dialog {
        width: 75;
        max-height: 85%;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    #details-title {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }
    .details-row {
        height: auto;
        margin-bottom: 1;
    }
    .details-key {
        width: 20;
        color: bold yellow;
    }
    .details-val {
        width: 1fr;
        color: white;
    }
    .details-perm {
        color: bold green;
    }
    #details-btn-bar {
        align: center middle;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close", show=True),
        Binding("enter", "dismiss_modal", "Close", show=False),
        Binding("q", "dismiss_modal", "Close", show=False),
    ]

    def __init__(self, item_path: str) -> None:
        super().__init__()
        self.item_path = item_path

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        path_obj = Path(self.item_path)
        name = path_obj.name or self.item_path
        is_dir = os.path.isdir(self.item_path)
        icon = get_file_icon(name, is_dir=is_dir)

        try:
            st = os.lstat(self.item_path)
            size_bytes = st.st_size
            if is_dir:
                size_str = format_human_size(calculate_dir_size(self.item_path, max_items=2000))
            else:
                size_str = f"{format_human_size(size_bytes)} ({size_bytes:,} bytes)"

            ctime_str = format_timestamp(st.st_ctime)
            mtime_str = format_timestamp(st.st_mtime)
            atime_str = format_timestamp(st.st_atime)

            # Plain English Permissions
            eng_perms = format_permissions_english(st)
            octal_perms = oct(st.st_mode & 0o777)
            symbolic_perms = stat.filemode(st.st_mode)

            # Owner and Group
            try:
                owner = pwd.getpwuid(st.st_uid).pw_name
            except Exception:
                owner = str(st.st_uid)
            try:
                group = grp.getgrgid(st.st_gid).gr_name
            except Exception:
                group = str(st.st_gid)

            owner_info = f"{owner} (UID: {st.st_uid}) · Group: {group} (GID: {st.st_gid})"

        except Exception as e:
            size_str = "Unknown"
            ctime_str = mtime_str = atime_str = "Unknown"
            eng_perms = f"Error reading stat: {e}"
            octal_perms = symbolic_perms = "-"
            owner_info = "-"

        type_label = "Directory" if is_dir else ("Symbolic Link" if os.path.islink(self.item_path) else "File")

        with Vertical(id="details-dialog"):
            yield Label(f"{icon} {name} ─ Detailed Information", id="details-title")
            with VerticalScroll():
                with Horizontal(classes="details-row"):
                    yield Label("Full Path:", classes="details-key")
                    yield Label(self.item_path, classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Type:", classes="details-key")
                    yield Label(f"{icon} {type_label}", classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Size:", classes="details-key")
                    yield Label(size_str, classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Created / Changed:", classes="details-key")
                    yield Label(ctime_str, classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Last Modified:", classes="details-key")
                    yield Label(mtime_str, classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Last Accessed:", classes="details-key")
                    yield Label(atime_str, classes="details-val")

                with Horizontal(classes="details-row"):
                    yield Label("Permissions:", classes="details-key")
                    yield Label(f"{eng_perms}\n[dim]({octal_perms} / {symbolic_perms})[/dim]", classes="details-val details-perm")

                with Horizontal(classes="details-row"):
                    yield Label("Ownership:", classes="details-key")
                    yield Label(owner_info, classes="details-val")

            with Horizontal(id="details-btn-bar"):
                yield Button("Close (Esc)", variant="primary", id="btn-close-details")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-details":
            self.dismiss(None)


# ==============================================================================
# Main Interactive TUI Application
# ==============================================================================

class ListInspectorApp(App):
    """Modern interactive directory list and tree inspector for EasyCLI."""

    TITLE = "EasyCLI Directory Inspector"
    SUB_TITLE = "Modern Replacement for ls, tree, du, and stat"

    CSS = """
    Screen {
        background: $surface;
    }
    #status-bar {
        dock: top;
        height: 3;
        background: $surface-darken-1;
        border-bottom: heavy cyan;
        padding: 0 1;
        content-align: left middle;
    }
    #content-container {
        height: 1fr;
        width: 1fr;
    }
    #entries-table {
        height: 1fr;
        width: 1fr;
    }
    #entries-tree {
        height: 1fr;
        width: 1fr;
        display: none;
    }
    #empty-msg {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        color: yellow;
        display: none;
    }
    #loading-box {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-align: center;
        display: none;
    }
    """

    BINDINGS = [
        Binding("t", "toggle_view", "Toggle View [t]", show=True),
        Binding("s", "cycle_sort", "Cycle Sort [s]", show=True),
        Binding("h", "toggle_hidden", "Toggle Hidden [h]", show=True),
        Binding("enter", "show_details", "Details Card [Enter]", show=True),
        Binding("r", "refresh_view", "Refresh [r]", show=True),
        Binding("q", "quit", "Quit [q]", show=True),
        Binding("escape", "quit", "Quit [Esc]", show=False),
    ]

    def __init__(self, target_dir: str) -> None:
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)
        self.view_mode: str = "flat"  # "flat" or "tree"
        self.sort_mode: str = "name"  # "name", "size", "date"
        self.show_hidden: bool = True
        self.entries: List[Dict[str, Any]] = []
        self.tree_initialized: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="status-bar")
        with Container(id="content-container"):
            yield DataTable(id="entries-table", cursor_type="row")
            yield Tree(f"📁 {self.target_dir}", id="entries-tree", data=self.target_dir)
            yield Static(id="empty-msg")
            with Vertical(id="loading-box"):
                yield LoadingIndicator()
                yield Label("⏳ Loading directory contents...")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#entries-table", DataTable)
        table.add_column("Type", width=6)
        table.add_column("Name", width=34)
        table.add_column("Size", width=14)
        table.add_column("Modified", width=18)
        table.add_column("Classification", width=16)

        self.load_directory()

    def update_status_bar(self) -> None:
        status = self.query_one("#status-bar", Static)
        view_label = "[bold cyan]List[/bold cyan]" if self.view_mode == "flat" else "[bold magenta]Tree[/bold magenta]"

        if self.sort_mode == "name":
            sort_label = "[bold green]Name (A-Z)[/bold green]"
        elif self.sort_mode == "size":
            sort_label = "[bold green]Size (Largest)[/bold green]"
        else:
            sort_label = "[bold green]Date (Newest)[/bold green]"

        hidden_label = "[bold yellow]Visible[/bold yellow]" if self.show_hidden else "[dim]Hidden[/dim]"

        file_count = sum(1 for e in self.entries if not e["is_dir"])
        dir_count = sum(1 for e in self.entries if e["is_dir"])

        text = (
            f"[bold white]📁 {self.target_dir}[/bold white]  "
            f"[dim]({len(self.entries)} items: {dir_count} folders, {file_count} files)[/dim]\n"
            f"View: {view_label}  ·  Sort: {sort_label}  ·  Hidden Files: {hidden_label}  ·  "
            f"[dim]Press [bold cyan]Enter[/bold cyan] for Stat Details[/dim]"
        )
        status.update(text)

    def load_directory(self) -> None:
        """Scan directory and populate the current active view."""
        loading = self.query_one("#loading-box", Vertical)
        empty_msg = self.query_one("#empty-msg", Static)
        table = self.query_one("#entries-table", DataTable)
        tree = self.query_one("#entries-tree", Tree)

        loading.display = True
        table.display = False
        tree.display = False
        empty_msg.display = False

        success, raw_entries, err = scan_directory_entries(
            self.target_dir,
            show_hidden=self.show_hidden,
        )

        loading.display = False

        if not success:
            empty_msg.update(f"[bold red]❌ Cannot access directory:[/bold red] {err}")
            empty_msg.display = True
            self.entries = []
            self.update_status_bar()
            return

        self.entries = raw_entries

        # Apply active sorting
        self.apply_sorting()

        if not self.entries:
            empty_msg.update(
                f"[bold yellow]📁 Folder is empty:[/bold yellow] {self.target_dir}\n\n"
                "[dim]No matching files or folders found.[/dim]"
            )
            empty_msg.display = True
            self.update_status_bar()
            return

        if self.view_mode == "flat":
            self.render_flat_table()
        else:
            self.render_tree_view()

        self.update_status_bar()

    def apply_sorting(self) -> None:
        """Sort entries list according to self.sort_mode."""
        if self.sort_mode == "name":
            self.entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        elif self.sort_mode == "size":
            self.entries.sort(key=lambda e: (not e["is_dir"], -(e.get("size") or 0), e["name"].lower()))
        elif self.sort_mode == "date":
            self.entries.sort(key=lambda e: (not e["is_dir"], -(e.get("mtime") or 0), e["name"].lower()))

    def render_flat_table(self) -> None:
        """Populate the DataTable widget with entries."""
        table = self.query_one("#entries-table", DataTable)
        tree = self.query_one("#entries-tree", Tree)
        empty_msg = self.query_one("#empty-msg", Static)

        tree.display = False
        empty_msg.display = False
        table.display = True
        table.clear()

        for item in self.entries:
            icon = item["icon"]
            name = item["name"]
            is_dir = item["is_dir"]
            is_hidden = item["is_hidden"]

            if is_hidden:
                name_fmt = f"[dim]{name}[/dim]"
                icon_fmt = f"[dim]{icon}[/dim]"
            elif is_dir:
                name_fmt = f"[bold blue]{name}/[/bold blue]"
                icon_fmt = icon
            else:
                name_fmt = name
                icon_fmt = icon

            size_val = item.get("size")
            size_fmt = format_human_size(size_val) if size_val is not None else ("-" if not is_dir else "📁 dir")
            if is_hidden:
                size_fmt = f"[dim]{size_fmt}[/dim]"

            mtime_fmt = format_timestamp(item.get("mtime"))
            if is_hidden:
                mtime_fmt = f"[dim]{mtime_fmt}[/dim]"

            classification = "Folder" if is_dir else ("Hidden File" if is_hidden else "File")

            table.add_row(
                icon_fmt,
                name_fmt,
                size_fmt,
                mtime_fmt,
                classification,
                key=item["path"],
            )

        table.focus()

    def render_tree_view(self) -> None:
        """Populate the Tree widget with directory hierarchy."""
        table = self.query_one("#entries-table", DataTable)
        tree = self.query_one("#entries-tree", Tree)
        empty_msg = self.query_one("#empty-msg", Static)

        table.display = False
        empty_msg.display = False
        tree.display = True

        tree.reset(f"📁 {self.target_dir}", data=self.target_dir)
        tree.root.expand()

        self._populate_tree_node(tree.root, self.target_dir, max_depth=2, current_depth=1)
        tree.focus()

    def _populate_tree_node(self, parent_node: Any, dir_path: str, max_depth: int = 2, current_depth: int = 1) -> None:
        """Recursively populate child nodes for directory."""
        if current_depth > max_depth:
            return

        try:
            items = []
            with os.scandir(dir_path) as it:
                for entry in it:
                    if not self.show_hidden and entry.name.startswith("."):
                        continue
                    try:
                        st = entry.stat(follow_symlinks=False)
                        is_dir = stat.S_ISDIR(st.st_mode)
                        size = st.st_size if not is_dir else None
                    except Exception:
                        is_dir = False
                        size = None
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "size": size,
                        "icon": get_file_icon(entry.name, is_dir=is_dir),
                    })
        except Exception:
            return

        # Sort items: directories first, then files
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        for it in items:
            name = it["name"]
            is_dir = it["is_dir"]
            icon = it["icon"]
            size_str = format_human_size(it["size"]) if it["size"] is not None else ""
            label_text = f"{icon} {name}" + (f"  [dim]({size_str})[/dim]" if size_str else "")

            if is_dir:
                node = parent_node.add(label_text, data=it["path"], expand=(current_depth == 1))
                if current_depth < max_depth:
                    self._populate_tree_node(node, it["path"], max_depth=max_depth, current_depth=current_depth + 1)
            else:
                parent_node.add_leaf(label_text, data=it["path"])

    # --------------------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------------------

    def action_toggle_view(self) -> None:
        """Toggle between flat list view and tree view ('t')."""
        self.view_mode = "tree" if self.view_mode == "flat" else "flat"
        if self.view_mode == "flat":
            self.render_flat_table()
        else:
            self.render_tree_view()
        self.update_status_bar()

    def action_cycle_sort(self) -> None:
        """Cycle sorting between Name -> Size -> Date ('s')."""
        if self.sort_mode == "name":
            self.sort_mode = "size"
        elif self.sort_mode == "size":
            self.sort_mode = "date"
        else:
            self.sort_mode = "name"

        self.apply_sorting()
        if self.view_mode == "flat":
            self.render_flat_table()
        else:
            self.render_tree_view()
        self.update_status_bar()

    def action_toggle_hidden(self) -> None:
        """Toggle hidden files visibility ('h')."""
        self.show_hidden = not self.show_hidden
        self.load_directory()

    def action_refresh_view(self) -> None:
        """Refresh directory listing ('r')."""
        self.load_directory()

    def action_show_details(self) -> None:
        """Open detailed stat card for currently focused entry ('Enter')."""
        selected_path: Optional[str] = None

        if self.view_mode == "flat":
            table = self.query_one("#entries-table", DataTable)
            if table.cursor_row is not None and 0 <= table.cursor_row < len(self.entries):
                selected_path = self.entries[table.cursor_row]["path"]
        else:
            tree = self.query_one("#entries-tree", Tree)
            if tree.cursor_node is not None and tree.cursor_node.data:
                selected_path = str(tree.cursor_node.data)

        if selected_path and os.path.exists(selected_path):
            self.push_screen(ItemDetailsModal(selected_path))
        else:
            self.notify("Select a valid item to view details.", severity="warning")


def run_list_tui_app(target_dir: str) -> None:
    """Launch the interactive List & Tree TUI Inspector."""
    app = ListInspectorApp(target_dir=target_dir)
    app.run()
