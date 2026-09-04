"""Modern, beginner-friendly Terminal Text Editor for EasyCLI v0.3."""

import glob
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure local user venv is accessible if system python lacks textual
venv_site = glob.glob(os.path.expanduser("~/.local/share/ezcli/venv/lib/python*/site-packages"))
if venv_site and venv_site[0] not in sys.path:
    sys.path.insert(0, venv_site[0])

from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)

from ..collectors import format_bytes


EXT_TO_LANGUAGE = {
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


class UnsavedChangesModal(ModalScreen[str]):
    """Modal dialog asking user to save or discard changes upon exit."""

    DEFAULT_CSS = """
    UnsavedChangesModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #unsaved-dialog {
        width: 60;
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
                "Would you like to save before closing?",
                id="unsaved-message",
            )
            with Horizontal(id="unsaved-buttons"):
                yield Button("Save & Exit [s]", variant="primary", id="btn-save")
                yield Button("Discard [d]", variant="error", id="btn-discard")
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


class EditorHelpModal(ModalScreen[None]):
    """Modal cheat sheet for editor shortcuts."""

    DEFAULT_CSS = """
    EditorHelpModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #help-dialog {
        width: 66;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #help-title {
        text-style: bold;
        color: $accent;
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
            "[bold cyan]EasyCLI Mini Editor Shortcuts[/bold cyan]\n\n"
            "  [bold green]Ctrl + S[/bold green]      Save file (auto-elevates if write-protected)\n"
            "  [bold green]Ctrl + Q / Esc[/bold green] Exit editor (prompts if unsaved changes exist)\n"
            "  [bold green]Ctrl + F[/bold green]      Find / Search text in file\n"
            "  [bold green]Ctrl + W[/bold green]      Toggle word wrap (soft wrap)\n"
            "  [bold green]Ctrl + Z[/bold green]      Undo edit\n"
            "  [bold green]Ctrl + Y[/bold green]      Redo edit\n"
            "  [bold green]F2 / Ctrl + H[/bold green] Show this help cheat sheet\n\n"
            "[dim]Press Esc or Enter to return to editing.[/dim]"
        )
        with Vertical(id="help-dialog"):
            yield Label("📖 Mini Editor Help", id="help-title")
            yield Static(help_text, id="help-content")
            with Horizontal(id="help-button-container"):
                yield Button("Got it! [Enter]", variant="primary", id="btn-close-help")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_dismiss_help(self) -> None:
        self.dismiss(None)


class EditorApp(App[bool]):
    """Modern beginner-friendly Terminal Text Editor for EasyCLI."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #editor-header-bar {
        dock: top;
        height: 1;
        background: $surface-darken-1;
        color: $text;
        padding: 0 1;
    }

    #editor-header-title {
        text-style: bold;
    }

    #find-bar {
        dock: top;
        height: 3;
        background: $surface-darken-2;
        border: round $accent;
        padding: 0 1;
        display: none;
    }

    #find-input {
        width: 1fr;
    }

    #find-status {
        width: auto;
        padding: 0 1;
        content-align: center middle;
        color: $text-muted;
    }

    #main-text-area {
        width: 100%;
        height: 1fr;
        border: none;
    }

    #editor-status-bar {
        dock: bottom;
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
    }

    #status-left {
        width: 1fr;
    }

    #status-right {
        width: auto;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save_file", "Save [Ctrl+S]", show=True),
        Binding("ctrl+q", "exit_editor", "Exit [Ctrl+Q]", show=True),
        Binding("escape", "handle_escape", "Exit [Esc]", show=False),
        Binding("ctrl+f", "toggle_find", "Find [Ctrl+F]", show=True),
        Binding("ctrl+w", "toggle_wrap", "Wrap [Ctrl+W]", show=True),
        Binding("f2", "show_help", "Help [F2]", show=True),
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
        self.last_search_term = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="editor-header-bar"):
            yield Label("", id="editor-header-title")

        with Horizontal(id="find-bar"):
            yield Input(placeholder="Find in file... (Enter to find next, Esc to close)", id="find-input")
            yield Label("", id="find-status")
            yield Button("Next", id="find-next", variant="primary")
            yield Button("Close", id="find-close", variant="default")

        text_area = TextArea(self.initial_content, id="main-text-area", show_line_numbers=True, soft_wrap=True)
        # Configure syntax highlighting if supported
        lang = self.detect_language()
        if lang and lang in getattr(text_area, "available_languages", set()):
            text_area.language = lang
        yield text_area

        with Horizontal(id="editor-status-bar"):
            yield Label("", id="status-left")
            yield Label("", id="status-right")

        yield Footer()

    def on_mount(self) -> None:
        self.update_header()
        self.update_status_bar()
        self.query_one("#main-text-area", TextArea).focus()

    def detect_language(self) -> Optional[str]:
        """Detect language syntax based on file extension."""
        _, ext = os.path.splitext(self.file_path)
        return EXT_TO_LANGUAGE.get(ext.lower())

    def update_header(self) -> None:
        """Update the top header bar with filename, modified badge, and elevation status."""
        filename = os.path.basename(self.file_path)
        mod_badge = " [bold yellow]● (Modified)[/bold yellow]" if self.is_modified else ""
        admin_badge = " [bold red]🔒 [Admin][/bold red]" if self.is_admin else ""
        new_badge = " [bold green](New File)[/bold green]" if self.is_new_file else ""

        title = f"📝 EasyCLI Editor — [bold white]{filename}[/bold white]{new_badge}{mod_badge}{admin_badge}  [dim]({self.file_path})[/dim]"
        self.query_one("#editor-header-title", Label).update(title)

    def update_status_bar(self) -> None:
        """Update bottom status line with cursor position, line count, language, and size."""
        text_area = self.query_one("#main-text-area", TextArea)
        row, col = text_area.cursor_location
        total_lines = len(text_area.text.splitlines()) or 1
        lang_name = (self.detect_language() or "Plain Text").capitalize()
        size_bytes = len(text_area.text.encode("utf-8"))
        size_str = format_bytes(size_bytes)
        wrap_status = "Wrap: On" if self.soft_wrap_enabled else "Wrap: Off"

        left_text = f"Ln {row + 1}, Col {col + 1}  │  {total_lines} lines  │  {size_str}"
        right_text = f"UTF-8  │  {lang_name}  │  {wrap_status}"

        self.query_one("#status-left", Label).update(left_text)
        self.query_one("#status-right", Label).update(right_text)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Track modification state."""
        if not self.is_modified:
            self.is_modified = True
            self.update_header()
        self.update_status_bar()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Track cursor position movements."""
        self.update_status_bar()

    # --------------------------------------------------------------------------
    # Saving & Auto-Elevation Logic
    # --------------------------------------------------------------------------
    def action_save_file(self) -> bool:
        """Save buffer content. Automatically prompts and elevates if permission is denied."""
        text_area = self.query_one("#main-text-area", TextArea)
        content = text_area.text

        # 1. Try standard unprivileged save first
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
            # 2. Seamless automatic elevation with consent
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
        """Handle Esc key: close find bar if open, else exit editor."""
        find_bar = self.query_one("#find-bar")
        if find_bar.display:
            find_bar.display = False
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
                # Cancel: return to editing
                self.query_one("#main-text-area", TextArea).focus()

        self.push_screen(UnsavedChangesModal(os.path.basename(self.file_path)), handle_modal_choice)

    # --------------------------------------------------------------------------
    # Find / Search Feature
    # --------------------------------------------------------------------------
    def action_toggle_find(self) -> None:
        """Toggle find bar."""
        find_bar = self.query_one("#find-bar")
        if find_bar.display:
            find_bar.display = False
            self.query_one("#main-text-area", TextArea).focus()
        else:
            find_bar.display = True
            find_input = self.query_one("#find-input", Input)
            find_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "find-input":
            self.perform_find(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "find-next":
            search_val = self.query_one("#find-input", Input).value
            self.perform_find(search_val)
        elif event.button.id == "find-close":
            self.query_one("#find-bar").display = False
            self.query_one("#main-text-area", TextArea).focus()

    def perform_find(self, query: str) -> None:
        """Find next match of query in text area."""
        status_label = self.query_one("#find-status", Label)
        if not query:
            status_label.update("Empty search.")
            return

        text_area = self.query_one("#main-text-area", TextArea)
        full_text = text_area.text
        if not full_text:
            status_label.update("No text to search.")
            return

        # Simple case-insensitive search
        query_lower = query.lower()
        full_lower = full_text.lower()

        count = full_lower.count(query_lower)
        if count == 0:
            status_label.update("No matches found.")
            return

        # Calculate character index from current cursor location
        lines = full_text.splitlines(keepends=True)
        cursor_row, cursor_col = text_area.cursor_location
        cur_char_offset = sum(len(lines[i]) for i in range(min(cursor_row, len(lines)))) + cursor_col

        # Find next index after cursor
        next_idx = full_lower.find(query_lower, cur_char_offset + 1)
        if next_idx == -1:
            # Wrap around to start
            next_idx = full_lower.find(query_lower, 0)

        if next_idx != -1:
            # Convert char offset back to row, col
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
            status_label.update(f"{count} match(es)")

    # --------------------------------------------------------------------------
    # Soft Wrap & Help
    # --------------------------------------------------------------------------
    def action_toggle_wrap(self) -> None:
        """Toggle soft wrap on the text area."""
        self.soft_wrap_enabled = not self.soft_wrap_enabled
        self.query_one("#main-text-area", TextArea).soft_wrap = self.soft_wrap_enabled
        self.update_status_bar()
        self.notify(f"Word wrap {'enabled' if self.soft_wrap_enabled else 'disabled'}")

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
