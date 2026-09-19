"""CLI dispatcher and direct-mode handler for ez startup-apps."""

import sys
from typing import List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .startup_app import StartupAppsApp
from .startup_engine import (
    StartupItem,
    scan_boot_services,
    scan_login_apps,
    toggle_boot_service,
    toggle_login_app,
)


def run_direct_startup_mode(target: str, console: Console) -> None:
    """Handle direct-mode single-item toggle: ez startup-apps <name>."""
    clean_target = target.strip().lower()

    login_items = scan_login_apps()
    service_items = scan_boot_services()
    all_items: List[StartupItem] = login_items + service_items

    # 1. Search for matches
    exact_matches = [it for it in all_items if it.name.lower() == clean_target or it.id.lower() == clean_target]
    matches = exact_matches or [it for it in all_items if clean_target in it.name.lower() or clean_target in it.id.lower()]

    if not matches:
        console.print(
            Panel(
                f"[bold red]No startup application or boot service found matching '[white]{target}[/white]'.[/bold red]\n\n"
                "[dim]Tip: Run 'ez startup-apps' without arguments to browse all items interactively.[/dim]",
                title="[bold red]Item Not Found[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        return

    item = matches[0]

    # 2. Render Single Item Card
    type_badge = "🚀 [cyan]Login Application[/cyan]" if item.item_type == "login" else "⚙️ [blue]System Boot Service[/blue]"
    status_badge = "[bold green]✔ Enabled[/bold green]" if item.state == "Enabled" else "[dim]✖ Disabled[/dim]"
    crit_badge = "\n[bold red]⚠️ Status: CRITICAL SYSTEM SERVICE (Locked)[/bold red]" if item.is_critical else ""

    next_state = "Disabled" if item.state == "Enabled" else "Enabled"
    next_effect = (
        f"This application will {'NOT ' if item.state == 'Enabled' else ''}start automatically when you log in."
        if item.item_type == "login"
        else f"This system service will {'NOT ' if item.state == 'Enabled' else ''}start automatically at system boot."
    )

    content = (
        f"[bold cyan]Name:[/bold cyan]        {item.name}\n"
        f"[bold cyan]Identifier:[/bold cyan]  {item.id}\n"
        f"[bold cyan]Category:[/bold cyan]    {type_badge}\n"
        f"[bold cyan]Status:[/bold cyan]      {status_badge}{crit_badge}\n"
        f"[bold cyan]Command/Path:[/bold cyan]{item.exec_cmd or item.file_path}\n\n"
        f"[yellow]Toggle Effect (Next Boot):[/yellow]\n{next_effect}"
    )

    console.print(
        Panel(
            content,
            title=f"🚀 Startup Item: [bold white]{item.name}[/bold white]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    # 3. Toggle prompt
    if item.item_type == "service" and item.state == "Enabled" and item.is_critical:
        console.print(
            Panel(
                f"[bold red]CRITICAL SAFETY WARNING:[/bold red]\n"
                f"Disabling '{item.name}' may cause network, audio, graphical, or system login failure.\n"
                f"To confirm disabling this service, you must type [bold red]DISABLE[/bold red]:",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        typed_conf = Prompt.ask("Type confirmation", console=console).strip()
        if typed_conf != "DISABLE":
            console.print("[yellow]Action cancelled. Critical service remains enabled.[/yellow]")
            return
    else:
        if not Confirm.ask(f"Do you want to switch '{item.name}' to [bold]{next_state}[/bold]?", default=True, console=console):
            console.print("[dim]Action cancelled. No changes made.[/dim]")
            return

    # 4. Apply toggle
    if item.item_type == "login":
        ok, msg = toggle_login_app(item)
    else:
        ok, msg = toggle_boot_service(item, console=console)

    if ok:
        console.print(
            Panel(
                f"✨ [bold green]{msg}[/bold green]",
                title="[bold green]Success[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]Failed to toggle item:[/bold red]\n\n{msg}",
                title="[bold red]Error[/bold red]",
                border_style="red",
                box=box.ROUNDED,
            )
        )


def run_startup_apps_cli(target: Optional[str] = None, console: Optional[Console] = None) -> None:
    """Entrypoint for ez startup-apps."""
    if console is None:
        console = Console()

    if target and target.strip():
        run_direct_startup_mode(target.strip(), console)
    else:
        app = StartupAppsApp()
        app.run()
