"""Modern, beginner-friendly Terminal Text & Code Editor for EasyCLI v0.3."""

import glob
import os
import re
import sys
from pathlib import Path
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
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Header,
    Input,
    Label,
    OptionList,
    Static,
    TextArea,
)
from textual.widgets.option_list import Option  # type: ignore

from ..collectors import format_bytes
from ..explorer.file_icons import get_file_icon


EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".rs": "rust",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".sql": "sql",
    ".java": "java",
}

AVAILABLE_THEMES = [
    ("vscode_dark", "🎨 VS Code Dark (Default)"),
    ("dracula", "🧛 Dracula Theme"),
    ("monokai", "🌋 Monokai Theme"),
    ("github_light", "☀️ GitHub Light"),
]

AVAILABLE_LANGUAGES = [
    ("plain", "📄 Plain Text"),
    ("python", "🐍 Python (.py)"),
    ("bash", "📜 Bash / Shell (.sh)"),
    ("javascript", "🟨 JavaScript (.js)"),
    ("typescript", "🔷 TypeScript (.ts)"),
    ("markdown", "📝 Markdown (.md)"),
    ("json", "📦 JSON (.json)"),
    ("yaml", "⚙️ YAML (.yaml/.yml)"),
    ("toml", "🔧 TOML (.toml)"),
    ("html", "🌐 HTML (.html)"),
    ("css", "🎨 CSS (.css)"),
    ("rust", "🦀 Rust (.rs)"),
    ("go", "🐹 Go (.go)"),
    ("sql", "🗄️ SQL (.sql)"),
    ("java", "☕ Java (.java)"),
]


# ==============================================================================
# Modal Screens: Unsaved Changes, Go To Line, Theme Picker, Syntax Picker, Help
# ==============================================================================

class UnsavedChangesModal(ModalScreen[str]):
    """Modal dialog asking user to save or discard changes upon exit."""

    DEFAULT_CSS = """
    UnsavedChangesModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #unsaved-dialog {
        width: 62;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
    }
    #unsaved-title {
        text-style: bold;
        color: $warning;
        text-align: center;
        margin-bottom: 1;
    }
    #unsaved-message {
        text-align: center;
        margin-bottom: 1;
        color: $text;
    }
    #unsaved-buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    #unsaved-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("s", "choose_save", "Save & Exit"),
        Binding("d", "choose_discard", "Discard & Exit"),
        Binding("c", "choose_cancel", "Cancel"),
        Binding("escape", "choose_cancel", "Cancel"),
    ]

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename

    def compose(self) -> ComposeResult:
        with Vertical(id="unsaved-dialog"):
            yield Label("⚠️  Unsaved Changes", id="unsaved-title")
            yield Label(
                f"File '{self.filename}' has unsaved modifications.\n"
                "Would you like to save changes before closing?",
                id="unsaved-message",
            )
            with Horizontal(id="unsaved-buttons"):
                yield Button("💾 Save & Exit [s]", variant="success", id="btn-save")
                yield Button("🗑️ Discard [d]", variant="error", id="btn-discard")
                yield Button("Cancel [Esc]", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.dismiss("save")
        elif event.button.id == "btn-discard":
            self.dismiss("discard")
        else:
            self.dismiss("cancel")

    def action_choose_save(self) -> None:
        self.dismiss("save")

    def action_choose_discard(self) -> None:
        self.dismiss("discard")

    def action_choose_cancel(self) -> None:
        self.dismiss("cancel")


class GotoLineModal(ModalScreen[Optional[int]]):
    """Modal dialog to jump directly to a line number."""

    DEFAULT_CSS = """
    GotoLineModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #goto-card {
        width: 48;
        height: auto;
        border: round cyan;
        background: $surface;
        padding: 1 2;
    }
    #goto-title {
        text-style: bold;
        color: cyan;
        text-align: center;
        margin-bottom: 1;
    }
    #goto-hint {
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
    }
    #goto-input {
        margin-bottom: 1;
    }
    #goto-buttons {
        align: center middle;
        height: 3;
    }
    #goto-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "choose_cancel", "Cancel"),
    ]

    def __init__(self, current_line: int, max_lines: int) -> None:
        super().__init__()
        self.current_line = current_line
        self.max_lines = max_lines

    def compose(self) -> ComposeResult:
        with Vertical(id="goto-card"):
            yield Label("🚀 Jump to Line", id="goto-title")
            yield Label(f"Enter line number (1 - {self.max_lines}):", id="goto-hint")
            yield Input(placeholder=f"{self.current_line}", id="goto-input")
            with Horizontal(id="goto-buttons"):
                yield Button("Jump ↵", variant="primary", id="btn-jump")
                yield Button("Cancel [Esc]", variant="default", id="btn-cancel")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit_line(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-jump":
            val = self.query_one("#goto-input", Input).value
            self.submit_line(val)
        else:
            self.dismiss(None)

    def submit_line(self, raw_val: str) -> None:
        raw_val = raw_val.strip()
        if not raw_val:
            self.dismiss(None)
            return
        try:
            line_num = int(raw_val)
            if 1 <= line_num <= self.max_lines:
                self.dismiss(line_num)
            else:
                self.query_one("#goto-hint", Label).update(
                    f"[bold red]Line out of range! Enter 1 - {self.max_lines}:[/bold red]"
                )
        except ValueError:
            self.query_one("#goto-hint", Label).update("[bold red]Please enter a valid number:[/bold red]")

    def action_choose_cancel(self) -> None:
        self.dismiss(None)


class ThemePickerModal(ModalScreen[Optional[str]]):
    """Modal dialog allowing user to choose an editor theme with mouse/keyboard."""

    DEFAULT_CSS = """
    ThemePickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #theme-card {
        width: 52;
        height: auto;
        border: round magenta;
        background: $surface;
        padding: 1 2;
    }
    #theme-title {
        text-style: bold;
        color: magenta;
        text-align: center;
        margin-bottom: 1;
    }
    #theme-list {
        height: 8;
        margin-bottom: 1;
    }
    #theme-buttons {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-card"):
            yield Label("🎨 Select Editor Theme", id="theme-title")
            options = [Option(label, id=theme_id) for theme_id, label in AVAILABLE_THEMES]
            yield OptionList(*options, id="theme-list")
            with Horizontal(id="theme-buttons"):
                yield Button("Cancel [Esc]", variant="default", id="btn-theme-cancel")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(str(event.option.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class SyntaxPickerModal(ModalScreen[Optional[str]]):
    """Modal dialog allowing user to choose syntax highlighting language with mouse/keyboard."""

    DEFAULT_CSS = """
    SyntaxPickerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #syntax-card {
        width: 54;
        height: auto;
        border: round green;
        background: $surface;
        padding: 1 2;
    }
    #syntax-title {
        text-style: bold;
        color: green;
        text-align: center;
        margin-bottom: 1;
    }
    #syntax-list {
        height: 12;
        margin-bottom: 1;
    }
    #syntax-buttons {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="syntax-card"):
            yield Label("🔤 Select Syntax Highlighting", id="syntax-title")
            options = [Option(label, id=lang_id) for lang_id, label in AVAILABLE_LANGUAGES]
            yield OptionList(*options, id="syntax-list")
            with Horizontal(id="syntax-buttons"):
                yield Button("Cancel [Esc]", variant="default", id="btn-syntax-cancel")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        lang = str(event.option.id)
        self.dismiss(None if lang == "plain" else lang)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class EditorHelpModal(ModalScreen[None]):
    """Modal cheat sheet for editor shortcuts and mouse actions."""

    DEFAULT_CSS = """
    EditorHelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #help-dialog {
        width: 68;
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
    #help-button-container {
        align: center middle;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_help", "Close"),
        Binding("enter", "dismiss_help", "Close"),
    ]

    def compose(self) -> ComposeResult:
        help_text = (
            "[bold cyan]EasyCLI Mini Editor Shortcuts & Mouse Controls[/bold cyan]\n\n"
            "  [bold green]Mouse Support:[/bold green] Click any toolbar button, click bottom action bar,\n"
            "                 click status badges, drag to highlight text, scroll with wheel.\n\n"
            "  [bold green]Ctrl + S[/bold green]      Save file (auto-prompts elevation if write-protected)\n"
            "  [bold green]Ctrl + X[/bold green]      Save and Exit editor immediately\n"
            "  [bold green]Ctrl + Q / Esc[/bold green] Exit editor (prompts if unsaved changes exist)\n"
            "  [bold green]Ctrl + F[/bold green]      Toggle interactive Find & Replace bar\n"
            "  [bold green]Ctrl + G / L[/bold green]  Jump to line number\n"
            "  [bold green]Ctrl + W[/bold green]      Toggle soft word wrap (On/Off)\n"
            "  [bold green]Ctrl + Z[/bold green]      Undo edit\n"
            "  [bold green]Ctrl + Y[/bold green]      Redo edit\n"
            "  [bold green]F2 / Ctrl + H[/bold green] Show this help cheat sheet\n\n"
            "[dim]Click 'Got it!' or press Esc to return to editing.[/dim]"
        )
        with Vertical(id="help-dialog"):
            yield Label("📖 Mini Editor Guide", id="help-title")
            yield Static(help_text, id="help-content")
            with Horizontal(id="help-button-container"):
                yield Button("Got it! [Enter]", variant="primary", id="btn-close-help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


# ==============================================================================
# Main Editor Application with Mouse Interactive Toolbar & Status System
# ==============================================================================

class EditorApp(App[bool]):
    """Modern beginner-friendly Terminal Text & Code Editor for EasyCLI."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #editor-header-bar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
        padding: 0 1;
        border: none;
    }

    #editor-header-title {
        width: 1fr;
        text-style: bold;
    }

    #editor-path-breadcrumb {
        width: auto;
        color: $text-muted;
    }

    #find-replace-panel {
        dock: top;
        height: auto;
        background: $surface-darken-2;
        border: round cyan;
        padding: 0 1;
        margin: 0 1;
        display: none;
    }

    .find-row {
        height: 3;
        align-vertical: middle;
        margin: 0;
    }

    .find-row Input {
        width: 1fr;
        margin-right: 1;
    }

    .find-row Button {
        min-width: 0;
        height: 3;
        margin-right: 1;
        padding: 0 1;
    }

    #find-status-label {
        width: 14;
        content-align: center middle;
        color: yellow;
        text-style: bold;
    }

    #main-text-area {
        width: 100%;
        height: 1fr;
        border: none;
    }

    #editor-bottom-container {
        dock: bottom;
        height: auto;
        background: $surface-darken-1;
    }

    #editor-status-bar {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        border: none;
    }

    #status-left {
        width: 1fr;
        height: 1;
        align-vertical: middle;
    }

    #status-right {
        width: auto;
        height: 1;
        align-vertical: middle;
    }

    .status-bar-btn {
        min-width: 0;
        height: 1;
        padding: 0 1;
        margin: 0;
        border: none;
        background: transparent;
        color: cyan;
        text-style: bold;
    }

    .status-bar-btn:hover {
        background: $surface-lighten-1;
        color: yellow;
    }

    #status-stats-label {
        color: $text-muted;
    }

    #status-encoding-label {
        color: $text-muted;
    }

    #editor-bottom-bar {
        height: 1;
        background: $surface-darken-2;
        align-vertical: middle;
        padding: 0 1;
        border: none;
    }

    #editor-bottom-bar Button {
        min-width: 0;
        height: 1;
        margin: 0 1 0 0;
        padding: 0 1;
        border: none;
        background: $surface-lighten-1;
        color: $text;
        text-style: bold;
    }

    #editor-bottom-bar Button:hover {
        background: $primary;
        color: $surface;
    }

    #bot-save {
        color: #4ade80;
    }

    #bot-save-exit {
        color: #38bdf8;
    }

    #bot-find {
        color: #facc15;
    }

    #bot-help {
        color: #c084fc;
    }

    #bot-exit {
        color: #f87171;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save_file", "Save", show=False),
        Binding("ctrl+x", "save_and_exit", "Save & Exit", show=False),
        Binding("ctrl+q", "exit_editor", "Exit", show=False),
        Binding("escape", "handle_escape", "Exit", show=False),
        Binding("ctrl+f", "toggle_find", "Find & Replace", show=False),
        Binding("ctrl+g", "goto_line", "Go to Line", show=False),
        Binding("ctrl+l", "goto_line", "Go to Line", show=False),
        Binding("ctrl+w", "toggle_wrap", "Wrap", show=False),
        Binding("ctrl+z", "undo_action", "Undo", show=False),
        Binding("ctrl+y", "redo_action", "Redo", show=False),
        Binding("f2", "show_help", "Help", show=False),
        Binding("ctrl+h", "show_help", "Help", show=False),
    ]

    def __init__(
        self,
        file_path: str,
        initial_content: str = "",
        is_new_file: bool = False,
        is_admin: bool = False,
    ) -> None:
        super().__init__()
        self.file_path = os.path.abspath(file_path)
        self.initial_content = initial_content
        self.is_new_file = is_new_file
        self.is_admin = is_admin
        self.is_modified = False
        self.soft_wrap_enabled = True
        self.active_theme = "vscode_dark"
        self.active_language: Optional[str] = None
        self.last_search_term = ""

    def compose(self) -> ComposeResult:
        # Clean Single-line Header Bar with Title and Path Breadcrumb
        with Horizontal(id="editor-header-bar"):
            yield Label("", id="editor-header-title")
            yield Label("", id="editor-path-breadcrumb")

        # Interactive Find & Replace Collapsible Panel
        with Vertical(id="find-replace-panel"):
            with Horizontal(classes="find-row"):
                yield Input(placeholder="Find in file...", id="find-input")
                yield Button("Next ▶", id="btn-find-next", variant="primary")
                yield Button("◀ Prev", id="btn-find-prev")
                yield Label("0 matches", id="find-status-label")
                yield Button("✖ Close", id="btn-find-close")
            with Horizontal(classes="find-row"):
                yield Input(placeholder="Replace with...", id="replace-input")
                yield Button("Replace ↵", id="btn-replace")
                yield Button("Replace All ⚡", id="btn-replace-all", variant="warning")

        # Main Text Editing Surface
        text_area = TextArea(
            self.initial_content,
            id="main-text-area",
            show_line_numbers=True,
            soft_wrap=True,
            theme=self.active_theme,
        )
        self.active_language = self.detect_language()
        if self.active_language and self.active_language in getattr(text_area, "available_languages", set()):
            text_area.language = self.active_language
        yield text_area

        # Bottom Area containing Status Bar and Action Bar
        with Vertical(id="editor-bottom-container"):
            # Mouse Interactive Status Bar
            with Horizontal(id="editor-status-bar"):
                with Horizontal(id="status-left"):
                    yield Button("📍 Ln 1, Col 1", id="sb-pos", classes="status-bar-btn")
                    yield Label(" │ 1 lines │ 0 B", id="status-stats-label")
                with Horizontal(id="status-right"):
                    yield Button("🔤 Syntax", id="sb-syntax", classes="status-bar-btn")
                    yield Button("🎨 VS Code", id="sb-theme", classes="status-bar-btn")
                    yield Button("🔄 Wrap: On", id="sb-wrap", classes="status-bar-btn")
                    yield Label(" │ UTF-8", id="status-encoding-label")

            # Compact Mouse-Interactive Bottom Action Bar (Non-redundant & Screen-fit)
            with Horizontal(id="editor-bottom-bar"):
                yield Button("💾 Save", id="bot-save")
                yield Button("💾 Save & Exit", id="bot-save-exit")
                yield Button("🔍 Find", id="bot-find")
                yield Button("❓ Help", id="bot-help")
                yield Button("❌ Exit", id="bot-exit")

    def on_mount(self) -> None:
        self.update_header()
        self.update_status_bar()
        self.query_one("#main-text-area", TextArea).focus()

    def detect_language(self) -> Optional[str]:
        """Detect language syntax based on file extension."""
        _, ext = os.path.splitext(self.file_path)
        return EXT_TO_LANGUAGE.get(ext.lower())

    def update_header(self) -> None:
        """Update the top title row with icon, filename, modified badge, and elevation status."""
        filename = os.path.basename(self.file_path)
        file_icon = get_file_icon(filename)
        mod_badge = " [bold yellow]● Modified[/bold yellow]" if self.is_modified else ""
        admin_badge = " [bold red]🔒 [Admin][/bold red]" if self.is_admin else ""
        new_badge = " [bold green](New File)[/bold green]" if self.is_new_file else ""

        title = f"{file_icon} [bold white]{filename}[/bold white]{new_badge}{mod_badge}{admin_badge}"
        self.query_one("#editor-header-title", Label).update(title)

        # Format clean breadcrumb
        home = os.path.expanduser("~")
        if self.file_path.startswith(home):
            rel = os.path.relpath(self.file_path, home)
            path_display = f"~ / {rel}"
        else:
            path_display = self.file_path
        self.query_one("#editor-path-breadcrumb", Label).update(f"[dim]{path_display}[/dim]")

    def update_status_bar(self) -> None:
        """Update status buttons and metrics."""
        text_area = self.query_one("#main-text-area", TextArea)
        row, col = text_area.cursor_location
        total_lines = len(text_area.text.splitlines()) or 1
        size_bytes = len(text_area.text.encode("utf-8"))
        size_str = format_bytes(size_bytes)
        wrap_label = "🔄 Wrap: On" if self.soft_wrap_enabled else "🔄 Wrap: Off"
        lang_name = (self.active_language or "Plain Text").capitalize()

        # Update button labels
        self.query_one("#sb-pos", Button).label = f"📍 Ln {row + 1}, Col {col + 1}"
        self.query_one("#status-stats-label", Label).update(f" │ {total_lines} lines │ {size_str}")
        self.query_one("#sb-syntax", Button).label = f"🔤 {lang_name}"
        self.query_one("#sb-theme", Button).label = f"🎨 {self.active_theme.replace('_', ' ').capitalize()}"
        self.query_one("#sb-wrap", Button).label = wrap_label

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Track modifications in real time."""
        if not self.is_modified:
            self.is_modified = True
            self.update_header()
        self.update_status_bar()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Track cursor movements in real time."""
        self.update_status_bar()

    # --------------------------------------------------------------------------
    # Mouse Interactive Button Handlers
    # --------------------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id in ("tb-save", "bot-save"):
            self.action_save_file()
        elif btn_id in ("tb-save-exit", "bot-save-exit"):
            self.action_save_and_exit()
        elif btn_id in ("tb-find", "bot-find"):
            self.action_toggle_find()
        elif btn_id == "tb-undo":
            self.action_undo_action()
        elif btn_id == "tb-redo":
            self.action_redo_action()
        elif btn_id in ("tb-goto", "sb-pos", "bot-goto"):
            self.action_goto_line()
        elif btn_id in ("tb-wrap", "sb-wrap"):
            self.action_toggle_wrap()
        elif btn_id in ("tb-theme", "sb-theme"):
            self.action_pick_theme()
        elif btn_id in ("tb-syntax", "sb-syntax"):
            self.action_pick_syntax()
        elif btn_id in ("tb-help", "bot-help"):
            self.action_show_help()
        elif btn_id in ("tb-exit", "bot-exit"):
            self.action_exit_editor()
        # Find & Replace Panel buttons
        elif btn_id == "btn-find-next":
            self.perform_find_direction(forward=True)
        elif btn_id == "btn-find-prev":
            self.perform_find_direction(forward=False)
        elif btn_id == "btn-find-close":
            self.query_one("#find-replace-panel").display = False
            self.query_one("#main-text-area", TextArea).focus()
        elif btn_id == "btn-replace":
            self.action_replace_single()
        elif btn_id == "btn-replace-all":
            self.action_replace_all()

    # --------------------------------------------------------------------------
    # Saving & Auto-Elevation Logic
    # --------------------------------------------------------------------------
    def action_save_and_exit(self) -> None:
        """Save file content and exit immediately. If save fails or is cancelled, stay in editor."""
        saved = self.action_save_file()
        if saved:
            self.exit(True)

    def action_save_file(self) -> bool:
        """Save file content, automatically escalating to admin with consent if restricted."""
        text_area = self.query_one("#main-text-area", TextArea)
        content = text_area.text

        # 1. Try normal save
        try:
            parent_dir = os.path.dirname(self.file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.is_modified = False
            self.is_new_file = False
            self.update_header()
            self.update_status_bar()
            self.notify("File saved successfully! ✔", severity="information")
            return True
        except (PermissionError, OSError):
            # 2. Seamless elevation prompt
            return self.prompt_and_elevate_save(content)

    def prompt_and_elevate_save(self, content: str) -> bool:
        """Prompt user in terminal for administrator authorization and save elevated."""
        from rich.console import Console
        from rich.prompt import Confirm
        from ..elevation import elevated_file_write

        success = False
        err = ""
        declined = False

        with self.suspend():
            c = Console()
            c.print(f"\n[bold yellow]🔒 Admin rights are required to save changes to '[white]{self.file_path}[/white]'.[/bold yellow]")
            if not Confirm.ask("   [bold cyan]Save with administrator rights?[/bold cyan]", default=True, console=c):
                declined = True
            else:
                success, err = elevated_file_write(
                    path=self.file_path,
                    content=content,
                    reason=f"Save changes to protected file '{self.file_path}'",
                    console=c,
                )

        if success:
            self.is_admin = True
            self.is_modified = False
            self.is_new_file = False
            self.update_header()
            self.update_status_bar()
            self.notify("Saved successfully with admin rights! 🔒", severity="information")
            return True
        elif declined:
            self.notify("Elevation cancelled. File was NOT saved.", severity="warning")
            return False
        else:
            self.notify(f"Save failed: {err or 'Permission denied'}", severity="error")
            return False

    # --------------------------------------------------------------------------
    # Exit & Unsaved Changes Guard
    # --------------------------------------------------------------------------
    def action_handle_escape(self) -> None:
        """Handle Esc key: close find panel if open, else exit editor."""
        find_panel = self.query_one("#find-replace-panel")
        if find_panel.display:
            find_panel.display = False
            self.query_one("#main-text-area", TextArea).focus()
            return
        self.action_exit_editor()

    def action_exit_editor(self) -> None:
        """Exit editor, prompting if modified."""
        if not self.is_modified:
            self.exit(False)
            return

        def handle_modal_choice(choice: Optional[str]) -> None:
            if choice == "save":
                saved = self.action_save_file()
                if saved:
                    self.exit(True)
            elif choice == "discard":
                self.exit(False)
            else:
                self.query_one("#main-text-area", TextArea).focus()

        self.push_screen(UnsavedChangesModal(os.path.basename(self.file_path)), handle_modal_choice)

    # --------------------------------------------------------------------------
    # Find & Replace System
    # --------------------------------------------------------------------------
    def action_toggle_find(self) -> None:
        """Toggle Find & Replace bar."""
        find_panel = self.query_one("#find-replace-panel")
        if find_panel.display:
            find_panel.display = False
            self.query_one("#main-text-area", TextArea).focus()
        else:
            find_panel.display = True
            find_input = self.query_one("#find-input", Input)
            find_input.focus()
            if find_input.value:
                self.perform_find_direction(forward=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "find-input":
            self.perform_find_direction(forward=True)
        elif event.input.id == "replace-input":
            self.action_replace_single()

    def perform_find_direction(self, forward: bool = True) -> None:
        """Search query forward or backward from cursor."""
        query = self.query_one("#find-input", Input).value
        status_label = self.query_one("#find-status-label", Label)
        if not query:
            status_label.update("Empty search")
            return

        text_area = self.query_one("#main-text-area", TextArea)
        full_text = text_area.text
        if not full_text:
            status_label.update("No text")
            return

        query_lower = query.lower()
        full_lower = full_text.lower()
        count = full_lower.count(query_lower)

        if count == 0:
            status_label.update("0 matches")
            return

        lines = full_text.splitlines(keepends=True)
        cursor_row, cursor_col = text_area.cursor_location
        cur_offset = sum(len(lines[i]) for i in range(min(cursor_row, len(lines)))) + cursor_col

        if forward:
            next_idx = full_lower.find(query_lower, cur_offset + 1)
            if next_idx == -1:
                next_idx = full_lower.find(query_lower, 0)
        else:
            next_idx = full_lower.rfind(query_lower, 0, max(0, cur_offset - 1))
            if next_idx == -1:
                next_idx = full_lower.rfind(query_lower)

        if next_idx != -1:
            running_len = 0
            found_row = 0
            found_col = 0
            for r_idx, line in enumerate(lines):
                line_len = len(line)
                if running_len + line_len > next_idx:
                    found_row = r_idx
                    found_col = next_idx - running_len
                    break
                running_len += line_len

            text_area.move_cursor((found_row, found_col))
            text_area.scroll_cursor_visible()
            status_label.update(f"{count} match{'es' if count != 1 else ''}")

    def action_replace_single(self) -> None:
        """Replace current match and advance to next."""
        find_query = self.query_one("#find-input", Input).value
        replace_text = self.query_one("#replace-input", Input).value
        if not find_query:
            return

        text_area = self.query_one("#main-text-area", TextArea)
        full_text = text_area.text
        if not full_text:
            return

        lines = full_text.splitlines(keepends=True)
        row, col = text_area.cursor_location
        cur_offset = sum(len(lines[i]) for i in range(min(row, len(lines)))) + col

        if full_text[cur_offset : cur_offset + len(find_query)].lower() == find_query.lower():
            new_text = full_text[:cur_offset] + replace_text + full_text[cur_offset + len(find_query):]
            text_area.load_text(new_text)
            self.notify("Replaced 1 occurrence ✔")
            self.perform_find_direction(forward=True)
        else:
            self.perform_find_direction(forward=True)

    def action_replace_all(self) -> None:
        """Replace all occurrences across entire file."""
        find_query = self.query_one("#find-input", Input).value
        replace_text = self.query_one("#replace-input", Input).value
        if not find_query:
            return

        text_area = self.query_one("#main-text-area", TextArea)
        full_text = text_area.text
        if not full_text:
            return

        pattern = re.compile(re.escape(find_query), re.IGNORECASE)
        new_text, count = pattern.subn(replace_text, full_text)
        if count > 0:
            text_area.load_text(new_text)
            self.query_one("#find-status-label", Label).update("0 matches")
            self.notify(f"Replaced {count} occurrence(s)! ✔", severity="information")
        else:
            self.notify("No matches found to replace.", severity="warning")

    # --------------------------------------------------------------------------
    # Jump to Line, Theme, Syntax, Wrap & Undo/Redo
    # --------------------------------------------------------------------------
    def action_goto_line(self) -> None:
        """Prompt to jump directly to a line number."""
        text_area = self.query_one("#main-text-area", TextArea)
        total_lines = len(text_area.text.splitlines()) or 1
        cur_line = text_area.cursor_location[0] + 1

        def handle_goto_result(target_line: Optional[int]) -> None:
            if target_line is not None:
                text_area.move_cursor((target_line - 1, 0))
                text_area.scroll_cursor_visible()
                self.update_status_bar()
                self.notify(f"Jumped to line {target_line}")
            text_area.focus()

        self.push_screen(GotoLineModal(cur_line, total_lines), handle_goto_result)

    def action_pick_theme(self) -> None:
        """Open theme picker modal."""
        def handle_theme_result(chosen_theme: Optional[str]) -> None:
            if chosen_theme:
                self.active_theme = chosen_theme
                text_area = self.query_one("#main-text-area", TextArea)
                text_area.theme = chosen_theme
                self.update_status_bar()
                self.notify(f"Theme switched to: {chosen_theme}")
            self.query_one("#main-text-area", TextArea).focus()

        self.push_screen(ThemePickerModal(), handle_theme_result)

    def action_pick_syntax(self) -> None:
        """Open syntax picker modal."""
        def handle_syntax_result(chosen_lang: Optional[str]) -> None:
            text_area = self.query_one("#main-text-area", TextArea)
            if chosen_lang and chosen_lang in getattr(text_area, "available_languages", set()):
                self.active_language = chosen_lang
                text_area.language = chosen_lang
                self.notify(f"Syntax highlighted as: {chosen_lang.capitalize()}")
            else:
                self.active_language = None
                text_area.language = None
                self.notify("Syntax set to Plain Text")
            self.update_status_bar()
            text_area.focus()

        self.push_screen(SyntaxPickerModal(), handle_syntax_result)

    def action_toggle_wrap(self) -> None:
        """Toggle soft wrap."""
        self.soft_wrap_enabled = not self.soft_wrap_enabled
        self.query_one("#main-text-area", TextArea).soft_wrap = self.soft_wrap_enabled
        self.update_status_bar()
        self.notify(f"Word wrap {'enabled' if self.soft_wrap_enabled else 'disabled'}")

    def action_undo_action(self) -> None:
        """Undo last text edit."""
        self.query_one("#main-text-area", TextArea).action_undo()
        self.notify("Undo", severity="information")

    def action_redo_action(self) -> None:
        """Redo last text edit."""
        self.query_one("#main-text-area", TextArea).action_redo()
        self.notify("Redo", severity="information")

    def action_show_help(self) -> None:
        """Display help cheat sheet modal."""
        self.push_screen(EditorHelpModal())


def run_mini_editor(
    file_path: str,
    initial_content: str = "",
    is_new_file: bool = False,
    is_admin: bool = False,
) -> bool:
    """Launch the modern EasyCLI Mini Editor app."""
    app = EditorApp(
        file_path=file_path,
        initial_content=initial_content,
        is_new_file=is_new_file,
        is_admin=is_admin,
    )
    result = app.run()
    return bool(result)
