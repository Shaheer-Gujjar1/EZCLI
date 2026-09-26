"""CLI orchestrator for the Internet Speed Test command."""

import sys
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from ..elevation import elevated_package_install
from .speedtest_engine import execute_speedtest, has_speedtest_cli


def run_speedtest_cli(console: Optional[Console] = None) -> None:
    """Entry point for `ez speedtest`."""
    if console is None:
        console = Console()

    # Step 1: If speedtest-cli is missing, offer install or automatic fallback
    if not has_speedtest_cli() and sys.stdin.isatty():
        console.print(
            Panel(
                "⚡ [bold cyan]speedtest-cli is not currently installed[/bold cyan]\n\n"
                "EasyCLI can use its built-in fast HTTP download/upload engine,\n"
                "or install [bold green]speedtest-cli[/bold green] for global multi-region Ookla server testing.\n\n"
                "Would you like EasyCLI to install [bold green]speedtest-cli[/bold green] now via administrator helper?",
                title="[bold cyan]Enhanced Speedtest Available[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        try:
            if Confirm.ask("[bold cyan]Install speedtest-cli?[/bold cyan]", default=False):
                elevated_package_install(
                    ["speedtest-cli"],
                    reason="Install speedtest-cli for network bandwidth testing",
                    task_description="Install speedtest-cli",
                    console=console,
                )
        except (KeyboardInterrupt, EOFError):
            pass

    # Step 2: Interactive TUI mode
    if sys.stdout.isatty():
        from ..main import check_textual_installed

        if check_textual_installed(console):
            from .speedtest_tui import SpeedtestApp

            app = SpeedtestApp()
            app.run()
            return

    # Step 3: Headless / Rich console fallback
    console.print("[dim]Testing connection latency and bandwidth...[/dim]")
    res = execute_speedtest()

    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        title="⚡ Internet Speed Test Results",
    )
    table.add_column("Metric", width=22)
    table.add_column("Measured Value", width=24)
    table.add_column("Quality Assessment", width=34)

    table.add_row("⚡ Ping (Latency)", f"{res.ping_ms} ms", "Optimal" if res.ping_ms < 40 else "Standard")
    table.add_row("⬇️ Download Speed", f"{res.download_mbps} Mbps", "High Speed" if res.download_mbps > 50 else "Standard")
    table.add_row("⬆️ Upload Speed", f"{res.upload_mbps} Mbps", "Fast" if res.upload_mbps > 20 else "Standard")

    console.print(table)
    console.print(
        Panel(
            f"Server: [bold white]{res.server_name}[/bold white] ({res.server_country})  |  ISP: [bold]{res.isp}[/bold]\n"
            f"Rating: {res.rating}",
            border_style="green",
            box=box.ROUNDED,
        )
    )
