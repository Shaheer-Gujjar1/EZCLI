"""Interactive CLI workflow for 'ez uninstall <name>' subcommand."""

from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .collectors import collect_installed_packages
from .elevation import elevated_package_uninstall


def render_uninstall_warning_card(console: Console, target: Dict[str, Any]) -> None:
    """Display a clear, reassuring warning card detailing the software item being removed."""
    name = target.get("name", "")
    app_id = target.get("app_id", name)
    version = target.get("version", "Unknown")
    size = target.get("size", "-")
    plat_name = target.get("platform_name", "APT")
    plat_icon = target.get("platform_icon", "📦")
    desc = target.get("description", "")

    info_table = Table(box=None, show_header=False, padding=(0, 1))
    info_table.add_column("Key", style="bold cyan", width=18)
    info_table.add_column("Value", style="white")

    info_table.add_row("Application", f"[bold red]{name}[/bold red]")
    info_table.add_row("Package / App ID", f"[bold]{app_id}[/bold]")
    info_table.add_row("Source", f"{plat_icon} {plat_name}")
    info_table.add_row("Installed Version", version or "[dim]N/A[/dim]")
    if size and size != "-":
        info_table.add_row("Space Occupied", size)
    if desc:
        info_table.add_row("Description", desc)

    warning_text = (
        "\n[bold yellow]⚠️ IMPACT NOTICE:[/bold yellow]\n"
        "• This action will remove the application binaries and desktop launcher shortcuts.\n"
        "• Personal documents and user configurations in your home directory are preserved.\n"
        "• Administrator privileges are required to perform this removal."
    )

    content = Table(box=None, show_header=False, padding=(0, 0))
    content.add_column("Body")
    content.add_row(info_table)
    content.add_row(warning_text)

    console.print(
        Panel(
            content,
            title=f"[bold yellow]⚠️ Confirm Uninstallation: {name} ({plat_icon} {plat_name})[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def run_cli_uninstall(app_name: Optional[str] = None, console: Optional[Console] = None) -> None:
    """
    Safely uninstall an application across APT, Flatpak, or Snap.
    Features:
      - Automatic installed-package lookup and multi-source resolution
      - Clear pre-removal warning card
      - One single consent prompt followed by non-cached admin password authentication
      - Zero password caching or storage
    """
    console = console or Console()

    # 1. Prompt for application name if not supplied
    clean_query = (app_name or "").strip()
    if not clean_query:
        try:
            clean_query = Prompt.ask("[bold cyan]Enter application or package name to uninstall[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Uninstallation cancelled.[/dim]")
            return

    if not clean_query:
        console.print("[yellow]No package specified. Uninstallation cancelled.[/yellow]")
        return

    # 2. Search installed software across APT, Flatpak, and Snap
    with console.status(f"[bold cyan]Searching installed applications for '{clean_query}'...[/bold cyan]", spinner="dots"):
        data = collect_installed_packages(clean_query)

    matches: List[Dict[str, Any]] = data.get("matches", [])

    # Exact matches take priority
    q_lower = clean_query.lower()
    exact_matches: List[Dict[str, Any]] = []
    fuzzy_matches: List[Dict[str, Any]] = []

    for item in matches:
        name_lower = item.get("name", "").lower()
        app_id = item.get("app_id", "").lower()
        app_suffix = app_id.split(".")[-1] if "." in app_id else ""

        if name_lower == q_lower or app_id == q_lower or app_suffix == q_lower:
            exact_matches.append(item)
        else:
            fuzzy_matches.append(item)

    candidates = exact_matches if exact_matches else fuzzy_matches

    # 3. Handle not found
    if not candidates:
        tips_table = Table(box=None, show_header=False, padding=(0, 1))
        tips_table.add_column("Icon", style="bold cyan", width=3)
        tips_table.add_column("Guidance", style="white")
        tips_table.add_row("🔍", f"No installed application named '[bold cyan]{clean_query}[/bold cyan]' was found.")
        tips_table.add_row("📋", "List installed software with [bold green]ez installed-packages[/bold green] to check exact names.")
        tips_table.add_row("📦", "Search the software catalog with [bold green]ez package-search <name>[/bold green] to check available packages.")

        console.print(
            Panel(
                tips_table,
                title="[bold yellow]Application Not Found[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 1),
            )
        )
        return

    # 4. If multiple candidates exist:
    # If they are different sources for the same app or distinct packages, let user pick
    chosen_targets: List[Dict[str, Any]] = []
    if len(candidates) > 1:
        console.print(f"\n[bold cyan]Multiple matching installations were found for '{clean_query}':[/bold cyan]")
        for idx, item in enumerate(candidates, 1):
            plat_icon = item.get("platform_icon", "📦")
            plat_name = item.get("platform_name", "APT")
            version_str = f" (v{item['version']})" if item.get("version") else ""
            console.print(
                f"  [bold yellow][{idx}][/bold yellow] {plat_icon} [bold]{item['name']}[/bold] "
                f"[dim]({item.get('app_id', item['name'])}){version_str}[/dim]"
            )
        console.print(f"  [bold yellow][{len(candidates) + 1}][/bold yellow] 💥 [bold red]Uninstall from ALL listed sources[/bold red]\n")

        try:
            choice = Prompt.ask(
                f"Select option [1-{len(candidates) + 1}] (or press Enter to cancel)",
                default="",
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Uninstallation cancelled.[/dim]")
            return

        if not choice or not choice.isdigit():
            console.print("[yellow]Uninstallation cancelled.[/yellow]")
            return

        c_idx = int(choice)
        if 1 <= c_idx <= len(candidates):
            chosen_targets = [candidates[c_idx - 1]]
        elif c_idx == len(candidates) + 1:
            chosen_targets = list(candidates)
        else:
            console.print("[yellow]Invalid choice. Uninstallation cancelled.[/yellow]")
            return
    else:
        chosen_targets = [candidates[0]]

    # 5. Process each target with warning card, single consent, and admin elevation
    for target in chosen_targets:
        console.print()
        render_uninstall_warning_card(console, target)
        console.print()

        # Single user consent prompt
        try:
            approved = Confirm.ask(
                f"⚠️ Are you sure you want to completely uninstall '[bold red]{target.get('name')}[/bold red]'?",
                default=False,
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Uninstallation cancelled.[/dim]")
            return

        if not approved:
            console.print(f"[yellow]Uninstallation of '{target.get('name')}' cancelled by user.[/yellow]")
            continue

        # 6. Elevated uninstallation with single password prompt (no caching)
        plat = str(target.get("platform") or "apt")
        plat_name = str(target.get("platform_name") or plat.upper())
        pkg_id: str = str(target.get("app_id") or target.get("name") or "")

        with console.status(f"[bold cyan]Uninstalling '{pkg_id}' via {plat_name}...[/bold cyan]", spinner="dots"):
            ok, _, err = elevated_package_uninstall(
                platform=plat,
                package=pkg_id,
                skip_explanation=True,  # Warning card above serves as the explanation
                console=console,
            )

        if ok:
            console.print(
                Panel(
                    f"✔ [bold green]Successfully uninstalled '{target.get('name')}' via {plat_name}![/bold green]\n\n"
                    f"[dim]Application binaries, shortcuts, and integrations have been removed from your system.[/dim]",
                    title="[bold green]Uninstallation Complete[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Failed to uninstall '{target.get('name')}' via {plat_name}:[/bold red]\n\n{err or 'Uninstallation failed.'}",
                    title="[bold red]Uninstallation Error[/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                    padding=(1, 2),
                )
            )
