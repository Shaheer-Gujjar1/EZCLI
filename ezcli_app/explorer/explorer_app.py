"""Textual-based Modern Terminal File Explorer for EasyCLI v0.2."""

import datetime
import glob
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure local user venv is accessible if system python lacks textual
venv_site = glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App  # type: ignore
try:
    from textual.app import ComposeResult  # type: ignore
except ImportError:
    ComposeResult = Any  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option  # type: ignore

from ..collectors import format_bytes
from .file_icons import get_file_icon
from .places import (
    add_recent,
    get_standard_places,
    load_bookmarks,
    toggle_bookmark,
)


FIRST_RUN_FLAG = os.path.expanduser("~/.local/share/ezcli/first_run_seen")


# ==============================================================================
# Modal Overlays
# ==============================================================================
class FirstRunOverlay(ModalScreen):
    """Friendly first-run tutorial overlay teaching the 3 essential keys."""

    DEFAULT_CSS = """
    FirstRunOverlay {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #tutorial-card {
        width: 60;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    .key-title {
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }
    .key-row {
        margin: 1 0;
        color: white;
    }
    .key-highlight {
        color: yellow;
        text-style: bold;
    }
    .dismiss-hint {
        color: gray;
        margin-top: 1;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="tutorial-card"):
            yield Label("👋 Welcome to EasyCLI File Explorer!", classes="key-title")
            yield Label("A beginner-friendly graphical manager right in your terminal.\n")
            yield Label("Three basic keys to get started:", classes="key-row")
            yield Label("  • [Enter]  Open / navigate folder", classes="key-highlight")
            yield Label("  • [Space]  Select / multi-select items", classes="key-highlight")
            yield Label("  • [q]      Quit / close explorer", classes="key-highlight")
            yield Label("\nPress any key or click to start exploring...", classes="dismiss-hint")

    def on_key(self, event) -> None:
        self.dismiss()

    def on_click(self, event) -> None:
        self.dismiss()


class PlacesModal(ModalScreen[Optional[str]]):
    """Quick Places menu: Home, Downloads, Documents, Desktop, Recent, Bookmarks."""

    DEFAULT_CSS = """
    PlacesModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #places-card {
        width: 65;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, current_path: str):
        super().__init__()
        self.current_path = current_path
        self.places_options: List[Tuple[str, str, str]] = []

    def compose(self) -> ComposeResult:
        with Container(id="places-card"):
            yield Label("📍 Quick Places & Bookmarks (Select to jump):", classes="key-title")
            yield OptionList(id="places-list")
            yield Label("[dim]Press Enter to navigate, Esc to cancel[/dim]")

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        self.places_options = []

        # Standard places
        for icon, name, p in get_standard_places():
            self.places_options.append((icon, name, p))
            option_list.add_option(Option(f"{icon} {name}  [dim]({p})[/dim]"))

        # Bookmarks
        bookmarks = load_bookmarks()
        if bookmarks:
            option_list.add_option(Option("─" * 40, disabled=True))
            for b in bookmarks:
                name = os.path.basename(b) or b
                self.places_options.append(("⭐", f"Bookmark: {name}", b))
                option_list.add_option(Option(f"⭐ {name}  [dim]({b})[/dim]"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        # Adjust for possible disabled divider
        valid_options = [opt for opt in self.places_options]
        if 0 <= idx < len(valid_options):
            self.dismiss(valid_options[idx][2])
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class ActionMenuModal(ModalScreen[str]):
    """Confirmation action menu when a directory is chosen."""

    DEFAULT_CSS = """
    ActionMenuModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #action-card {
        width: 65;
        height: auto;
        border: round green;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, directory_path: str):
        super().__init__()
        self.directory_path = directory_path

    def compose(self) -> ComposeResult:
        with Container(id="action-card"):
            yield Label(f"📁 Selected Directory: [bold cyan]{self.directory_path}[/bold cyan]")
            yield Label("Choose what you would like to do:\n")
            yield OptionList(
                Option("🐚 Open shell here (spawn $SHELL at this directory)", id="shell"),
                Option("📋 Copy path to clipboard / view path", id="copy_path"),
                Option("ℹ️ Show directory information & disk usage", id="info"),
                Option("❌ Cancel", id="cancel"),
                id="action-list",
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        action_id = str(event.option.id)
        self.dismiss(action_id)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss("cancel")


# ==============================================================================
# Main Explorer Application
# ==============================================================================
class ExplorerApp(App[Optional[Any]]):
    """Modular Terminal File Explorer and Picker for EasyCLI v0.2."""

    CSS = """
    Screen {
        background: $surface;
    }
    #header-container {
        dock: top;
        height: 3;
        background: $panel;
        padding: 0 1;
        border-bottom: solid cyan;
    }
    #breadcrumb-label {
        color: cyan;
        text-style: bold;
    }
    #status-summary {
        color: yellow;
    }
    #search-input {
        display: none;
        dock: top;
        margin: 0 1;
    }
    #body-container {
        height: 1fr;
    }
    #file-table {
        height: 1fr;
    }
    #info-sidebar {
        width: 32;
        display: none;
        border-left: solid cyan;
        background: $panel;
        padding: 1;
    }
    #empty-message {
        display: none;
        text-align: center;
        margin-top: 5;
        color: yellow;
        text-style: bold;
    }
    #permission-message {
        display: none;
        text-align: center;
        margin-top: 5;
        color: red;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit_explorer", "Quit", show=True),
        Binding("enter", "confirm_open", "Open", show=True),
        Binding("space", "toggle_select", "Select", show=True),
        Binding("slash", "start_search", "Search", show=True),
        Binding("p", "open_places", "Places", show=True),
        Binding("h", "toggle_hidden", "Hidden", show=True),
        Binding("s", "cycle_sort", "Sort", show=True),
        Binding("i", "toggle_info", "Info", show=True),
        Binding("b", "toggle_bookmark", "Bookmark", show=True),
    ]

    def __init__(
        self,
        mode: str = "choose_dir",  # "choose_dir", "pick_source", "pick_dest"
        initial_dir: str = "~",
    ):
        super().__init__()
        self.mode = mode
        self.current_dir = os.path.abspath(os.path.expanduser(initial_dir))
        self.show_hidden = False
        self.sort_mode = "name"  # "name", "size", "date"
        self.selected_paths: Set[str] = set()
        self.cached_entries: List[Dict[str, Any]] = []
        self.filtered_entries: List[Dict[str, Any]] = []
        self.active_search_query = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="header-container"):
            yield Label(self.get_breadcrumb_string(), id="breadcrumb-label")
            yield Label(self.get_status_summary_string(), id="status-summary")

        yield Input(placeholder="Type to filter files (Esc to clear)...", id="search-input")

        with Horizontal(id="body-container"):
            yield DataTable(id="file-table")
            yield Static(id="empty-message")
            yield Static(id="permission-message")
            with Vertical(id="info-sidebar"):
                yield Label("📌 [bold]Item Info[/bold]\n")
                yield Static(id="info-content")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_column("Icon", width=4)
        table.add_column("Name", width=34)
        table.add_column("Size", width=12)
        table.add_column("Modified", width=18)

        # Load directory contents
        self.load_directory(self.current_dir)

        # Check first-run tutorial overlay
        if not os.path.isfile(FIRST_RUN_FLAG):
            try:
                os.makedirs(os.path.dirname(FIRST_RUN_FLAG), exist_ok=True)
                with open(FIRST_RUN_FLAG, "w") as f:
                    f.write("1")
                self.push_screen(FirstRunOverlay())
            except Exception:
                pass

    def get_breadcrumb_string(self) -> str:
        """Format path with home emoji and breadcrumb dividers."""
        home = str(Path.home())
        display_path = self.current_dir
        if display_path == home:
            return "🏠 Home (~)"
        elif display_path.startswith(home):
            rel = display_path[len(home):].strip("/")
            return "🏠 ~ / " + " / ".join(rel.split("/"))
        else:
            return "📁 " + " / ".join([p for p in display_path.split("/") if p])

    def get_status_summary_string(self) -> str:
        """Format selection counter and active sorting state."""
        sel_count = len(self.selected_paths)
        sel_text = f"[bold green]{sel_count} items selected[/bold green] | " if sel_count else ""
        mode_text = {
            "choose_dir": "Mode: Choose Directory",
            "pick_source": "Mode: Select Files/Folders to Copy or Move",
            "pick_dest": "Mode: Select Destination Directory",
        }.get(self.mode, "")
        return f"{sel_text}{mode_text} (Sort: {self.sort_mode.capitalize()} | Hidden: {'On' if self.show_hidden else 'Off'})"

    def update_headers(self) -> None:
        self.query_one("#breadcrumb-label", Label).update(self.get_breadcrumb_string())
        self.query_one("#status-summary", Label).update(self.get_status_summary_string())

    def load_directory(self, target_dir: str) -> None:
        """Load directory contents safely with error catching."""
        self.current_dir = os.path.abspath(target_dir)
        add_recent(self.current_dir)
        self.update_headers()

        table = self.query_one(DataTable)
        empty_msg = self.query_one("#empty-message", Static)
        perm_msg = self.query_one("#permission-message", Static)

        table.clear()
        empty_msg.display = False
        perm_msg.display = False
        table.display = True

        self.cached_entries = []

        # Add parent directory row '..' if not root
        if self.current_dir != "/":
            parent = os.path.dirname(self.current_dir)
            self.cached_entries.append({
                "name": ".. (Parent Folder)",
                "path": parent,
                "is_dir": True,
                "is_parent": True,
                "size_str": "-",
                "mtime_str": "-",
                "size_bytes": 0,
                "mtime": 0,
                "icon": "📁",
            })

        try:
            with os.scandir(self.current_dir) as it:
                for entry in it:
                    name = entry.name
                    if not self.show_hidden and name.startswith("."):
                        continue

                    try:
                        st = entry.stat(follow_symlinks=False)
                        is_dir = entry.is_dir(follow_symlinks=False)
                        icon = get_file_icon(name, is_dir=is_dir)
                        size_str = format_bytes(st.st_size) if not is_dir else "-"
                        mtime_dt = datetime.datetime.fromtimestamp(st.st_mtime)
                        mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M")

                        self.cached_entries.append({
                            "name": name,
                            "path": entry.path,
                            "is_dir": is_dir,
                            "is_parent": False,
                            "size_str": size_str,
                            "mtime_str": mtime_str,
                            "size_bytes": st.st_size,
                            "mtime": st.st_mtime,
                            "icon": icon,
                        })
                    except (PermissionError, FileNotFoundError):
                        continue

        except PermissionError:
            table.display = False
            perm_msg.update("🔒 [bold red]Permission Denied[/bold red]\nYou do not have permission to read this directory.")
            perm_msg.display = True
            return
        except Exception as e:
            table.display = False
            perm_msg.update(f"⚠️ Error reading directory: {e}")
            perm_msg.display = True
            return

        # Sort entries
        self.apply_sorting_and_filtering()

    def apply_sorting_and_filtering(self) -> None:
        table = self.query_one(DataTable)
        empty_msg = self.query_one("#empty-message", Static)
        table.clear()

        # Separate parent row from regular items
        parents = [e for e in self.cached_entries if e.get("is_parent")]
        regulars = [e for e in self.cached_entries if not e.get("is_parent")]

        # Apply search filter
        if self.active_search_query:
            q = self.active_search_query.lower()
            regulars = [e for e in regulars if q in e["name"].lower()]

        # Apply sort mode (directories always first)
        if self.sort_mode == "size":
            regulars.sort(key=lambda e: (not e["is_dir"], -e["size_bytes"], e["name"].lower()))
        elif self.sort_mode == "date":
            regulars.sort(key=lambda e: (not e["is_dir"], -e["mtime"], e["name"].lower()))
        else:
            # Name
            regulars.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))

        self.filtered_entries = parents + regulars

        if not regulars and not parents:
            empty_msg.update("📁 [yellow]This folder is empty[/yellow]")
            empty_msg.display = True
            table.display = False
            return

        empty_msg.display = False
        table.display = True

        for item in self.filtered_entries:
            path = item["path"]
            icon = item["icon"]
            name = item["name"]

            # Highlight selected items
            if path in self.selected_paths:
                icon_display = f"✔ {icon}"
                name_display = f"[bold green]{name}[/bold green]"
            else:
                icon_display = icon
                name_display = f"[bold cyan]{name}[/bold cyan]" if item["is_dir"] else name

            table.add_row(
                icon_display,
                name_display,
                item["size_str"],
                item["mtime_str"],
                key=path,
            )

        if self.filtered_entries:
            table.move_cursor(row=0)

    # --------------------------------------------------------------------------
    # User Interactions & Keybindings
    # --------------------------------------------------------------------------
    def action_quit_explorer(self) -> None:
        self.exit(None)

    def action_start_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.display = True
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        input_id = getattr(event, "input", None)
        ctrl_id = getattr(input_id, "id", None) or getattr(event.control, "id", None)
        if ctrl_id == "search-input":
            self.active_search_query = event.value
            self.apply_sorting_and_filtering()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = getattr(event, "input", None)
        ctrl_id = getattr(input_id, "id", None) or getattr(event.control, "id", None)
        if ctrl_id == "search-input":
            search_input = self.query_one("#search-input", Input)
            search_input.display = False
            self.query_one(DataTable).focus()

    def action_toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self.load_directory(self.current_dir)

    def action_cycle_sort(self) -> None:
        modes = ["name", "size", "date"]
        idx = (modes.index(self.sort_mode) + 1) % len(modes)
        self.sort_mode = modes[idx]
        self.apply_sorting_and_filtering()
        self.update_headers()

    def action_toggle_info(self) -> None:
        sidebar = self.query_one("#info-sidebar")
        sidebar.display = not sidebar.display
        if sidebar.display:
            self.update_info_panel()

    def action_toggle_bookmark(self) -> None:
        added = toggle_bookmark(self.current_dir)
        status = "Added bookmark for" if added else "Removed bookmark for"
        self.notify(f"{status} {os.path.basename(self.current_dir) or self.current_dir}")

    def action_open_places(self) -> None:
        def on_place_chosen(target: Optional[str]) -> None:
            if target and os.path.isdir(target):
                self.load_directory(target)

        self.push_screen(PlacesModal(self.current_dir), on_place_chosen)

    def action_toggle_select(self) -> None:
        """Toggle selection on highlighted item (Space)."""
        table = self.query_one(DataTable)
        if not self.filtered_entries or table.cursor_row is None:
            return

        item = self.filtered_entries[table.cursor_row]
        if item.get("is_parent"):
            return

        p = item["path"]
        if p in self.selected_paths:
            self.selected_paths.remove(p)
        else:
            self.selected_paths.add(p)

        # Refresh display while preserving cursor position
        curr_row = table.cursor_row
        self.apply_sorting_and_filtering()
        table.move_cursor(row=curr_row)
        self.update_headers()

    def action_confirm_open(self) -> None:
        """Handle Enter key: navigate folder or confirm selection."""
        table = self.query_one(DataTable)
        if not self.filtered_entries or table.cursor_row is None:
            return

        item = self.filtered_entries[table.cursor_row]

        # 1. Navigating inside directories
        if item["is_dir"]:
            self.load_directory(item["path"])
            return

        # 2. In pick_source mode: selection confirms or toggles
        if self.mode == "pick_source":
            if not self.selected_paths:
                self.selected_paths.add(item["path"])
            self.exit(list(self.selected_paths))
            return

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Mouse click or Enter on DataTable."""
        self.action_confirm_open()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self.query_one("#info-sidebar").display:
            self.update_info_panel()

    def update_info_panel(self) -> None:
        table = self.query_one(DataTable)
        info_label = self.query_one("#info-content", Static)
        if not self.filtered_entries or table.cursor_row is None:
            info_label.update("No item selected.")
            return

        item = self.filtered_entries[table.cursor_row]
        p = item["path"]

        try:
            st = os.stat(p)
            mode_str = stat.filemode(st.st_mode)
            info_text = (
                f"[bold cyan]Name:[/bold cyan] {item['name']}\n"
                f"[bold cyan]Type:[/bold cyan] {'Directory' if item['is_dir'] else 'File'}\n"
                f"[bold cyan]Size:[/bold cyan] {item['size_str']}\n"
                f"[bold cyan]Permissions:[/bold cyan] {mode_str}\n"
                f"[bold cyan]Modified:[/bold cyan] {item['mtime_str']}\n\n"
                f"[dim]{p}[/dim]"
            )
            info_label.update(info_text)
        except Exception as e:
            info_label.update(f"Cannot read info: {e}")

    # --------------------------------------------------------------------------
    # Confirming the Directory in choose_dir mode
    # --------------------------------------------------------------------------
    def confirm_chosen_directory(self) -> None:
        """Show action menu when directory is chosen."""
        def handle_action(action: str) -> None:
            if action == "shell":
                self.exit({"action": "shell", "dir": self.current_dir})
            elif action == "copy_path":
                self.exit({"action": "copy_path", "dir": self.current_dir})
            elif action == "info":
                self.exit({"action": "info", "dir": self.current_dir})

        self.push_screen(ActionMenuModal(self.current_dir), handle_action)


# ==============================================================================
# Helper Runners for CLI commands
# ==============================================================================
def run_choose_directory(initial_dir: str = "~") -> None:
    """Launch the interactive directory explorer."""
    app = ExplorerApp(mode="choose_dir", initial_dir=initial_dir)
    # Add a custom keybinding to choose the current directory
    app.BINDINGS.append(Binding("c", "choose_current", "Choose Dir", show=True))

    def action_choose_current(self: ExplorerApp) -> None:
        self.confirm_chosen_directory()

    setattr(ExplorerApp, "action_choose_current", action_choose_current)

    result = app.run()

    if isinstance(result, dict):
        act = result.get("action")
        target_dir = result.get("dir", os.getcwd())

        if act == "shell":
            shell = os.environ.get("SHELL", "/bin/bash")
            print(f"\n🚀 Spawning shell at: {target_dir}")
            print("Type 'exit' or press Ctrl+D to return to your previous session.\n")
            try:
                subprocess.run([shell], cwd=target_dir)
            except Exception as e:
                print(f"Error launching shell: {e}")

        elif act == "copy_path":
            print(f"\n📋 Directory Path: {target_dir}\n")

        elif act == "info":
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table
            console = Console()
            t = Table(box=None, show_header=False)
            t.add_column("Key", style="bold cyan")
            t.add_column("Value", style="white")
            t.add_row("Directory", target_dir)
            try:
                item_count = len(os.listdir(target_dir))
                t.add_row("Items Count", str(item_count))
            except Exception:
                pass
            console.print(Panel(t, title="📁 Directory Information", border_style="cyan"))


def run_source_picker(initial_dir: str = "~") -> List[str]:
    """Launch explorer to pick source files/directories for copy or move."""
    app = ExplorerApp(mode="pick_source", initial_dir=initial_dir)
    app.BINDINGS.append(Binding("c", "confirm_selection", "Confirm", show=True))

    def action_confirm_selection(self: ExplorerApp) -> None:
        table = self.query_one(DataTable)
        if not self.selected_paths and self.filtered_entries and table.cursor_row is not None:
            item = self.filtered_entries[table.cursor_row]
            if not item.get("is_parent"):
                self.selected_paths.add(item["path"])
        self.exit(list(self.selected_paths))

    setattr(ExplorerApp, "action_confirm_selection", action_confirm_selection)
    result = app.run()
    return result if isinstance(result, list) else []


def run_destination_picker(initial_dir: str = "~") -> Optional[str]:
    """Launch explorer to pick target destination directory."""
    app = ExplorerApp(mode="pick_dest", initial_dir=initial_dir)
    app.BINDINGS.append(Binding("c", "confirm_dest", "Select Target", show=True))

    def action_confirm_dest(self: ExplorerApp) -> None:
        self.exit(self.current_dir)

    setattr(ExplorerApp, "action_confirm_dest", action_confirm_dest)
    result = app.run()
    return result if isinstance(result, str) else None
