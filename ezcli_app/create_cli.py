"""Direct CLI handlers for ezcli create-folder and ezcli create-file."""

import os
import stat
import sys
from typing import Optional, Tuple
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .elevation import elevated_create_file, elevated_make_dir, is_root
from .file_engine import is_destination_protected


def validate_item_name(name: str) -> Tuple[bool, str]:
    """Validate that a filename or folder name is safe and valid."""
    cleaned = name.strip()
    if not cleaned:
        return False, "Name cannot be empty."
    if "\0" in cleaned:
        return False, "Name contains invalid characters (null bytes)."
    if "/" in cleaned or "\\" in cleaned:
        return False, "Path separators ('/' or '\\') are not allowed in item names."
    if cleaned in (".", ".."):
        return False, "Name cannot be '.' or '..'."
    return True, ""


def run_cli_create_folder(
    folder_name: Optional[str] = None,
    dest_dir: Optional[str] = None,
    choose_dest: bool = False,
    console: Optional[Console] = None,
    name: Optional[str] = None,
) -> None:
    """Create a new folder directly or via visual directory picker."""
    folder_name = name if name is not None else folder_name
    console = console or Console()
    effective_dest_dir = dest_dir or os.getcwd()

    # 1. If choose-directory requested or folder_name explicitly requests picker
    if choose_dest or (folder_name and folder_name.lower() in ("choose-directory", "choose", "picker", "select")):
        from .explorer.explorer_app import ExplorerApp
        console.print("[bold cyan]Opening mini explorer to choose parent directory...[/bold cyan]")
        app = ExplorerApp(mode="pick_dest", initial_dir=effective_dest_dir)
        picked = app.run()
        if not picked or not isinstance(picked, str):
            console.print("[dim]Folder creation cancelled.[/dim]")
            return
        effective_dest_dir = picked
        if folder_name and folder_name.lower() in ("choose-directory", "choose", "picker", "select"):
            folder_name = None  # Prompt for name next only if name was the keyword

    # 2. If folder name not specified, prompt user interactively
    if not folder_name:
        console.print(f"[dim]Destination location:[/dim] [cyan]{effective_dest_dir}[/cyan]")
        try:
            folder_name = Prompt.ask("[bold cyan]Enter new folder name[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

    # If folder_name contains slashes or path separators, extract directory & base name
    if "/" in folder_name or "\\" in folder_name:
        expanded = os.path.abspath(os.path.expanduser(folder_name))
        effective_dest_dir = os.path.dirname(expanded)
        folder_name = os.path.basename(expanded)

    valid, err_msg = validate_item_name(folder_name)
    if not valid:
        console.print(f"[bold red]Invalid folder name:[/bold red] {err_msg}")
        return

    target_path = os.path.join(effective_dest_dir, folder_name)

    if os.path.exists(target_path):
        console.print(f"[bold red]Error:[/bold red] An item named '[yellow]{folder_name}[/yellow]' already exists at '[cyan]{effective_dest_dir}[/cyan]'.")
        return

    # 3. Handle creation (normal user vs automatic elevation)
    created_elevated = False
    if not is_destination_protected(target_path) and not is_root():
        try:
            os.makedirs(target_path, exist_ok=False)
        except PermissionError:
            # Automatic elevation prompt
            console.print(
                "[yellow]Access denied:[/yellow] This location requires admin rights to create folders."
            )
            confirm = Confirm.ask("Create folder with admin rights? [Y/n]", default=True)
            if not confirm:
                console.print("[dim]Folder creation cancelled.[/dim]")
                return
            ok = elevated_make_dir(
                target_path,
                reason=f"Create folder '{target_path}'",
                console=console,
            )
            if not ok:
                return
            created_elevated = True
        except Exception as e:
            console.print(f"[bold red]Error creating folder:[/bold red] {e}")
            return
    else:
        # Protected destination: perform elevated creation
        if not is_root():
            ok = elevated_make_dir(
                target_path,
                reason=f"Create folder '{target_path}'",
                console=console,
            )
            if not ok:
                return
            created_elevated = True
        else:
            try:
                os.makedirs(target_path, exist_ok=False)
            except Exception as e:
                console.print(f"[bold red]Error creating folder:[/bold red] {e}")
                return

    # 4. Display modern, user-friendly success card
    badge = " 🔒 [bold yellow](Admin)[/bold yellow]" if created_elevated else ""
    summary_text = (
        f"[bold green]✔ Created folder successfully![/bold green]{badge}\n\n"
        f"📁 [bold]Folder:[/bold] [yellow]{folder_name}[/yellow]\n"
        f"📂 [bold]Location:[/bold] [cyan]{effective_dest_dir}[/cyan]\n"
        f"🔗 [bold]Full Path:[/bold] [dim]{target_path}[/dim]"
    )
    console.print()
    console.print(
        Panel(
            summary_text,
            title="[bold green]Folder Created[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def run_cli_create_file(
    file_name: Optional[str] = None,
    dest_dir: Optional[str] = None,
    choose_dest: bool = False,
    console: Optional[Console] = None,
    name: Optional[str] = None,
) -> None:
    """Create a new blank file directly or via visual directory picker."""
    file_name = name if name is not None else file_name
    console = console or Console()
    effective_dest_dir = dest_dir or os.getcwd()

    # 1. If choose-directory requested or file_name explicitly requests picker
    if choose_dest or (file_name and file_name.lower() in ("choose-directory", "choose", "picker", "select")):
        from .explorer.explorer_app import ExplorerApp
        console.print("[bold cyan]Opening mini explorer to choose destination directory...[/bold cyan]")
        app = ExplorerApp(mode="pick_dest", initial_dir=effective_dest_dir)
        picked = app.run()
        if not picked or not isinstance(picked, str):
            console.print("[dim]File creation cancelled.[/dim]")
            return
        effective_dest_dir = picked
        if file_name and file_name.lower() in ("choose-directory", "choose", "picker", "select"):
            file_name = None  # Prompt for name next only if name was the keyword

    # 2. If file name not specified, prompt user interactively
    if not file_name:
        console.print(f"[dim]Destination location:[/dim] [cyan]{effective_dest_dir}[/cyan]")
        try:
            file_name = Prompt.ask(
                "[bold cyan]Enter new file name (with extension, e.g. notes.txt)[/bold cyan]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

    # If file_name contains slashes or path separators, extract directory & base name
    if "/" in file_name or "\\" in file_name:
        expanded = os.path.abspath(os.path.expanduser(file_name))
        effective_dest_dir = os.path.dirname(expanded)
        file_name = os.path.basename(expanded)

    valid, err_msg = validate_item_name(file_name)
    if not valid:
        console.print(f"[bold red]Invalid file name:[/bold red] {err_msg}")
        return

    target_path = os.path.join(effective_dest_dir, file_name)

    if os.path.exists(target_path):
        console.print(f"[bold red]Error:[/bold red] An item named '[yellow]{file_name}[/yellow]' already exists at '[cyan]{effective_dest_dir}[/cyan]'.")
        return

    # 3. Handle creation (normal user vs automatic elevation)
    created_elevated = False
    if not is_destination_protected(target_path) and not is_root():
        try:
            # Create empty file
            with open(target_path, "x") as f:
                pass
        except PermissionError:
            console.print(
                "[yellow]Access denied:[/yellow] This location requires admin rights to create files."
            )
            confirm = Confirm.ask("Create file with admin rights? [Y/n]", default=True)
            if not confirm:
                console.print("[dim]File creation cancelled.[/dim]")
                return
            ok = elevated_create_file(
                target_path,
                reason=f"Create blank file '{target_path}'",
                console=console,
            )
            if not ok:
                return
            created_elevated = True
        except Exception as e:
            console.print(f"[bold red]Error creating file:[/bold red] {e}")
            return
    else:
        if not is_root():
            ok = elevated_create_file(
                target_path,
                reason=f"Create blank file '{target_path}'",
                console=console,
            )
            if not ok:
                return
            created_elevated = True
        else:
            try:
                with open(target_path, "x") as f:
                    pass
            except Exception as e:
                console.print(f"[bold red]Error creating file:[/bold red] {e}")
                return

    # 4. Display confirmation card
    badge = " 🔒 [bold yellow](Admin)[/bold yellow]" if created_elevated else ""
    summary_text = (
        f"[bold green]✔ Created file successfully![/bold green]{badge}\n\n"
        f"📄 [bold]File:[/bold]     [yellow]{file_name}[/yellow]\n"
        f"📂 [bold]Location:[/bold] [cyan]{effective_dest_dir}[/cyan]\n"
        f"🔗 [bold]Full Path:[/bold] [dim]{target_path}[/dim]\n"
        f"📏 [bold]Size:[/bold]      0 B (blank file)"
    )
    console.print()
    console.print(
        Panel(
            summary_text,
            title="[bold green]File Created[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
