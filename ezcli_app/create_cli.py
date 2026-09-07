"""Direct CLI handlers for ez create-folder and ez create-file."""

import os
import stat
import sys
from typing import List, Optional, Sequence, Tuple, Union
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .elevation import elevated_create_file, elevated_make_dir, is_root
from .file_engine import is_destination_protected, normalize_target_args


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


def _resolve_target_item(
    raw_target: str,
    base_dest_dir: str,
    is_folder: bool,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Validates a target item name and resolves its parent destination and clean base name.

    Returns:
        (dest_dir, clean_item_name, error_message)
    """
    cleaned = raw_target.strip()
    if is_folder:
        # Strip trailing slashes for folders (e.g., 'folder1/' -> 'folder1')
        cleaned = cleaned.rstrip("/\\")

    if not cleaned:
        return None, None, "Item name cannot be empty."

    # If an absolute path is provided (e.g. in test suites)
    if os.path.isabs(cleaned):
        dest = os.path.dirname(cleaned)
        item_name = os.path.basename(cleaned)
        valid, err = validate_item_name(item_name)
        if not valid:
            return None, None, err
        return dest, item_name, None

    # For relative items: strictly enforce current parent directory (no subfolders or traversal)
    if "/" in cleaned or "\\" in cleaned:
        kind = "folder" if is_folder else "file"
        cmd = "create-folder" if is_folder else "create-file"
        return (
            None,
            None,
            f"Subfolder paths ('{raw_target}') are not permitted. Direct creation only supports items in the current parent directory ('{base_dest_dir}'). To create in another directory, use 'ez {cmd} choose-directory'.",
        )

    valid, err = validate_item_name(cleaned)
    if not valid:
        return None, None, err

    return base_dest_dir, cleaned, None


def run_cli_create_folder(
    folder_name: Optional[Union[str, Sequence[str]]] = None,
    dest_dir: Optional[str] = None,
    choose_dest: bool = False,
    console: Optional[Console] = None,
    name: Optional[Union[str, Sequence[str]]] = None,
    raw_args: Optional[Sequence[str]] = None,
) -> None:
    """Create one or more new folders directly or via visual directory picker."""
    console = console or Console()
    effective_dest_dir = dest_dir or os.getcwd()

    # Collect all input candidates
    raw_inputs: List[str] = []
    if raw_args:
        raw_inputs.extend(raw_args)
    elif name is not None:
        if isinstance(name, str):
            raw_inputs.append(name)
        else:
            raw_inputs.extend(name)
    elif folder_name is not None:
        if isinstance(folder_name, str):
            raw_inputs.append(folder_name)
        else:
            raw_inputs.extend(folder_name)

    # 1. If choose-directory requested or explicitly present in raw inputs
    choose_requested = choose_dest or any(
        a.lower() in ("choose-directory", "choose", "picker", "select") for a in raw_inputs
    )
    filtered_inputs = [
        a for a in raw_inputs if a.lower() not in ("choose-directory", "choose", "picker", "select")
    ]

    if choose_requested:
        from .explorer.explorer_app import ExplorerApp

        console.print("[bold cyan]Opening mini explorer to choose parent directory...[/bold cyan]")
        app = ExplorerApp(mode="pick_dest", initial_dir=effective_dest_dir)
        picked = app.run()
        if not picked or not isinstance(picked, str):
            console.print("[dim]Folder creation cancelled.[/dim]")
            return
        effective_dest_dir = picked

    # 2. Normalize targets (split comma-separated and space-separated names)
    targets = normalize_target_args(filtered_inputs)

    # 3. If no folder names specified, prompt user interactively
    if not targets:
        console.print(f"[dim]Destination location:[/dim] [cyan]{effective_dest_dir}[/cyan]")
        try:
            prompt_input = Prompt.ask(
                "[bold cyan]Enter new folder name(s) (separated by commas)[/bold cyan]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

        if not prompt_input:
            console.print("[dim]Cancelled.[/dim]")
            return
        targets = normalize_target_args([prompt_input])

    if not targets:
        console.print("[bold red]Invalid folder name:[/bold red] Name cannot be empty.")
        return

    # 4. Resolve and validate all targets upfront (atomic check)
    unique_resolved: List[Tuple[str, str, str]] = []  # (dest_dir, name, full_path)
    seen_paths = set()

    for t in targets:
        dest, clean_name, err = _resolve_target_item(t, effective_dest_dir, is_folder=True)
        if err:
            console.print(f"[bold red]Invalid folder name:[/bold red] {err}")
            return
        assert dest is not None and clean_name is not None
        full_path = os.path.join(dest, clean_name)
        if full_path in seen_paths:
            continue
        seen_paths.add(full_path)
        unique_resolved.append((dest, clean_name, full_path))

    # Check for existing items on filesystem
    existing_items = [name for _, name, full_path in unique_resolved if os.path.exists(full_path)]
    if existing_items:
        if len(existing_items) == 1:
            console.print(
                f"[bold red]Error:[/bold red] An item named '[yellow]{existing_items[0]}[/yellow]' already exists at '[cyan]{effective_dest_dir}[/cyan]'."
            )
        else:
            names_str = ", ".join(f"'{n}'" for n in existing_items)
            console.print(
                f"[bold red]Error:[/bold red] Items named [yellow]{names_str}[/yellow] already exist at '[cyan]{effective_dest_dir}[/cyan]'."
            )
        return

    # 5. Handle creation (normal user vs automatic elevation)
    needs_elevation = any(is_destination_protected(p) for _, _, p in unique_resolved)
    created_elevated = False

    if needs_elevation and not is_root():
        console.print(
            "[yellow]Access denied:[/yellow] This location requires admin rights to create folders."
        )
        confirm = Confirm.ask("Create folder with admin rights? [Y/n]", default=True)
        if not confirm:
            console.print("[dim]Folder creation cancelled.[/dim]")
            return
        created_elevated = True
        for dest, clean_name, full_path in unique_resolved:
            ok = elevated_make_dir(
                full_path,
                reason=f"Create folder '{full_path}'",
                console=console,
            )
            if not ok:
                return
    else:
        # Attempt standard creation, fallback to elevation on PermissionError
        created_paths: List[str] = []
        for dest, clean_name, full_path in unique_resolved:
            try:
                os.makedirs(full_path, exist_ok=False)
                created_paths.append(full_path)
            except PermissionError:
                if not is_root():
                    console.print(
                        "[yellow]Access denied:[/yellow] This location requires admin rights to create folders."
                    )
                    confirm = Confirm.ask("Create folder with admin rights? [Y/n]", default=True)
                    if not confirm:
                        console.print("[dim]Folder creation cancelled.[/dim]")
                        return
                    created_elevated = True
                    ok = elevated_make_dir(
                        full_path,
                        reason=f"Create folder '{full_path}'",
                        console=console,
                    )
                    if not ok:
                        return
                    created_paths.append(full_path)
                else:
                    console.print(f"[bold red]Error creating folder '{clean_name}':[/bold red] Permission denied.")
                    return
            except Exception as e:
                console.print(f"[bold red]Error creating folder '{clean_name}':[/bold red] {e}")
                return

    # 6. Display modern, user-friendly success card
    badge = " 🔒 [bold yellow](Admin)[/bold yellow]" if created_elevated else ""
    if len(unique_resolved) == 1:
        dest, clean_name, full_path = unique_resolved[0]
        summary_text = (
            f"[bold green]✔ Created folder successfully![/bold green]{badge}\n\n"
            f"📁 [bold]Folder:[/bold]   [yellow]{clean_name}[/yellow]\n"
            f"📂 [bold]Location:[/bold] [cyan]{dest}[/cyan]\n"
            f"🔗 [bold]Full Path:[/bold] [dim]{full_path}[/dim]"
        )
        title = "[bold green]Folder Created[/bold green]"
    else:
        count = len(unique_resolved)
        names_list = ", ".join(name for _, name, _ in unique_resolved)
        paths_lines = "\n".join(f"   • [dim]{p}[/dim]" for _, _, p in unique_resolved)
        summary_text = (
            f"[bold green]✔ Created {count} folders successfully![/bold green]{badge}\n\n"
            f"📁 [bold]Folders:[/bold]  [yellow]{names_list}[/yellow]\n"
            f"📂 [bold]Location:[/bold] [cyan]{effective_dest_dir}[/cyan]\n\n"
            f"🔗 [bold]Full Paths:[/bold]\n{paths_lines}"
        )
        title = f"[bold green]{count} Folders Created[/bold green]"

    console.print()
    console.print(
        Panel(
            summary_text,
            title=title,
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def run_cli_create_file(
    file_name: Optional[Union[str, Sequence[str]]] = None,
    dest_dir: Optional[str] = None,
    choose_dest: bool = False,
    console: Optional[Console] = None,
    name: Optional[Union[str, Sequence[str]]] = None,
    raw_args: Optional[Sequence[str]] = None,
) -> None:
    """Create one or more new blank files directly or via visual directory picker."""
    console = console or Console()
    effective_dest_dir = dest_dir or os.getcwd()

    # Collect all input candidates
    raw_inputs: List[str] = []
    if raw_args:
        raw_inputs.extend(raw_args)
    elif name is not None:
        if isinstance(name, str):
            raw_inputs.append(name)
        else:
            raw_inputs.extend(name)
    elif file_name is not None:
        if isinstance(file_name, str):
            raw_inputs.append(file_name)
        else:
            raw_inputs.extend(file_name)

    # 1. If choose-directory requested or explicitly present in raw inputs
    choose_requested = choose_dest or any(
        a.lower() in ("choose-directory", "choose", "picker", "select") for a in raw_inputs
    )
    filtered_inputs = [
        a for a in raw_inputs if a.lower() not in ("choose-directory", "choose", "picker", "select")
    ]

    if choose_requested:
        from .explorer.explorer_app import ExplorerApp

        console.print("[bold cyan]Opening mini explorer to choose destination directory...[/bold cyan]")
        app = ExplorerApp(mode="pick_dest", initial_dir=effective_dest_dir)
        picked = app.run()
        if not picked or not isinstance(picked, str):
            console.print("[dim]File creation cancelled.[/dim]")
            return
        effective_dest_dir = picked

    # 2. Normalize targets (split comma-separated and space-separated names)
    targets = normalize_target_args(filtered_inputs)

    # 3. If no file names specified, prompt user interactively
    if not targets:
        console.print(f"[dim]Destination location:[/dim] [cyan]{effective_dest_dir}[/cyan]")
        try:
            prompt_input = Prompt.ask(
                "[bold cyan]Enter new file name(s) (with extension, e.g. notes.txt, todo.md)[/bold cyan]"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

        if not prompt_input:
            console.print("[dim]Cancelled.[/dim]")
            return
        targets = normalize_target_args([prompt_input])

    if not targets:
        console.print("[bold red]Invalid file name:[/bold red] Name cannot be empty.")
        return

    # 4. Resolve and validate all targets upfront (atomic check)
    unique_resolved: List[Tuple[str, str, str]] = []  # (dest_dir, name, full_path)
    seen_paths = set()

    for t in targets:
        dest, clean_name, err = _resolve_target_item(t, effective_dest_dir, is_folder=False)
        if err:
            console.print(f"[bold red]Invalid file name:[/bold red] {err}")
            return
        assert dest is not None and clean_name is not None
        full_path = os.path.join(dest, clean_name)
        if full_path in seen_paths:
            continue
        seen_paths.add(full_path)
        unique_resolved.append((dest, clean_name, full_path))

    # Check for existing items on filesystem
    existing_items = [name for _, name, full_path in unique_resolved if os.path.exists(full_path)]
    if existing_items:
        if len(existing_items) == 1:
            console.print(
                f"[bold red]Error:[/bold red] An item named '[yellow]{existing_items[0]}[/yellow]' already exists at '[cyan]{effective_dest_dir}[/cyan]'."
            )
        else:
            names_str = ", ".join(f"'{n}'" for n in existing_items)
            console.print(
                f"[bold red]Error:[/bold red] Items named [yellow]{names_str}[/yellow] already exist at '[cyan]{effective_dest_dir}[/cyan]'."
            )
        return

    # 5. Handle creation (normal user vs automatic elevation)
    needs_elevation = any(is_destination_protected(p) for _, _, p in unique_resolved)
    created_elevated = False

    if needs_elevation and not is_root():
        console.print(
            "[yellow]Access denied:[/yellow] This location requires admin rights to create files."
        )
        confirm = Confirm.ask("Create file with admin rights? [Y/n]", default=True)
        if not confirm:
            console.print("[dim]File creation cancelled.[/dim]")
            return
        created_elevated = True
        for dest, clean_name, full_path in unique_resolved:
            ok = elevated_create_file(
                full_path,
                reason=f"Create blank file '{full_path}'",
                console=console,
            )
            if not ok:
                return
    else:
        # Attempt standard creation, fallback to elevation on PermissionError
        created_paths: List[str] = []
        for dest, clean_name, full_path in unique_resolved:
            try:
                with open(full_path, "x"):
                    pass
                created_paths.append(full_path)
            except PermissionError:
                if not is_root():
                    console.print(
                        "[yellow]Access denied:[/yellow] This location requires admin rights to create files."
                    )
                    confirm = Confirm.ask("Create file with admin rights? [Y/n]", default=True)
                    if not confirm:
                        console.print("[dim]File creation cancelled.[/dim]")
                        return
                    created_elevated = True
                    ok = elevated_create_file(
                        full_path,
                        reason=f"Create blank file '{full_path}'",
                        console=console,
                    )
                    if not ok:
                        return
                    created_paths.append(full_path)
                else:
                    console.print(f"[bold red]Error creating file '{clean_name}':[/bold red] Permission denied.")
                    return
            except Exception as e:
                console.print(f"[bold red]Error creating file '{clean_name}':[/bold red] {e}")
                return

    # 6. Display confirmation card
    badge = " 🔒 [bold yellow](Admin)[/bold yellow]" if created_elevated else ""
    if len(unique_resolved) == 1:
        dest, clean_name, full_path = unique_resolved[0]
        summary_text = (
            f"[bold green]✔ Created file successfully![/bold green]{badge}\n\n"
            f"📄 [bold]File:[/bold]     [yellow]{clean_name}[/yellow]\n"
            f"📂 [bold]Location:[/bold] [cyan]{dest}[/cyan]\n"
            f"🔗 [bold]Full Path:[/bold] [dim]{full_path}[/dim]\n"
            f"📏 [bold]Size:[/bold]      0 B (blank file)"
        )
        title = "[bold green]File Created[/bold green]"
    else:
        count = len(unique_resolved)
        names_list = ", ".join(name for _, name, _ in unique_resolved)
        paths_lines = "\n".join(f"   • [dim]{p}[/dim]" for _, _, p in unique_resolved)
        summary_text = (
            f"[bold green]✔ Created {count} blank files successfully![/bold green]{badge}\n\n"
            f"📄 [bold]Files:[/bold]     [yellow]{names_list}[/yellow]\n"
            f"📂 [bold]Location:[/bold]  [cyan]{effective_dest_dir}[/cyan]\n\n"
            f"🔗 [bold]Full Paths:[/bold]\n{paths_lines}\n\n"
            f"📏 [bold]Total Size:[/bold] 0 B ({count} blank files)"
        )
        title = f"[bold green]{count} Files Created[/bold green]"

    console.print()
    console.print(
        Panel(
            summary_text,
            title=title,
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

