"""CLI orchestrator for the UFW Firewall command."""

import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..elevation import elevated_package_install
from .firewall_engine import (
    get_firewall_status,
    is_ufw_installed,
)


def run_firewall_cli(console: Optional[Console] = None) -> None:
    """Entry point for `ez firewall`."""
    if console is None:
        console = Console()

    # Step 1: Check if ufw is installed
    if not is_ufw_installed():
        console.print(
            Panel(
                "🛡️ [bold cyan]UFW (Uncomplicated Firewall) is not installed[/bold cyan]\n\n"
                "UFW provides standard network port filtering, connection blocking, and security protection.\n\n"
                "To manage your system firewall with EasyCLI, UFW is required.\n\n"
                "Would you like EasyCLI to install [bold green]ufw[/bold green] now via the administrator helper?",
                title="[bold yellow]Firewall Tool Missing[/bold yellow]",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
        try:
            if sys.stdin.isatty() and Confirm.ask("[bold cyan]Install ufw now?[/bold cyan]", default=True):
                success = elevated_package_install(
                    ["ufw"],
                    reason="Install UFW firewall package",
                    task_description="Install UFW",
                    console=console,
                )
                if not success:
                    console.print("[bold red]Installation aborted or failed.[/bold red]")
                    return
                console.print("[bold green]✓ UFW successfully installed![/bold green]\n")
            else:
                console.print("[dim]Run 'sudo apt install ufw' to install manually.[/dim]")
                return
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return

    # Step 2: If stdout is a TTY and Textual is available, launch TUI
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .firewall_tui import FirewallApp

            app = FirewallApp()
            app.run()
            return

    # Fallback: Rich console output for headless / piped execution
    status = get_firewall_status()
    status_style = "bold green" if status.active else "bold red"
    status_text = "ACTIVE" if status.active else "INACTIVE"

    console.print(
        Panel(
            f"Status: [{status_style}]{status_text}[/{status_style}]  |  "
            f"Default Incoming: [bold]{status.default_incoming.upper()}[/bold]  |  "
            f"Default Outgoing: [bold]{status.default_outgoing.upper()}[/bold]\n"
            f"SSH Rule: {'[bold green]Protected (Port 22 Allowed)[/bold green]' if status.has_ssh_rule else '[bold yellow]Not Detected (Lockout Risk)[/bold yellow]'}",
            title="🛡️ [bold cyan]EasyCLI Firewall Status[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    if status.rules:
        table = Table(
            title="Firewall Rules",
            box=box.ROUNDED,
            border_style="cyan",
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", width=4)
        table.add_column("Action", width=10)
        table.add_column("To Port / Service", width=20)
        table.add_column("Direction", width=10)
        table.add_column("From", width=20)
        table.add_column("IP Ver", width=8)

        for rule in status.rules:
            action_colored = f"[bold green]{rule.action}[/bold green]" if rule.action == "ALLOW" else f"[bold red]{rule.action}[/bold red]"
            table.add_row(
                str(rule.index),
                action_colored,
                rule.to_port,
                rule.direction,
                rule.from_ip,
                "IPv6" if rule.v6 else "IPv4",
            )
        console.print(table)
    else:
        console.print("[dim]No numbered firewall rules configured.[/dim]")
