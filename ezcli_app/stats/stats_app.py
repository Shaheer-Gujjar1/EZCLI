"""Modern, live-updating Terminal System and Process Monitor for EasyCLI.
A sleek, beginner-friendly, and interactive htop alternative.
"""

import glob
import os
import signal
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure local user venv is accessible if system python lacks textual
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
    Input,
    Label,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option  # type: ignore

from ..elevation import is_root
from .metrics import SystemMetricsCollector


def make_gauge_markup(percent: float, width: int = 14) -> str:
    """Create a sleek visual gauge bar using unicode blocks."""
    pct = max(0.0, min(100.0, percent))
    filled_len = int(round((pct / 100.0) * width))
    empty_len = width - filled_len

    if pct >= 80.0:
        color = "bold red"
    elif pct >= 50.0:
        color = "bold yellow"
    else:
        color = "bold green"

    bar = f"[{color}]{'█' * filled_len}[/{color}][dim #444444]{'░' * empty_len}[/dim #444444]"
    return f"{bar} [{color}]{pct:5.1f}%[/{color}]"


# ==============================================================================
# Modal Dialogs: Kill Process, Process Details, Sort Picker, Help
# ==============================================================================

class KillProcessModal(ModalScreen[Optional[Tuple[int, int]]]):
    """Confirmation modal to safely terminate or kill a process."""

    DEFAULT_CSS = """
    KillProcessModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #kill-dialog {
        width: 66;
        height: auto;
        border: round red;
        background: $surface;
        padding: 1 2;
    }
    #kill-title {
        text-style: bold;
        color: red;
        text-align: center;
        margin-bottom: 1;
    }
    .kill-info {
        color: white;
        margin-bottom: 1;
    }
    .kill-cmd-box {
        background: $surface-darken-1;
        border: solid gray;
        padding: 0 1;
        margin-bottom: 1;
        color: cyan;
    }
    #kill-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    #kill-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("t", "terminate", "Terminate"),
        Binding("k", "kill", "Force Kill"),
    ]

    def __init__(self, process: Dict[str, Any]) -> None:
        super().__init__()
        self.process = process

    def compose(self) -> ComposeResult:
        p = self.process
        with Vertical(id="kill-dialog"):
            yield Label(f"🛑 Terminate Process: {p.get('comm', 'Unknown')}", id="kill-title")
            yield Label(
                f"[bold cyan]PID:[/bold cyan] {p.get('pid')}    "
                f"[bold cyan]User:[/bold cyan] {p.get('user')}    "
                f"[bold cyan]CPU:[/bold cyan] {p.get('cpu')}%    "
                f"[bold cyan]RAM:[/bold cyan] {p.get('rss_str')}",
                classes="kill-info",
            )
            cmd_preview = p.get("args") or p.get("comm") or ""
            if len(cmd_preview) > 120:
                cmd_preview = cmd_preview[:117] + "..."
            yield Label(f"[dim]Command:[/dim] {cmd_preview}", classes="kill-cmd-box")
            yield Label(
                "Choose safe termination ([bold green]SIGTERM[/bold green]) or immediate abort ([bold red]SIGKILL[/bold red]):",
                classes="kill-info",
            )
            with Horizontal(id="kill-buttons"):
                yield Button("Terminate (t)", variant="primary", id="btn-term")
                yield Button("Force Kill (k)", variant="error", id="btn-kill")
                yield Button("Cancel (Esc)", variant="default", id="btn-cancel")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_terminate(self) -> None:
        self.dismiss((self.process["pid"], signal.SIGTERM))

    def action_kill(self) -> None:
        self.dismiss((self.process["pid"], signal.SIGKILL))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-term":
            self.action_terminate()
        elif event.button.id == "btn-kill":
            self.action_kill()
        else:
            self.action_cancel()


class ProcessDetailsModal(ModalScreen[None]):
    """Inspection modal showing in-depth details of the selected process."""

    DEFAULT_CSS = """
    ProcessDetailsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #details-dialog {
        width: 78;
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
    #details-scroll {
        height: auto;
        max-height: 22;
        margin-bottom: 1;
    }
    .details-row {
        margin: 0 0 1 0;
        color: $text;
    }
    #details-buttons {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
    ]

    def __init__(self, details: Dict[str, Any], proc_summary: Dict[str, Any]) -> None:
        super().__init__()
        self.details = details
        self.proc_summary = proc_summary

    def compose(self) -> ComposeResult:
        d = self.details
        p = self.proc_summary
        pid = d.get("pid", p.get("pid"))
        name = d.get("name") or p.get("comm") or "Process"

        with Vertical(id="details-dialog"):
            yield Label(f"ℹ️ Process Details: {name} (PID {pid})", id="details-title")
            with VerticalScroll(id="details-scroll"):
                yield Label(
                    f"• [bold cyan]PID:[/bold cyan] {pid}    "
                    f"• [bold cyan]Parent PID (PPID):[/bold cyan] {d.get('ppid', p.get('ppid'))}    "
                    f"• [bold cyan]User:[/bold cyan] {p.get('user')}",
                    classes="details-row",
                )
                yield Label(
                    f"• [bold cyan]State:[/bold cyan] {d.get('state') or p.get('stat')}    "
                    f"• [bold cyan]Threads:[/bold cyan] {d.get('threads')}    "
                    f"• [bold cyan]Open File Descriptors:[/bold cyan] {d.get('fds_count')}",
                    classes="details-row",
                )
                yield Label(
                    f"• [bold cyan]CPU Usage:[/bold cyan] {p.get('cpu')}%    "
                    f"• [bold cyan]CPU Time:[/bold cyan] {p.get('time')}    "
                    f"• [bold cyan]Memory (RSS):[/bold cyan] {p.get('rss_str')} ({d.get('vm_rss', 'N/A')})",
                    classes="details-row",
                )
                yield Label(
                    f"• [bold cyan]Virtual Memory (VmSize):[/bold cyan] {d.get('vm_size', 'N/A')}",
                    classes="details-row",
                )
                yield Label(
                    f"• [bold cyan]Executable (EXE):[/bold cyan]\n  [dim]{d.get('exe')}[/dim]",
                    classes="details-row",
                )
                yield Label(
                    f"• [bold cyan]Working Directory (CWD):[/bold cyan]\n  [dim]{d.get('cwd')}[/dim]",
                    classes="details-row",
                )
                cmdline = d.get("cmdline") or p.get("args") or p.get("comm") or "N/A"
                yield Label(
                    f"• [bold cyan]Full Command Line:[/bold cyan]\n  [green]{cmdline}[/green]",
                    classes="details-row",
                )
            with Horizontal(id="details-buttons"):
                yield Button("Close (Esc)", variant="primary", id="btn-close-details")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_close()


class SortPickerModal(ModalScreen[Optional[str]]):
    """Modal to choose process table sort criteria."""

    DEFAULT_CSS = """
    SortPickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #sort-dialog {
        width: 48;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    #sort-title {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }
    #sort-options {
        height: 12;
        margin-bottom: 1;
    }
    #sort-buttons {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    SORT_CHOICES = [
        ("cpu", "⚡ CPU Usage (% - Highest First)"),
        ("mem", "🧠 Memory Usage (% - Highest First)"),
        ("rss", "💾 Resident RAM (MB/GB - Highest First)"),
        ("pid", "🔢 Process ID (PID - Numerical)"),
        ("time", "⏱️ CPU Time (Longest Running)"),
        ("name", "🔤 Process Name (A-Z)"),
        ("user", "👤 User Owner (A-Z)"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="sort-dialog"):
            yield Label("🔀 Sort Processes By", id="sort-title")
            options = [Option(label, id=val) for val, label in self.SORT_CHOICES]
            yield OptionList(*options, id="sort-options")
            with Horizontal(id="sort-buttons"):
                yield Button("Cancel (Esc)", variant="default", id="btn-cancel-sort")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        sort_key = event.option_id
        self.dismiss(str(sort_key))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_cancel()


class StatsHelpModal(ModalScreen[None]):
    """Cheat sheet modal explaining shortcuts, mouse controls, and safety."""

    DEFAULT_CSS = """
    StatsHelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #help-dialog {
        width: 72;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }
    #help-content {
        margin-bottom: 1;
        color: $text;
    }
    #help-buttons {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
        Binding("f1", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        help_text = (
            "[bold cyan]EasyCLI Live Stats & Process Monitor Guide[/bold cyan]\n\n"
            "  [bold green]Mouse Controls:[/bold green] Click any row to highlight, click column header to sort,\n"
            "                  click bottom action buttons, scroll table with wheel.\n\n"
            "  [bold green]k / x[/bold green]          Terminate or Kill selected process (safe confirmation)\n"
            "  [bold green]Enter / i[/bold green]      Inspect process details (cwd, exe, open files, cmdline)\n"
            "  [bold green]/ or Ctrl+F[/bold green]    Search / filter processes in real-time\n"
            "  [bold green]s[/bold green]              Open Sort Picker (CPU%, Memory%, RAM, PID, Name)\n"
            "  [bold green]Space[/bold green]          Pause / Resume live stats updates\n"
            "  [bold green]+ / -[/bold green]          Speed up or slow down refresh interval\n"
            "  [bold green]r[/bold green]              Force immediate refresh\n"
            "  [bold green]q / Esc[/bold green]        Quit Live Stats monitor\n\n"
            "[dim]Auto-Elevation: Terminating system/root processes will automatically prompt\n"
            "for admin elevation using EasyCLI's secure elevation helper.[/dim]"
        )
        with Vertical(id="help-dialog"):
            yield Label("📖 Monitor Controls & Help", id="help-title")
            yield Static(help_text, id="help-content")
            with Horizontal(id="help-buttons"):
                yield Button("Got it! (Esc)", variant="primary", id="btn-close-help")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_close()


# ==============================================================================
# Main Live Stats Application
# ==============================================================================

class StatsApp(App[None]):
    """Modern interactive Live System and Process Monitor."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #header-bar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
        padding: 0 1;
    }

    #header-title {
        width: auto;
        text-style: bold;
        color: cyan;
    }

    #header-info {
        width: 1fr;
        color: $text-muted;
        text-align: center;
    }

    #header-status {
        width: auto;
        text-align: right;
    }

    #dashboard-container {
        dock: top;
        height: auto;
        min-height: 8;
        max-height: 12;
        background: $surface;
        border-bottom: solid $surface-darken-2;
        padding: 0 1;
    }

    #dash-grid {
        grid-size: 2;
        grid-gutter: 1;
        height: auto;
    }

    .dash-card {
        background: $surface-darken-1;
        border: round $primary-darken-2;
        padding: 0 1;
        height: auto;
    }

    .card-title {
        text-style: bold;
        color: cyan;
        margin-bottom: 0;
    }

    .metric-row {
        height: 1;
        color: $text;
    }

    #cores-container {
        height: auto;
        max-height: 4;
        margin-top: 0;
    }

    #filter-bar {
        dock: top;
        height: 3;
        background: $surface-darken-2;
        border-bottom: solid cyan;
        padding: 0 1;
        display: none;
        align-vertical: middle;
    }

    #filter-input {
        width: 1fr;
        margin-right: 1;
    }

    #btn-clear-filter {
        min-width: 8;
        margin-right: 1;
    }

    #btn-close-filter {
        min-width: 8;
    }

    #process-table {
        width: 100%;
        height: 1fr;
        border: none;
    }

    #bottom-status-container {
        dock: bottom;
        height: auto;
        background: $surface-darken-1;
        border-top: solid $surface-darken-2;
    }

    #notification-banner {
        height: 1;
        background: $primary-darken-3;
        color: white;
        text-align: center;
        text-style: bold;
        display: none;
    }

    #action-bar {
        height: 3;
        align: center middle;
        padding: 0 1;
    }

    #action-bar Button {
        min-width: 8;
        height: 3;
        margin: 0 1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("escape", "handle_escape", "Back/Quit"),
        Binding("slash", "toggle_filter", "Filter"),
        Binding("ctrl+f", "toggle_filter", "Filter"),
        Binding("s", "open_sort", "Sort"),
        Binding("space", "toggle_pause", "Pause/Play"),
        Binding("k", "kill_selected", "Kill"),
        Binding("x", "kill_selected", "Kill"),
        Binding("enter", "inspect_selected", "Info"),
        Binding("i", "inspect_selected", "Info"),
        Binding("r", "refresh_now", "Refresh"),
        Binding("f1", "show_help", "Help"),
        Binding("h", "show_help", "Help"),
        Binding("plus", "speed_up", "Speed Up"),
        Binding("minus", "slow_down", "Slow Down"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.collector = SystemMetricsCollector()
        self.refresh_interval = 1.0
        self.is_paused = False
        self.sort_by = "cpu"
        self.sort_reverse = True
        self.filter_text = ""
        self.cached_processes: List[Dict[str, Any]] = []
        self.timer = None
        self.selected_pid: Optional[int] = None

    def compose(self) -> ComposeResult:
        # 1. Top Header Bar
        with Horizontal(id="header-bar"):
            yield Label("⚡ EasyCLI Live Monitor", id="header-title")
            yield Label("Loading system info...", id="header-info")
            admin_badge = " [bold red](Admin)[/bold red]" if is_root() else ""
            yield Label(f"[bold green]● LIVE ({self.refresh_interval:.1f}s)[/bold green]{admin_badge}", id="header-status")

        # 2. Resource Dashboard Cards
        with Container(id="dashboard-container"):
            with Grid(id="dash-grid"):
                # Card 1: CPU
                with Vertical(classes="dash-card", id="card-cpu"):
                    yield Label("⚡ CPU Utilization", classes="card-title")
                    yield Static("Calculating CPU...", id="cpu-overall-text", classes="metric-row")
                    yield Static("Load Average: ...", id="cpu-load-text", classes="metric-row")
                    yield Static("Per-Core Breakdown:", id="cpu-cores-header", classes="metric-row")
                    yield Static("", id="cores-grid")

                # Card 2: Memory & Tasks
                with Vertical(classes="dash-card", id="card-mem"):
                    yield Label("🧠 Memory & System Tasks", classes="card-title")
                    yield Static("RAM: Calculating...", id="ram-text", classes="metric-row")
                    yield Static("Avail: ... | Free: ... | Cache: ...", id="ram-breakdown-text", classes="metric-row")
                    yield Static("Swap: ...", id="swap-text", classes="metric-row")
                    yield Static("Tasks: ...", id="tasks-text", classes="metric-row")

        # 3. Filter / Search Bar
        with Horizontal(id="filter-bar"):
            yield Input(placeholder="🔍 Type to filter processes by name, PID, user, or command...", id="filter-input")
            yield Button("Clear", variant="default", id="btn-clear-filter")
            yield Button("Done", variant="primary", id="btn-close-filter")

        # 4. Interactive Process Table
        yield DataTable(id="process-table", cursor_type="row")

        # 5. Bottom Action Bar
        with Vertical(id="bottom-status-container"):
            yield Static("", id="notification-banner")
            with Horizontal(id="action-bar"):
                yield Button("❓ Help (F1)", variant="default", id="btn-help")
                yield Button("🔍 Filter (/)", variant="default", id="btn-filter")
                yield Button("🔀 Sort (s)", variant="default", id="btn-sort")
                yield Button("⏸️ Pause (Space)", variant="default", id="btn-pause")
                yield Button("🛑 Kill (k)", variant="error", id="btn-kill")
                yield Button("ℹ️ Details (i)", variant="primary", id="btn-info")
                yield Button("🔄 Refresh (r)", variant="default", id="btn-refresh")
                yield Button("❌ Quit (q)", variant="default", id="btn-quit")

    def on_mount(self) -> None:
        """Configure table columns and start background live refresh."""
        table = self.query_one("#process-table", DataTable)
        table.add_column("PID", key="pid", width=8)
        table.add_column("USER", key="user", width=12)
        table.add_column("CPU%", key="cpu", width=8)
        table.add_column("MEM%", key="mem", width=8)
        table.add_column("RAM", key="rss", width=10)
        table.add_column("STAT", key="stat", width=6)
        table.add_column("TIME", key="time", width=10)
        table.add_column("COMMAND", key="comm")

        # Initial metrics refresh
        self.refresh_stats()

        # Start live timer
        self.timer = self.set_interval(self.refresh_interval, self.refresh_stats)

    def refresh_stats(self) -> None:
        """Fetch real-time metrics and update UI."""
        if self.is_paused:
            return

        overview = self.collector.get_system_overview()
        procs, tasks = self.collector.get_processes(
            sort_by=self.sort_by,
            reverse=self.sort_reverse,
            filter_text=self.filter_text,
            limit=250,
        )
        self.cached_processes = procs

        # 1. Update Header Bar
        up_str = overview.get("uptime_str", "N/A")
        os_str = overview.get("os_name", "Linux")
        host_str = overview.get("hostname", "")
        self.query_one("#header-info", Label).update(
            f"{host_str} ({os_str})  •  Kernel: {overview.get('kernel')}  •  Uptime: {up_str}"
        )

        # 2. Update CPU Card
        cpu_pct = overview.get("cpu_percent", 0.0)
        cpu_bar = make_gauge_markup(cpu_pct, width=16)
        self.query_one("#cpu-overall-text", Static).update(
            f"CPU Overall: {cpu_bar}"
        )
        l1 = overview.get("load_1m", 0.0)
        l5 = overview.get("load_5m", 0.0)
        l15 = overview.get("load_15m", 0.0)
        cores = overview.get("cores", 1)
        self.query_one("#cpu-load-text", Static).update(
            f"Load Average: [bold cyan]{l1:.2f}[/bold cyan], [bold cyan]{l5:.2f}[/bold cyan], [bold cyan]{l15:.2f}[/bold cyan] ({cores} cores)"
        )

        # Per-core breakdown
        per_core = overview.get("cpu_per_core", [])
        if per_core:
            core_chunks = []
            # Group cores into pairs
            for i in range(0, len(per_core), 2):
                c1 = per_core[i]
                c1_bar = make_gauge_markup(c1["percent"], width=8)
                part1 = f"C{c1['core_id']:<2}: {c1_bar}"
                if i + 1 < len(per_core):
                    c2 = per_core[i + 1]
                    c2_bar = make_gauge_markup(c2["percent"], width=8)
                    part2 = f"  C{c2['core_id']:<2}: {c2_bar}"
                else:
                    part2 = ""
                core_chunks.append(part1 + part2)
            # Display up to 4 lines of cores
            self.query_one("#cores-grid", Static).update("\n".join(core_chunks[:4]))

        # 3. Update Memory Card
        ram_pct = overview.get("ram_percent", 0.0)
        ram_bar = make_gauge_markup(ram_pct, width=14)
        ram_used = overview.get("ram_used_str", "0B")
        ram_tot = overview.get("ram_total_str", "0B")
        self.query_one("#ram-text", Static).update(
            f"RAM:  {ram_bar}  ({ram_used} / {ram_tot})"
        )

        ram_avail = overview.get("ram_avail_str", "0B")
        ram_free = overview.get("ram_free_str", "0B")
        self.query_one("#ram-breakdown-text", Static).update(
            f"Available: [bold green]{ram_avail}[/bold green] | Free: [dim]{ram_free}[/dim]"
        )

        swap_pct = overview.get("swap_percent", 0.0)
        swap_bar = make_gauge_markup(swap_pct, width=14)
        swap_used = overview.get("swap_used_str", "0B")
        swap_tot = overview.get("swap_total_str", "0B")
        self.query_one("#swap-text", Static).update(
            f"Swap: {swap_bar}  ({swap_used} / {swap_tot})"
        )

        t_total = tasks.get("total", 0)
        t_run = tasks.get("running", 0)
        t_sleep = tasks.get("sleeping", 0)
        t_zombie = tasks.get("zombie", 0)
        zombie_badge = f" [bold red]{t_zombie} zombie[/bold red]" if t_zombie else "0 zombie"
        self.query_one("#tasks-text", Static).update(
            f"Tasks: [bold]{t_total}[/bold] total, [bold green]{t_run} running[/bold green], {t_sleep} sleeping, {zombie_badge}"
        )

        # 4. Update Process Table
        table = self.query_one("#process-table", DataTable)
        saved_row_idx = table.cursor_row
        table.clear(columns=False)

        for p in procs:
            cpu_val = p["cpu"]
            cpu_color = "bold red" if cpu_val >= 75.0 else ("bold yellow" if cpu_val >= 25.0 else "green")
            mem_val = p["mem"]
            mem_color = "bold red" if mem_val >= 50.0 else ("bold yellow" if mem_val >= 15.0 else "white")

            table.add_row(
                str(p["pid"]),
                f"[dim cyan]{p['user']}[/dim cyan]",
                f"[{cpu_color}]{cpu_val:5.1f}%[/{cpu_color}]",
                f"[{mem_color}]{mem_val:5.1f}%[/{mem_color}]",
                p["rss_str"],
                p["stat"],
                p["time"],
                p["comm"],
                key=str(p["pid"]),
            )

        # Restore cursor position
        if table.row_count > 0:
            if saved_row_idx is not None and saved_row_idx < table.row_count:
                table.move_cursor(row=saved_row_idx, animate=False)
            elif saved_row_idx is not None and saved_row_idx >= table.row_count:
                table.move_cursor(row=table.row_count - 1, animate=False)

    def show_notification(self, message: str, is_error: bool = False) -> None:
        """Display a temporary banner message."""
        banner = self.query_one("#notification-banner", Static)
        banner.styles.background = "crimson" if is_error else "darkgreen"
        banner.update(f" {message} ")
        banner.display = True
        self.set_timer(3.5, lambda: self._hide_notification())

    def _hide_notification(self) -> None:
        self.query_one("#notification-banner", Static).display = False

    def get_selected_process(self) -> Optional[Dict[str, Any]]:
        """Return the dictionary of the highlighted row in the process table."""
        table = self.query_one("#process-table", DataTable)
        if table.cursor_row is None or table.cursor_row >= len(self.cached_processes):
            return None
        return self.cached_processes[table.cursor_row]

    # ==========================================================================
    # Actions & Keybindings
    # ==========================================================================

    def action_quit_app(self) -> None:
        self.exit()

    def action_handle_escape(self) -> None:
        filter_bar = self.query_one("#filter-bar", Horizontal)
        if filter_bar.display:
            filter_bar.display = False
            self.filter_text = ""
            self.query_one("#filter-input", Input).value = ""
            self.refresh_stats()
            self.query_one("#process-table", DataTable).focus()
        else:
            self.exit()

    def action_toggle_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Horizontal)
        filter_input = self.query_one("#filter-input", Input)
        if filter_bar.display:
            filter_bar.display = False
            self.query_one("#process-table", DataTable).focus()
        else:
            filter_bar.display = True
            filter_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self.filter_text = event.value
            self.refresh_stats()

    def action_open_sort(self) -> None:
        def on_sort_picked(chosen_sort: Optional[str]) -> None:
            if chosen_sort:
                if self.sort_by == chosen_sort:
                    # Toggle reverse order if same column picked
                    self.sort_reverse = not self.sort_reverse
                else:
                    self.sort_by = chosen_sort
                    self.sort_reverse = True if chosen_sort in ("cpu", "mem", "rss", "time") else False
                self.show_notification(f"Sorted by {chosen_sort.upper()} ({'Descending' if self.sort_reverse else 'Ascending'})")
                self.refresh_stats()

        self.push_screen(SortPickerModal(), on_sort_picked)

    def action_toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
        status_label = self.query_one("#header-status", Label)
        pause_btn = self.query_one("#btn-pause", Button)
        admin_badge = " [bold red](Admin)[/bold red]" if is_root() else ""

        if self.is_paused:
            status_label.update(f"[bold yellow]❚❚ PAUSED[/bold yellow]{admin_badge}")
            pause_btn.label = "▶️ Resume (Space)"
            self.show_notification("Live updates paused. Press Space to resume.")
        else:
            status_label.update(f"[bold green]● LIVE ({self.refresh_interval:.1f}s)[/bold green]{admin_badge}")
            pause_btn.label = "⏸️ Pause (Space)"
            self.show_notification("Live updates resumed.")
            self.refresh_stats()

    def action_kill_selected(self) -> None:
        p = self.get_selected_process()
        if not p:
            self.show_notification("No process selected to terminate.", is_error=True)
            return

        def on_kill_confirmed(result: Optional[Tuple[int, int]]) -> None:
            if not result:
                return
            pid, sig = result
            success, msg = self.collector.terminate_process(pid, sig)
            self.show_notification(msg, is_error=not success)
            self.refresh_stats()

        self.push_screen(KillProcessModal(p), on_kill_confirmed)

    def action_inspect_selected(self) -> None:
        p = self.get_selected_process()
        if not p:
            self.show_notification("No process selected to inspect.", is_error=True)
            return

        pid = p["pid"]
        details = self.collector.get_process_details(pid)
        self.push_screen(ProcessDetailsModal(details, p))

    def action_refresh_now(self) -> None:
        self.refresh_stats()
        self.show_notification("Stats refreshed.")

    def action_show_help(self) -> None:
        self.push_screen(StatsHelpModal())

    def action_speed_up(self) -> None:
        if self.refresh_interval > 0.5:
            self.refresh_interval = max(0.5, round(self.refresh_interval - 0.5, 1))
            self._update_timer_interval()

    def action_slow_down(self) -> None:
        if self.refresh_interval < 5.0:
            self.refresh_interval = min(5.0, round(self.refresh_interval + 0.5, 1))
            self._update_timer_interval()

    def _update_timer_interval(self) -> None:
        if self.timer:
            self.timer.stop()
        self.timer = self.set_interval(self.refresh_interval, self.refresh_stats)
        admin_badge = " [bold red](Admin)[/bold red]" if is_root() else ""
        self.query_one("#header-status", Label).update(
            f"[bold green]● LIVE ({self.refresh_interval:.1f}s)[/bold green]{admin_badge}"
        )
        self.show_notification(f"Refresh interval set to {self.refresh_interval:.1f}s")

    # ==========================================================================
    # Button & Event Handlers
    # ==========================================================================

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-quit":
            self.action_quit_app()
        elif btn_id == "btn-help":
            self.action_show_help()
        elif btn_id == "btn-filter":
            self.action_toggle_filter()
        elif btn_id == "btn-sort":
            self.action_open_sort()
        elif btn_id == "btn-pause":
            self.action_toggle_pause()
        elif btn_id == "btn-kill":
            self.action_kill_selected()
        elif btn_id == "btn-info":
            self.action_inspect_selected()
        elif btn_id == "btn-refresh":
            self.action_refresh_now()
        elif btn_id == "btn-clear-filter":
            self.query_one("#filter-input", Input).value = ""
            self.filter_text = ""
            self.refresh_stats()
        elif btn_id == "btn-close-filter":
            self.action_toggle_filter()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Cycle or select column sorting when column header is clicked."""
        col_key = str(event.column_key.value)
        if col_key in ("pid", "user", "cpu", "mem", "rss", "time", "comm"):
            if col_key == "comm":
                col_key = "name"
            if self.sort_by == col_key:
                self.sort_reverse = not self.sort_reverse
            else:
                self.sort_by = col_key
                self.sort_reverse = True if col_key in ("cpu", "mem", "rss", "time") else False
            self.show_notification(f"Sorted by {col_key.upper()} ({'Descending' if self.sort_reverse else 'Ascending'})")
            self.refresh_stats()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Double click or Enter on row opens Process Details."""
        self.action_inspect_selected()


def run_live_stats() -> None:
    """Entry point to launch the live stats Textual TUI."""
    app = StatsApp()
    app.run()
