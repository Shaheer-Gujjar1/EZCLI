"""Search file engine and interactive CLI for EasyCLI (ez search-file).

Provides:
- Fuzzy file search by name starting from /home
- Optional system-wide search ('/') with safe automatic administrator elevation
- Rich results table with emoji icons, file sizes, and timestamps
- Interactive selection to open file, copy path to clipboard, or edit with EasyCLI
"""

import base64
import datetime
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .elevation import elevated_search_files
from .explorer.file_icons import get_file_icon
from .privileged_helper import format_bytes


def fuzzy_match_score(query: str, target: str) -> float:
    """Compute fuzzy match score between query and target filename.

    Returns score from 0.0 (no match) to 100.0 (exact match).
    """
    q = query.strip().lower()
    t = target.strip().lower()

    if not q or not t:
        return 0.0

    # 1. Exact match
    if t == q:
        return 100.0

    # 2. Exact match without file extension
    base, _ = os.path.splitext(t)
    if base == q:
        return 95.0

    # 3. Prefix match
    if t.startswith(q):
        return 90.0

    # 4. Word boundary / acronym match (e.g. 'tw' -> 'test_wifi.py')
    parts = [p for p in t.replace("_", " ").replace("-", " ").replace(".", " ").split() if p]
    if len(parts) >= 2 and len(q) <= len(parts):
        initials = "".join(p[0] for p in parts)
        if initials.startswith(q) or q in initials:
            return 82.0

    # 5. Case-insensitive substring match
    if q in t:
        ratio = len(q) / max(1, len(t))
        return 70.0 + min(15.0, ratio * 15.0)

    # 6. Subsequence match (all chars of query appear in target in order)
    idx = 0
    matched = 0
    for ch in q:
        pos = t.find(ch, idx)
        if pos == -1:
            break
        idx = pos + 1
        matched += 1

    if matched == len(q):
        ratio = len(q) / max(1, len(t))
        return 50.0 + min(15.0, ratio * 15.0)

    return 0.0


def search_home_directory(term: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """Scan /home for files and directories matching term fuzzy."""
    clean_term = term.strip().lower()
    if not clean_term:
        return []

    # Target /home; fallback to user home directory if /home is empty or absent
    search_root = "/home"
    if not os.path.exists(search_root) or not os.listdir(search_root):
        search_root = os.path.expanduser("~")

    # Skip trash, cache, and build caches for fast traversal
    skip_dirs = {
        ".local/share/Trash",
        ".Trash",
        ".cache",
        "__pycache__",
    }

    results: List[Dict[str, Any]] = []

    try:
        for current_dir, dirs, files in os.walk(search_root, topdown=True, followlinks=False):
            # Prune known junk/cache subdirectories
            dirs[:] = [
                d for d in dirs
                if not any(skip in os.path.join(current_dir, d) for skip in skip_dirs)
            ]

            items_to_check = [(f, False) for f in files] + [(d, True) for d in dirs]
            for item_name, is_dir in items_to_check:
                score = fuzzy_match_score(clean_term, item_name)
                if score >= 50.0:
                    full_path = os.path.join(current_dir, item_name)
                    size_bytes = 0
                    size_str = "-"
                    mtime_str = "Unknown"

                    try:
                        st = os.stat(full_path, follow_symlinks=False)
                        if not is_dir:
                            size_bytes = st.st_size
                            size_str = format_bytes(st.st_size)
                        mtime_dt = datetime.datetime.fromtimestamp(st.st_mtime)
                        mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pass

                    icon = get_file_icon(item_name, is_dir=is_dir)

                    results.append({
                        "name": item_name,
                        "path": full_path,
                        "is_dir": is_dir,
                        "size_bytes": size_bytes,
                        "size_str": size_str,
                        "mtime_str": mtime_str,
                        "score": score,
                        "icon": icon,
                    })

                    if len(results) >= max_results * 2:
                        dirs.clear()
                        break

            if len(results) >= max_results * 2:
                break

    except Exception:
        pass

    # Sort results by score descending, then shorter name, then newer mtime
    results.sort(key=lambda x: (x.get("score", 0.0), -len(x.get("name", ""))), reverse=True)
    return results[:max_results]


def search_system_root(
    term: str,
    max_results: int = 50,
    console: Optional[Console] = None,
) -> List[Dict[str, Any]]:
    """Scan entire system ('/') for files matching term using administrator privileges."""
    c = console or Console()
    c.print("🔍 [bold cyan]Scanning system-wide ('/') with administrator privileges...[/bold cyan]")

    success, raw_results, err = elevated_search_files(
        root_dir="/",
        term=term,
        max_results=max_results,
        console=c,
    )

    if not success or not raw_results:
        if err:
            c.print(f"[dim yellow]System search note:[/dim yellow] {err}")
        return []

    # Enrich elevated results with icons
    results: List[Dict[str, Any]] = []
    for item in raw_results:
        item_name = item.get("name", "")
        is_dir = item.get("is_dir", False)
        item["icon"] = get_file_icon(item_name, is_dir=is_dir)
        results.append(item)

    return results


def copy_path_to_clipboard(path: str) -> bool:
    """Copy given path string to system clipboard using multiple strategies."""
    copied = False

    # Strategy 1: Wayland wl-copy
    if shutil.which("wl-copy"):
        try:
            subprocess.run(
                ["wl-copy"],
                input=path.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=True,
            )
            copied = True
        except Exception:
            pass

    # Strategy 2: X11 xclip
    if not copied and shutil.which("xclip"):
        try:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=path.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=True,
            )
            copied = True
        except Exception:
            pass

    # Strategy 3: X11 xsel
    if not copied and shutil.which("xsel"):
        try:
            subprocess.run(
                ["xsel", "--clipboard", "--input"],
                input=path.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=True,
            )
            copied = True
        except Exception:
            pass

    # Strategy 4: ANSI OSC 52 Escape Sequence (works in all modern terminals)
    try:
        b64 = base64.b64encode(path.encode("utf-8")).decode("ascii")
        sys.stdout.write(f"\033]52;c;{b64}\a")
        sys.stdout.flush()
        copied = True
    except Exception:
        pass

    return copied


def open_path_in_system(path: str) -> Tuple[bool, str]:
    """Open the file or folder using system default application."""
    if not os.path.exists(path):
        return False, f"Path '{path}' no longer exists."

    if shutil.which("xdg-open"):
        try:
            subprocess.Popen(
                ["xdg-open", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True, f"Opened '{os.path.basename(path)}' with system default application."
        except Exception as e:
            return False, f"Failed to launch xdg-open: {e}"

    return False, "No default graphical opener ('xdg-open') found on system."


def edit_path_in_easycli(path: str, console: Console) -> None:
    """Launch the file in EasyCLI's built-in file editor."""
    if os.path.isdir(path):
        console.print("[bold yellow]Cannot edit a directory.[/bold yellow] Please select a file.")
        return

    try:
        from .edit_cli import run_cli_edit_file

        class EditArgs:
            target = path

        run_cli_edit_file(args=EditArgs(), console=console)
    except Exception as e:
        console.print(f"[bold red]Failed to launch file editor:[/bold red] {e}")


def render_search_results_table(
    results: List[Dict[str, Any]],
    term: str,
    scope_label: str,
    console: Console,
) -> None:
    """Render a clean, rich results table."""
    table = Table(
        title=f"🔍 File Search Results for [bold cyan]'{term}'[/bold cyan] ({len(results)} found in [bold]{scope_label}[/bold])",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        title_style="bold white",
    )

    table.add_column("#", justify="right", style="bold cyan")
    table.add_column("Type", justify="center")
    table.add_column("File Name", style="bold white")
    table.add_column("Location / Directory", style="dim cyan")
    table.add_column("Size", justify="right", style="white")
    table.add_column("Modified", justify="center", style="dim white")

    for idx, item in enumerate(results, start=1):
        name = item.get("name", "")
        path = item.get("path", "")
        dir_name = os.path.dirname(path) or "/"
        size_str = item.get("size_str", "-")
        mtime_str = item.get("mtime_str", "-")
        icon = item.get("icon", "📄")

        table.add_row(
            str(idx),
            icon,
            name,
            dir_name,
            size_str,
            mtime_str,
        )

    console.print(table)


def interactive_select_and_act(
    results: List[Dict[str, Any]],
    term: str,
    console: Console,
    searched_system: bool = False,
) -> None:
    """Prompt user to select a result to Open, Copy Path, or Edit, or search system-wide."""
    current_results = list(results)
    system_done = searched_system

    while True:
        if not current_results:
            return

        # Prompt hint banner
        hint_text = (
            "[bold green][1-N][/bold green] Select file to Open / Copy Path   "
            "[bold yellow][s][/bold yellow] 🌐 Search entire system ('/')   "
            "[dim][q] Quit[/dim]"
            if not system_done
            else "[bold green][1-N][/bold green] Select file to Open / Copy Path   [dim][q] Quit[/dim]"
        )

        console.print(
            Panel(
                f"{hint_text}\n"
                f"[dim]Didn't find what you were looking for? Press [/dim][bold yellow]'s'[/bold yellow][dim] to search system-wide with admin privileges.[/dim]"
                if not system_done
                else f"{hint_text}",
                border_style="cyan" if not system_done else "dim",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

        try:
            choice = Prompt.ask("👉 Enter choice", default="q").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Search closed.[/dim]")
            return

        if choice.lower() in ("q", "quit", "exit"):
            console.print("[dim]Search closed.[/dim]")
            return

        # Handle system search option
        if choice.lower() == "s":
            if system_done:
                console.print("ℹ️ [dim]System-wide search has already been performed.[/dim]")
                continue

            system_results = search_system_root(term, max_results=50, console=console)
            system_done = True

            if system_results:
                current_results = system_results
                render_search_results_table(
                    current_results,
                    term,
                    scope_label="Entire System ('/')",
                    console=console,
                )
            else:
                console.print(
                    Panel(
                        f"❌ No matches found for [bold cyan]'{term}'[/bold cyan] anywhere on the system.",
                        border_style="red",
                        box=box.ROUNDED,
                    )
                )
            continue

        # Validate numeric choice
        try:
            idx = int(choice)
            if idx < 1 or idx > len(current_results):
                console.print(f"[bold red]Invalid number.[/bold red] Please enter 1 to {len(current_results)}.")
                continue
        except ValueError:
            console.print("[bold red]Invalid option.[/bold red] Enter a number, 's' for system search, or 'q' to quit.")
            continue

        selected_item = current_results[idx - 1]
        name = selected_item.get("name", "")
        path = selected_item.get("path", "")
        icon = selected_item.get("icon", "📄")
        size_str = selected_item.get("size_str", "-")
        mtime_str = selected_item.get("mtime_str", "-")

        # Action sub-menu
        console.print(
            Panel(
                f"[bold cyan]{icon} {name}[/bold cyan]\n"
                f"[dim]📍 Path:[/dim] [white]{path}[/white]\n"
                f"[dim]📊 Size:[/dim] {size_str}   [dim]🕒 Modified:[/dim] {mtime_str}\n\n"
                f"  [bold cyan][1][/bold cyan] 📂 Open in default application\n"
                f"  [bold cyan][2][/bold cyan] 📋 Copy path to clipboard\n"
                f"  [bold cyan][3][/bold cyan] ✏️ Edit with EasyCLI Editor\n"
                f"  [bold cyan][q][/bold cyan] ❌ Back to search list",
                title="[bold yellow]Select Action[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )

        try:
            act = Prompt.ask("👉 Action", choices=["1", "2", "3", "q"], default="1").strip()
        except (KeyboardInterrupt, EOFError):
            continue

        if act == "1":
            ok, msg = open_path_in_system(path)
            if ok:
                console.print(f"🚀 [bold green]Success:[/bold green] {msg}")
            else:
                console.print(f"⚠️ [bold yellow]Notice:[/bold yellow] {msg}")
        elif act == "2":
            copy_path_to_clipboard(path)
            console.print(
                Panel(
                    f"📋 [bold green]Path copied to clipboard![/bold green]\n\n"
                    f"[bold white]{path}[/bold white]",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
        elif act == "3":
            edit_path_in_easycli(path, console=console)
        elif act == "q":
            continue


def run_search_file_cli(
    term: Optional[str] = None,
    console: Optional[Console] = None,
) -> None:
    """Main CLI entrypoint for 'ez search-file <term>'."""
    c = console or Console()

    clean_term = (term or "").strip()
    if not clean_term:
        c.print(
            Panel(
                "🔍 [bold cyan]EasyCLI Fast File Search[/bold cyan]\n\n"
                "[bold white]Usage:[/bold white] [green]ez search-file <term>[/green]\n\n"
                "Searches [bold]/home[/bold] first by filename using fuzzy matching, "
                "with an option to search the entire system [bold]'/'[/bold] with administrator rights.\n\n"
                "[bold white]Examples:[/bold white]\n"
                "  ez search-file wifi_app.py\n"
                "  ez search-file nginx.conf\n"
                "  ez search-file report\n",
                title="[bold cyan]Search File Guide[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        return

    # Step 1: Search in /home first
    with c.status(f"🔍 Searching in [bold]/home[/bold] for '{clean_term}'...", spinner="dots"):
        home_results = search_home_directory(clean_term, max_results=50)

    # Step 2: If results found in /home
    if home_results:
        render_search_results_table(
            home_results,
            clean_term,
            scope_label="/home",
            console=c,
        )
        interactive_select_and_act(
            home_results,
            clean_term,
            console=c,
            searched_system=False,
        )
        return

    # Step 3: Zero results in /home -> Prompt for system-wide search ('/')
    c.print(
        Panel(
            f"❌ [bold red]File not found in /home for '[bold white]{clean_term}[/bold white]'.[/bold red]\n\n"
            "Would you like to expand the search to the entire system ([bold cyan]'/'[/bold cyan])? "
            "Safe administrator elevation will be used to scan protected directories.",
            title="[bold yellow]No Matches in /home[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    try:
        answer = Prompt.ask("📁 Wanna look in whole system? '/'", choices=["y", "n", "Y", "N"], default="y").strip().lower()
    except (KeyboardInterrupt, EOFError):
        c.print("\n[dim]Search cancelled.[/dim]")
        return

    if answer != "y":
        c.print("[dim]Search cancelled. No changes were made.[/dim]")
        return

    # Step 4: System-wide scan
    system_results = search_system_root(clean_term, max_results=50, console=c)
    if system_results:
        render_search_results_table(
            system_results,
            clean_term,
            scope_label="Entire System ('/')",
            console=c,
        )
        interactive_select_and_act(
            system_results,
            clean_term,
            console=c,
            searched_system=True,
        )
    else:
        c.print(
            Panel(
                f"❌ No matches found for [bold cyan]'{clean_term}'[/bold cyan] anywhere on the system.",
                border_style="red",
                box=box.ROUNDED,
            )
        )
