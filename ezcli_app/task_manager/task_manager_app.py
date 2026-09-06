"""Modern, Windows-inspired Terminal Task Manager for EasyCLI with full mouse support.
Supports Normal Mode (User Apps) and Pro Mode (All Processes with auto-elevation).
"""

import glob
import os
import signal
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure venv site-packages is accessible if textual is in user venv
venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll  # type: ignore
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

from .process_engine import ProcessEngine, ProcessItem


def make_mini_gauge(percent: float, width: int = 12) -> str:
    """Create a sleek visual mini gauge using unicode blocks."""
    pct = max(0.0, min(100.0, percent))
    filled = int(round((pct / 100.0) * width))
    empty = width - filled

    if pct >= 80.0:
        color = "bold red"
    elif pct >= 50.0:
        color = "bold yellow"
    else:
        color = "bold green"

    return f"[{color}]{'█' * filled}[/{color}][dim #444444]{'░' * empty}[/dim #444444] [{color}]{pct:4.1f}%[/{color}]"


# ==============================================================================
# Modal Dialogs: End Task, Process Details, Help
# ==============================================================================

class EndTaskModal(ModalScreen[Optional[Tuple[int, int]]]):
    """Confirmation modal to safely end or force-kill a task."""

    DEFAULT_CSS = """
    EndTaskModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #end-task-dialog {
        width: 72;
        height: auto;
        border: round red;
        background: $surface;
        padding: 1 2;
    }
    #end-task-title {
        text-style: bold;
        color: red;
        text-align: center;
        margin-bottom: 1;
    }
    .modal-line {
        color: white;
        margin-bottom: 1;
    }
    .unresp-warning {
        background: #442200;
        border: solid yellow;
        color: yellow;
        padding: 0 1;
        margin-bottom: 1;
        text-style: bold;
    }
    .system-warning {
        background: #440000;
        border: solid red;
        color: white;
        padding: 0 1;
        margin-bottom: 1;
        text-style: bold;
    }
    .cmd-box {
        background: $surface-darken-1;
        border: solid gray;
        color: cyan;
        padding: 0 1;
        margin-bottom: 1;
    }
    #modal-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    #modal-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "end_task", "End Task"),
        Binding("k", "force_kill", "Force Kill"),
    ]

    def __init__(self, process: ProcessItem) -> None:
        super().__init__()
        self.process = process

    def compose(self) -> ComposeResult:
        p = self.process
        with Vertical(id="end-task-dialog"):
            yield Label(f"🛑 End Task: {p.app_icon} {p.name}", id="end-task-title")

            if p.is_unresponsive:
                yield Label(
                    f"⚠️ ATTENTION: {p.unresponsive_badge}\n"
                    "This process is not responding to input or is locked in I/O wait.\n"
                    "Terminating it will release hung resources and unfreeze your session.",
                    classes="unresp-warning",
                )
            elif p.category == "system":
                yield Label(
                    "🛡️ SYSTEM PROCESS WARNING:\n"
                    "This is a system/root service. Terminating it requires administrator\n"
                    "rights and may disrupt system stability or services.",
                    classes="system-warning",
                )

            yield Label(
                f"PID: [bold cyan]{p.pid}[/bold cyan]   "
                f"User: [bold]{p.user}[/bold]   "
                f"CPU: [bold]{p.cpu_percent}%[/bold]   "
                f"RAM: [bold]{p.rss_str}[/bold] ({p.mem_percent}%)",
                classes="modal-line",
            )

            cmd_preview = p.args if len(p.args) <= 100 else (p.args[:97] + "...")
            yield Label(f"[dim]Command:[/dim] {cmd_preview}", classes="cmd-box")

            yield Label(
                "Choose safe [bold green]End Task (SIGTERM)[/bold green] to allow cleanup,\n"
                "or [bold red]Force Kill (SIGKILL)[/bold red] to immediately abort:",
                classes="modal-line",
            )

            with Horizontal(id="modal-buttons"):
                yield Button("🛑 End Task (Enter)", variant="primary", id="btn-end-task")
                yield Button("⚡ Force Kill (k)", variant="error", id="btn-force-kill")
                yield Button("Cancel (Esc)", variant="default", id="btn-cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_end_task(self) -> None:
        self.dismiss((self.process.pid, signal.SIGTERM))

    def action_force_kill(self) -> None:
        self.dismiss((self.process.pid, signal.SIGKILL))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-end-task":
            self.action_end_task()
        elif event.button.id == "btn-force-kill":
            self.action_force_kill()
        else:
            self.action_cancel()


class TaskDetailsModal(ModalScreen[None]):
    """Detailed inspection modal for a process."""

    DEFAULT_CSS = """
    TaskDetailsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #details-dialog {
        width: 76;
        height: auto;
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
        color: white;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    def __init__(self, process: ProcessItem) -> None:
        super().__init__()
        self.process = process

    def compose(self) -> ComposeResult:
        p = self.process

        # Read /proc/<pid>/ status details if accessible
        ppid_str = str(p.ppid)
        threads = "1"
        cwd = "N/A"
        exe = "N/A"
        try:
            cwd = os.readlink(f"/proc/{p.pid}/cwd")
        except Exception:
            pass
        try:
            exe = os.readlink(f"/proc/{p.pid}/exe")
        except Exception:
            pass
        try:
            with open(f"/proc/{p.pid}/status", "r") as f:
                for line in f:
                    if line.startswith("Threads:"):
                        threads = line.split()[1]
        except Exception:
            pass

        with Vertical(id="details-dialog"):
            yield Label(f"ℹ️ Process Details: {p.app_icon} {p.name}", id="details-title")

            unresp_str = f" [bold yellow]{p.unresponsive_badge}[/bold yellow]" if p.is_unresponsive else ""
            yield Label(f"Status: {p.status_icon} [bold]{p.status_text}[/bold]{unresp_str}", classes="details-row")
            yield Label(f"Category: [bold]{p.category_badge}[/bold]   PID: [bold cyan]{p.pid}[/bold cyan]   PPID: [bold]{ppid_str}[/bold]   User: [bold]{p.user}[/bold]", classes="details-row")
            yield Label(f"CPU Usage: [bold]{p.cpu_percent}%[/bold]   RAM Usage: [bold]{p.rss_str}[/bold] ({p.mem_percent}%)   Threads: [bold]{threads}[/bold]", classes="details-row")
            yield Label(f"Binary Path: [cyan]{exe}[/cyan]", classes="details-row")
            yield Label(f"Working Dir: [dim]{cwd}[/dim]", classes="details-row")
            yield Label(f"Full Arguments:\n[dim]{p.args}[/dim]", classes="details-row")

            with Horizontal(id="modal-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class TaskHelpModal(ModalScreen[None]):
    """Help modal showing mouse and keyboard shortcuts."""

    DEFAULT_CSS = """
    TaskHelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #help-dialog {
        width: 68;
        height: auto;
        border: round green;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: green;
        text-align: center;
        margin-bottom: 1;
    }
    .help-text {
        color: white;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Label("❓ EasyCLI Task Manager — Cheatsheet", id="help-title")
            help_content = (
                "🖱️ [bold yellow]Mouse Controls:[/bold yellow]\n"
                "  • [bold]Click row[/bold]       Select process\n"
                "  • [bold]Double-click[/bold]    Open End Task confirmation\n"
                "  • [bold]Click headers[/bold]   Sort by CPU, RAM, Name, PID, Status\n"
                "  • [bold]Click buttons[/bold]   Trigger actions, tabs, filters\n\n"
                "⌨️ [bold yellow]Keyboard Shortcuts:[/bold yellow]\n"
                "  • [bold green]Del / k[/bold green]          End Task (Graceful SIGTERM)\n"
                "  • [bold green]Shift+K / K[/bold green]      Force Kill (Immediate SIGKILL)\n"
                "  • [bold green]/[/bold green]              Instant Search / Filter box\n"
                "  • [bold green]Space[/bold green]          Pause / Resume live auto-refresh\n"
                "  • [bold green]r[/bold green]              Refresh list now\n"
                "  • [bold green]p[/bold green]              Toggle Normal Mode ⟷ Pro Mode\n"
                "  • [bold green]i / Enter[/bold green]      Inspect process details\n"
                "  • [bold green]1 - 5[/bold green]          Filter tabs (All, Apps, Background, System, Unresponsive)\n"
                "  • [bold green]q / Esc[/bold green]        Exit Task Manager\n"
            )
            yield Label(help_content, classes="help-text")
            with Horizontal(id="modal-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


# ==============================================================================
# Main Task Manager Application
# ==============================================================================

class TaskManagerApp(App[None]):
    """Modern terminal Task Manager application with mouse support and Windows aesthetics."""

    CSS = """
    Screen {
        background: #0f141c;
        color: #e2e8f0;
    }

    #header-container {
        height: 4;
        background: #1a2234;
        border-bottom: heavy #334155;
        padding: 0 1;
    }

    #title-row {
        height: 1;
        margin-top: 0;
    }

    #app-title {
        text-style: bold;
        color: #38bdf8;
    }

    #mode-indicator {
        text-align: right;
        color: #4ade80;
        text-style: bold;
    }

    #metrics-row {
        height: 1;
        margin-top: 1;
    }

    .metric-gauge {
        width: 28;
    }

    .metric-count {
        width: 18;
    }

    #unresp-metric {
        width: 22;
        text-style: bold;
    }

    #filter-container {
        height: 3;
        background: #131b2a;
        padding: 0 1;
        border-bottom: solid #1e293b;
    }

    #filter-input {
        width: 1fr;
        height: 3;
        border: solid #38bdf8;
        background: #0b0f17;
        color: white;
    }

    #category-bar {
        height: 3;
        background: #101726;
        padding: 0 1;
        border-bottom: solid #1e293b;
    }

    #category-bar Button {
        margin-right: 1;
        height: 3;
        border: none;
    }

    .tab-active {
        background: #0284c7;
        color: white;
        text-style: bold;
    }

    #table-container {
        height: 1fr;
        background: #0b0f17;
    }

    #process-table {
        height: 1fr;
        background: #0b0f17;
        border: none;
    }

    #action-bar {
        height: 3;
        background: #1a2234;
        border-top: solid #334155;
        padding: 0 1;
    }

    #action-bar Button {
        margin-right: 1;
        height: 3;
        border: none;
    }

    #status-notification {
        width: 1fr;
        text-align: right;
        color: #38bdf8;
        padding-right: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "escape_action", "Back/Quit", show=False),
        Binding("delete", "end_task", "End Task"),
        Binding("k", "end_task", "End Task"),
        Binding("K", "force_kill", "Force Kill"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("r", "refresh_now", "Refresh"),
        Binding("p", "toggle_mode", "Toggle Mode"),
        Binding("i", "inspect_details", "Details"),
        Binding("enter", "inspect_details", "Details"),
        Binding("question_mark", "show_help", "Help"),
        Binding("1", "tab_all", "All", show=False),
        Binding("2", "tab_apps", "Apps", show=False),
        Binding("3", "tab_bg", "Background", show=False),
        Binding("4", "tab_system", "System", show=False),
        Binding("5", "tab_unresp", "Unresponsive", show=False),
    ]

    def __init__(self, mode: str = "normal") -> None:
        super().__init__()
        self.mode = mode  # "normal" or "pro"
        self.engine = ProcessEngine()
        self.filter_text = ""
        self.category_filter = "all"
        self.sort_by = "cpu"
        self.sort_reverse = True
        self.is_paused = False
        self.refresh_timer = None
        self.current_processes: List[ProcessItem] = []
        self.selected_pid: Optional[int] = None

    def compose(self) -> ComposeResult:
        # 1. Top Dashboard Header
        with Vertical(id="header-container"):
            with Horizontal(id="title-row"):
                yield Label("📋 EasyCLI Task Manager", id="app-title")
                mode_badge = "📱 USER APPS" if self.mode == "normal" else "🛡️ PRO MODE (ALL TASKS)"
                mode_color = "#4ade80" if self.mode == "normal" else "#f43f5e"
                yield Label(f"[{mode_color}]{mode_badge}[/{mode_color}]", id="mode-indicator")

            with Horizontal(id="metrics-row"):
                yield Label("⚡ CPU: 0.0%", id="cpu-metric", classes="metric-gauge")
                yield Label("🧠 RAM: 0/0", id="ram-metric", classes="metric-gauge")
                yield Label("📱 Apps: 0", id="apps-metric", classes="metric-count")
                yield Label("✨ 0 Unresponsive", id="unresp-metric")

        # 2. Quick Filter Input
        with Horizontal(id="filter-container"):
            yield Input(
                placeholder="🔍 Type to filter processes by name, PID, user, or status... (Press / to focus)",
                id="filter-input",
            )

        # 3. Category Filter Tabs (Always visible, very prominent in Pro mode)
        with Horizontal(id="category-bar"):
            yield Button("🌟 All Tasks (1)", id="tab-all", classes="tab-active", variant="default")
            yield Button("📱 User Apps (2)", id="tab-apps", variant="default")
            yield Button("⚙️ Background (3)", id="tab-bg", variant="default")
            yield Button("🔒 System (4)", id="tab-system", variant="default")
            yield Button("⚠️ Unresponsive (5)", id="tab-unresp", variant="default")

        # 4. Main Process DataTable
        with Container(id="table-container"):
            yield DataTable(id="process-table", cursor_type="row")

        # 5. Bottom Action Bar
        with Horizontal(id="action-bar"):
            yield Button("🛑 End Task (Del)", variant="error", id="btn-end-task")
            yield Button("⚡ Force Kill (Shift+K)", variant="warning", id="btn-force-kill")
            yield Button("ℹ️ Details (i)", variant="primary", id="btn-details")
            yield Button("⏸️ Pause (Space)", variant="default", id="btn-pause")
            yield Button("🔄 Refresh (r)", variant="default", id="btn-refresh")
            pro_label = "🛡️ Switch to Pro (p)" if self.mode == "normal" else "📱 Switch to Apps (p)"
            yield Button(pro_label, variant="default", id="btn-toggle-mode")
            yield Button("❓ Help (?)", variant="default", id="btn-help")
            yield Label("", id="status-notification")

    def on_mount(self) -> None:
        """Initialize data table columns and start live polling timer."""
        table = self.query_one(DataTable)
        table.zebra_stripes = True

        # Define columns with user-friendly headers and sorting
        table.add_column("Status", key="status")
        table.add_column("Application / Process", key="name")
        table.add_column("PID", key="pid")
        table.add_column("User", key="user")
        table.add_column("CPU %", key="cpu")
        table.add_column("Memory %", key="mem")
        table.add_column("RAM Used", key="rss")
        table.add_column("CPU Time", key="time")
        if self.mode == "pro":
            table.add_column("Category", key="category")

        # Initial process refresh
        self.refresh_process_data()

        # Start 1.5s background polling timer
        self.refresh_timer = self.set_interval(1.5, self.on_timer_tick)

    def on_timer_tick(self) -> None:
        """Periodic background refresh."""
        if not self.is_paused:
            self.refresh_process_data()

    def refresh_process_data(self) -> None:
        """Poll engine, update dashboard metrics, and populate data table."""
        items, summary = self.engine.get_processes(
            mode=self.mode,
            filter_text=self.filter_text,
            category_filter=self.category_filter,
            sort_by=self.sort_by,
            reverse=self.sort_reverse,
        )
        self.current_processes = items

        # 1. Update Metrics Header
        cpu_gauge = make_mini_gauge(summary["overall_cpu"], width=10)
        self.query_one("#cpu-metric", Label).update(f"⚡ CPU: {cpu_gauge}")

        ram_pct = summary.get("ram_percent", 0.0)
        ram_gauge = make_mini_gauge(ram_pct, width=10)
        self.query_one("#ram-metric", Label).update(f"🧠 RAM: {ram_gauge}")

        self.query_one("#apps-metric", Label).update(f"📱 Apps: {summary['apps_count']}")

        unresp_count = summary.get("unresponsive_count", 0)
        unresp_label = self.query_one("#unresp-metric", Label)
        if unresp_count > 0:
            unresp_label.update(f"[bold red]⚠️ {unresp_count} Unresponsive![/bold red]")
        else:
            unresp_label.update("[bold green]✨ All Responsive[/bold green]")

        # 2. Populate DataTable
        table = self.query_one(DataTable)
        prev_scroll_y = table.scroll_y
        table.clear()

        selected_row_key = None

        for p in items:
            # Color CPU %
            if p.cpu_percent >= 50.0:
                cpu_text = f"[bold red]{p.cpu_percent:4.1f}%[/bold red]"
            elif p.cpu_percent >= 20.0:
                cpu_text = f"[bold yellow]{p.cpu_percent:4.1f}%[/bold yellow]"
            else:
                cpu_text = f"[bold green]{p.cpu_percent:4.1f}%[/bold green]"

            # Color Memory %
            if p.mem_percent >= 30.0:
                mem_text = f"[bold red]{p.mem_percent:4.1f}%[/bold red]"
            elif p.mem_percent >= 10.0:
                mem_text = f"[bold yellow]{p.mem_percent:4.1f}%[/bold yellow]"
            else:
                mem_text = f"[dim]{p.mem_percent:4.1f}%[/dim]"

            # Status Column with Unresponsive Badge
            if p.is_unresponsive:
                status_markup = f"[bold red]⚠️ Unresponsive[/bold red]"
                name_markup = f"[bold red]{p.app_icon} {p.name}[/bold red]"
            else:
                status_markup = f"{p.status_icon} {p.status_text}"
                name_markup = f"{p.app_icon} [bold]{p.name}[/bold]"

            pid_str = f"[bold cyan]{p.pid}[/bold cyan]"
            user_str = f"[bold]{p.user}[/bold]" if p.user == self.engine.current_user else f"[dim]{p.user}[/dim]"

            row_cells = [
                status_markup,
                name_markup,
                pid_str,
                user_str,
                cpu_text,
                mem_text,
                p.rss_str,
                p.time_str,
            ]
            if self.mode == "pro":
                row_cells.append(p.category_badge)

            row_key = f"pid_{p.pid}"
            table.add_row(*row_cells, key=row_key)

            if self.selected_pid == p.pid:
                selected_row_key = row_key

        if selected_row_key:
            try:
                table.move_cursor(row=table.get_row_index(selected_row_key))
            except Exception:
                pass
        table.scroll_y = prev_scroll_y

    def get_selected_process(self) -> Optional[ProcessItem]:
        """Return the currently highlighted ProcessItem."""
        table = self.query_one(DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self.current_processes):
            return None
        return self.current_processes[table.cursor_row]

    # ==========================================================================
    # Mouse & Event Handlers
    # ==========================================================================

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Row selected via Enter or double-click -> show details."""
        p = self.get_selected_process()
        if p:
            self.selected_pid = p.pid
            self.action_inspect_details()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Mouse click on table header sorts by that column!"""
        key = str(event.column_key.value)
        if key in ("status", "name", "pid", "user", "cpu", "mem", "rss", "time"):
            if self.sort_by == key:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_by = key
                self.sort_reverse = (key in ("cpu", "mem", "rss", "status"))

            order_str = "descending" if self.sort_reverse else "ascending"
            self.show_notification(f"Sorted by {key.upper()} ({order_str})")
            self.refresh_process_data()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live search-as-you-type filter."""
        self.filter_text = event.value.strip()
        self.refresh_process_data()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks across action bar and category tabs."""
        btn_id = event.button.id
        if btn_id == "btn-end-task":
            self.action_end_task()
        elif btn_id == "btn-force-kill":
            self.action_force_kill()
        elif btn_id == "btn-details":
            self.action_inspect_details()
        elif btn_id == "btn-pause":
            self.action_toggle_pause()
        elif btn_id == "btn-refresh":
            self.action_refresh_now()
        elif btn_id == "btn-toggle-mode":
            self.action_toggle_mode()
        elif btn_id == "btn-help":
            self.action_show_help()
        elif btn_id and btn_id.startswith("tab-"):
            # Category tabs
            self.set_category_tab(btn_id.replace("tab-", ""))

    def set_category_tab(self, tab: str) -> None:
        """Switch active category tab."""
        self.category_filter = tab

        # Update button visual styling
        for tab_id in ("all", "apps", "bg", "system", "unresp"):
            btn = self.query_one(f"#tab-{tab_id}", Button)
            expected = "app" if tab_id == "apps" else ("background" if tab_id == "bg" else ("unresponsive" if tab_id == "unresp" else tab_id))
            if tab == expected:
                btn.add_class("tab-active")
            else:
                btn.remove_class("tab-active")

        self.refresh_process_data()

    def show_notification(self, message: str, is_error: bool = False) -> None:
        """Show temporary status notification on the bottom bar."""
        notif = self.query_one("#status-notification", Label)
        color = "bold red" if is_error else "bold cyan"
        notif.update(f"[{color}]{message}[/{color}]")

    # ==========================================================================
    # Actions & Keyboard Shortcuts
    # ==========================================================================

    def action_focus_filter(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def action_escape_action(self) -> None:
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.has_focus:
            filter_input.value = ""
            self.query_one(DataTable).focus()
        else:
            self.exit()

    def action_toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        pause_btn = self.query_one("#btn-pause", Button)
        if self.is_paused:
            pause_btn.label = "▶️ Resume (Space)"
            self.show_notification("⏸️ Live polling paused.")
        else:
            pause_btn.label = "⏸️ Pause (Space)"
            self.show_notification("▶️ Live polling resumed.")
            self.refresh_process_data()

    def action_refresh_now(self) -> None:
        self.refresh_process_data()
        self.show_notification("🔄 Process list refreshed.")

    def action_toggle_mode(self) -> None:
        """Toggle between Normal Mode (Apps only) and Pro Mode (All Tasks)."""
        new_mode = "pro" if self.mode == "normal" else "normal"
        self.mode = new_mode

        # Update mode indicator
        mode_label = self.query_one("#mode-indicator", Label)
        badge_text = "📱 USER APPS" if self.mode == "normal" else "🛡️ PRO MODE (ALL TASKS)"
        badge_color = "#4ade80" if self.mode == "normal" else "#f43f5e"
        mode_label.update(f"[{badge_color}]{badge_text}[/{badge_color}]")

        # Update button text
        toggle_btn = self.query_one("#btn-toggle-mode", Button)
        toggle_btn.label = "🛡️ Switch to Pro (p)" if self.mode == "normal" else "📱 Switch to Apps (p)"

        # Re-initialize columns if needed
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_column("Status", key="status")
        table.add_column("Application / Process", key="name")
        table.add_column("PID", key="pid")
        table.add_column("User", key="user")
        table.add_column("CPU %", key="cpu")
        table.add_column("Memory %", key="mem")
        table.add_column("RAM Used", key="rss")
        table.add_column("CPU Time", key="time")
        if self.mode == "pro":
            table.add_column("Category", key="category")

        self.show_notification(f"Switched to {badge_text}")
        self.refresh_process_data()

    def action_end_task(self) -> None:
        p = self.get_selected_process()
        if not p:
            self.show_notification("No process selected to end.", is_error=True)
            return

        def on_confirmed(result: Optional[Tuple[int, int]]) -> None:
            if not result:
                return
            pid, sig = result
            ok, msg = self.engine.terminate_process(pid, sig, is_pro=(self.mode == "pro"), app=self)
            self.show_notification(msg, is_error=not ok)
            self.refresh_process_data()

        self.push_screen(EndTaskModal(p), on_confirmed)

    def action_force_kill(self) -> None:
        p = self.get_selected_process()
        if not p:
            self.show_notification("No process selected to force kill.", is_error=True)
            return

        # Instant force kill confirmation
        ok, msg = self.engine.terminate_process(p.pid, signal.SIGKILL, is_pro=(self.mode == "pro"), app=self)
        self.show_notification(msg, is_error=not ok)
        self.refresh_process_data()

    def action_inspect_details(self) -> None:
        p = self.get_selected_process()
        if not p:
            self.show_notification("No process selected to inspect.", is_error=True)
            return
        self.push_screen(TaskDetailsModal(p))

    def action_show_help(self) -> None:
        self.push_screen(TaskHelpModal())

    # Tab shortcut actions
    def action_tab_all(self) -> None:
        self.set_category_tab("all")

    def action_tab_apps(self) -> None:
        self.set_category_tab("app")

    def action_tab_bg(self) -> None:
        self.set_category_tab("background")

    def action_tab_system(self) -> None:
        self.set_category_tab("system")

    def action_tab_unresp(self) -> None:
        self.set_category_tab("unresponsive")


def run_task_manager(mode: str = "normal") -> None:
    """Entrypoint to launch the TaskManagerApp."""
    app = TaskManagerApp(mode=mode)
    app.run()
