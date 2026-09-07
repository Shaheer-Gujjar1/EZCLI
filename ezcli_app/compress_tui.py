import glob
import os
import sys
from typing import Dict, List, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .collectors import format_bytes
from .compress_engine import (
    SUPPORTED_FORMATS,
    calculate_targets_summary,
    suggest_archive_name,
)

# Optional site-packages bootstrap for ezcli virtual environment
venv_site = glob.glob(
    os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages")
)
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.widgets import Button, Footer, Header, Input, Label, OptionList  # type: ignore
from textual.widgets.option_list import Option  # type: ignore


FORMAT_OPTIONS = [
    (".zip", "📦 .zip", "Standard ZIP Archive (Fast, Universal Compatibility)"),
    (".tar.gz", "🗜️ .tar.gz", "Gzip Tarball (Standard Linux Compressed Archive)"),
    (".tar.xz", "⚡ .tar.xz", "XZ Tarball (High Compression, Minimal Size)"),
    (".7z", "🗃️ .7z", "7-Zip Archive (Maximum Compression Ratio)"),
    (".tar.bz2", "📦 .tar.bz2", "Bzip2 Tarball (High Compression)"),
]


class CompressFormatApp(App[Optional[Dict[str, str]]]):
    """Interactive Textual TUI app to select compression format and customize archive name."""

    TITLE = "EasyCLI Archive Format Selector"
    SUB_TITLE = "Choose compression format and archive name"

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("q", "cancel", "Quit", show=False),
    ]

    DEFAULT_CSS = """
    Screen {
        align: center middle;
        background: rgba(0, 0, 0, 0.85);
    }

    #dialog-card {
        width: 72;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }

    #title-label {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }

    #summary-label {
        color: white;
        text-align: center;
        margin-bottom: 1;
    }

    #format-list {
        height: 8;
        border: solid dodgerblue;
        margin-bottom: 1;
    }

    #name-label {
        color: yellow;
        text-style: bold;
        margin-top: 1;
    }

    #name-input {
        border: solid cyan;
        margin-bottom: 1;
    }

    #button-bar {
        align: center middle;
        height: auto;
        margin-top: 1;
    }

    #button-bar Button {
        margin: 0 1;
    }
    """

    def __init__(self, targets: Sequence[str]):
        super().__init__()
        self.targets = list(targets)
        self.selected_format = ".zip"
        self.summary = calculate_targets_summary(self.targets)
        self.default_name = suggest_archive_name(self.targets, self.selected_format)

    def compose(self) -> ComposeResult:
        item_count = len(self.targets)
        byte_str = format_bytes(self.summary["total_bytes"])
        file_cnt = self.summary["file_count"]
        dir_cnt = self.summary["dir_count"]

        with Container(id="dialog-card"):
            yield Label("🗜️ Choose Compression Format", id="title-label")
            yield Label(
                f"Selected: [bold cyan]{item_count}[/bold cyan] items "
                f"({file_cnt} files, {dir_cnt} folders • ~{byte_str})",
                id="summary-label",
            )
            options = [
                Option(f"{badge}  {desc}", id=ext)
                for ext, badge, desc in FORMAT_OPTIONS
            ]
            yield OptionList(*options, id="format-list")
            yield Label("📁 Archive Name:", id="name-label")
            yield Input(value=self.default_name, id="name-input")
            with Horizontal(id="button-bar"):
                yield Button("🗜️ Compress", variant="primary", id="btn-compress")
                yield Button("❌ Cancel", variant="error", id="btn-cancel")

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option and event.option.id:
            new_fmt = str(event.option.id)
            self._update_format_selection(new_fmt)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option and event.option.id:
            new_fmt = str(event.option.id)
            self._update_format_selection(new_fmt)
            self.query_one("#name-input", Input).focus()

    def _update_format_selection(self, new_fmt: str) -> None:
        old_fmt = self.selected_format
        self.selected_format = new_fmt
        name_input = self.query_one("#name-input", Input)
        cur_val = name_input.value.strip()

        if cur_val.endswith(old_fmt):
            base_name = cur_val[: -len(old_fmt)]
            name_input.value = f"{base_name}{new_fmt}"
        elif "." not in cur_val:
            name_input.value = f"{cur_val}{new_fmt}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-compress":
            self._submit_selection()
        elif event.button.id == "btn-cancel":
            self.exit(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit_selection()

    def action_cancel(self) -> None:
        self.exit(None)

    def _submit_selection(self) -> None:
        name_input = self.query_one("#name-input", Input)
        val = name_input.value.strip()
        if not val:
            val = suggest_archive_name(self.targets, self.selected_format)

        if not any(val.endswith(ext) for ext in SUPPORTED_FORMATS):
            val = f"{val}{self.selected_format}"
        else:
            for ext in SUPPORTED_FORMATS:
                if val.endswith(ext):
                    self.selected_format = ext
                    break

        self.exit({"format": self.selected_format, "archive_name": val})


def prompt_format_cli(
    targets: Sequence[str],
    default_ext: str = ".zip",
    console: Optional[Console] = None,
) -> Optional[Dict[str, str]]:
    """CLI interactive fallback when Textual cannot be used or running in non-TTY mode."""
    console = console or Console()
    summary = calculate_targets_summary(targets)
    byte_str = format_bytes(summary["total_bytes"])

    table = Table(title="🗜️ Choose Compression Format", border_style="cyan")
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Format", style="bold white", width=12)
    table.add_column("Description", style="dim white")

    for idx, (ext, badge, desc) in enumerate(FORMAT_OPTIONS, start=1):
        table.add_row(str(idx), badge, desc)

    console.print(table)
    console.print(
        f"[dim]Selected: {len(targets)} items ({summary['file_count']} files, {summary['dir_count']} folders • ~{byte_str})[/dim]\n"
    )

    choice = Prompt.ask(
        "Choose format [1-5] (or 'q' to cancel)",
        choices=["1", "2", "3", "4", "5", "q", "Q"],
        default="1",
        console=console,
    )

    if choice.lower() == "q":
        return None

    idx = int(choice) - 1
    selected_ext = FORMAT_OPTIONS[idx][0]
    default_name = suggest_archive_name(targets, selected_ext)

    archive_name = Prompt.ask(
        "Archive output name",
        default=default_name,
        console=console,
    )

    archive_name = archive_name.strip()
    if not archive_name:
        archive_name = default_name

    if not any(archive_name.endswith(ext) for ext in SUPPORTED_FORMATS):
        archive_name = f"{archive_name}{selected_ext}"

    return {"format": selected_ext, "archive_name": archive_name}


def run_format_selector(
    targets: Sequence[str],
    console: Optional[Console] = None,
) -> Optional[Dict[str, str]]:
    """Launch Textual format selector or fallback to CLI prompt if interactive TTY is unavailable."""
    if sys.stdin.isatty():
        try:
            app = CompressFormatApp(targets=targets)
            res = app.run()
            if isinstance(res, dict) and "format" in res and "archive_name" in res:
                return res
            return None
        except Exception:
            # Fallback to CLI on any TUI rendering issue
            pass

    return prompt_format_cli(targets=targets, console=console)
