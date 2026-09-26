"""Visually distinct Textual TUI application for Internet Speed Testing."""

import glob
import os
import sys
import threading
from typing import Optional

venv_site = (
    glob.glob(os.path.expanduser("~/.local/share/ez/venv/lib/python*/site-packages"))
    + glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Horizontal, Vertical  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Footer,
    Header,
    Label,
    ProgressBar,
    Static,
)

from .speedtest_engine import SpeedTestResult, execute_speedtest


class SpeedtestApp(App[None]):
    """Textual interactive terminal speed test dashboard."""

    TITLE = "EasyCLI Speed Test"
    SUB_TITLE = "Real-Time Internet Bandwidth, Latency & Connection Performance"

    BINDINGS = [
        Binding("q", "quit", "❌ Close", show=True),
        Binding("r", "restart_test", "🔄 Test Again", show=True),
    ]

    CSS = """
    Screen {
        background: #030712;
        color: #f1f5f9;
        align: center middle;
    }

    #main-container {
        width: 76;
        height: auto;
        border: round #06b6d4;
        background: #0f172a;
        padding: 1 2;
    }

    #test-header {
        text-style: bold;
        color: #38bdf8;
        text-align: center;
        margin-bottom: 1;
    }

    #progress-label {
        color: #94a3b8;
        text-align: center;
        margin-bottom: 1;
    }

    ProgressBar {
        margin-bottom: 1;
        tint: #06b6d4;
    }

    #metric-cards {
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }

    .metric-card {
        width: 22;
        height: 5;
        border: round #38bdf8;
        background: #1e293b;
        content-align: center middle;
        margin: 0 1;
    }

    .metric-card-title {
        color: #94a3b8;
        text-align: center;
    }

    .metric-card-value {
        text-style: bold;
        font-size: 1;
        text-align: center;
    }

    #server-details {
        background: #1e293b;
        border: round #64748b;
        padding: 0 1;
        margin-bottom: 1;
        color: #cbd5e1;
        text-align: center;
    }

    #rating-banner {
        background: #1e1b4b;
        border: round #a855f7;
        padding: 0 1;
        margin-bottom: 1;
        text-align: center;
        color: #e9d5ff;
        text-style: bold;
    }

    #action-bar {
        height: auto;
        align: center middle;
    }

    #action-bar Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.test_in_progress = False
        self.result: Optional[SpeedTestResult] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-container"):
            yield Label("⚡ Internet Connection Speedometer", id="test-header")
            yield Label("Initializing connection...", id="progress-label")
            yield ProgressBar(total=100, show_eta=False, id="test-progress")
            with Horizontal(id="metric-cards"):
                with Vertical(classes="metric-card"):
                    yield Label("⚡ Latency (Ping)", classes="metric-card-title")
                    yield Label("-- ms", id="val-ping", classes="metric-card-value")
                with Vertical(classes="metric-card"):
                    yield Label("⬇️ Download Speed", classes="metric-card-title")
                    yield Label("-- Mbps", id="val-download", classes="metric-card-value")
                with Vertical(classes="metric-card"):
                    yield Label("⬆️ Upload Speed", classes="metric-card-title")
                    yield Label("-- Mbps", id="val-upload", classes="metric-card-value")
            yield Static(id="server-details")
            yield Static(id="rating-banner")
            with Horizontal(id="action-bar"):
                yield Button("🔄 Test Again", variant="primary", id="btn-retest")
                yield Button("❌ Close", variant="default", id="btn-close")
        yield Footer()

    def on_mount(self) -> None:
        self.start_test()

    def start_test(self) -> None:
        if self.test_in_progress:
            return
        self.test_in_progress = True
        self.query_one("#test-progress", ProgressBar).update(progress=10)
        self.query_one("#progress-label", Label).update("Connecting to optimal speed test server...")
        self.query_one("#val-ping", Label).update("-- ms")
        self.query_one("#val-download", Label).update("-- Mbps")
        self.query_one("#val-upload", Label).update("-- Mbps")
        self.query_one("#server-details", Static).update("Testing server discovery in progress...")
        self.query_one("#rating-banner", Static).update("Analyzing connection quality...")

        def worker():
            def cb(msg: str, frac: float):
                self.call_from_thread(self._update_progress, msg, frac)

            res = execute_speedtest(progress_callback=cb)
            self.call_from_thread(self._finish_test, res)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _update_progress(self, msg: str, frac: float) -> None:
        self.query_one("#progress-label", Label).update(msg)
        self.query_one("#test-progress", ProgressBar).update(progress=int(frac * 100))

    def _finish_test(self, res: SpeedTestResult) -> None:
        self.test_in_progress = False
        self.result = res

        self.query_one("#test-progress", ProgressBar).update(progress=100)
        self.query_one("#progress-label", Label).update("✅ Test Complete!")

        ping_color = "green" if res.ping_ms < 30 else ("yellow" if res.ping_ms < 70 else "red")
        self.query_one("#val-ping", Label).update(f"[bold {ping_color}]{res.ping_ms} ms[/]")
        self.query_one("#val-download", Label).update(f"[bold cyan]{res.download_mbps} Mbps[/]")
        self.query_one("#val-upload", Label).update(f"[bold #a855f7]{res.upload_mbps} Mbps[/]")

        self.query_one("#server-details", Static).update(
            f"Server: [bold white]{res.server_name}[/bold white] ({res.server_country})  |  "
            f"ISP: [bold white]{res.isp}[/bold white]"
        )
        self.query_one("#rating-banner", Static).update(res.rating)

    def action_restart_test(self) -> None:
        self.start_test()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-retest":
            self.start_test()
        elif event.button.id == "btn-close":
            self.exit()
