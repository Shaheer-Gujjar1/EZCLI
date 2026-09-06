"""Internet connectivity checker engine and visual pipeline renderer for EasyCLI.

Checks:
1. Local router default gateway ping
2. DNS domain resolution latency
3. Public internet reachability (ICMP ping with TCP fallback)
Visual pipeline: Router → DNS → Internet (✔/✖ with latency)
Diagnostic answer: "Why internet isn't working" one line reply
"""

import json
import os
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def get_default_gateway() -> Tuple[Optional[str], Optional[str]]:
    """Detect default gateway IP and network interface.

    Returns:
        (gateway_ip, interface_name) or (None, None) if not found.
    """
    # 1. Try ip -j route
    try:
        res = subprocess.run(
            ["ip", "-j", "route"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            routes = json.loads(res.stdout)
            for r in routes:
                if r.get("dst") == "default":
                    gw = r.get("gateway")
                    dev = r.get("dev")
                    if gw:
                        return str(gw), str(dev) if dev else None
    except Exception:
        pass

    # 2. Try standard ip route
    try:
        res = subprocess.run(
            ["ip", "route"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.splitlines():
                if line.startswith("default"):
                    parts = line.split()
                    gw = None
                    dev = None
                    if "via" in parts:
                        idx = parts.index("via")
                        if idx + 1 < len(parts):
                            gw = parts[idx + 1]
                    if "dev" in parts:
                        idx = parts.index("dev")
                        if idx + 1 < len(parts):
                            dev = parts[idx + 1]
                    if gw:
                        return gw, dev
    except Exception:
        pass

    # 3. Fallback to /proc/net/route
    try:
        with open("/proc/net/route", "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                fields = line.strip().split()
                if len(fields) >= 3:
                    iface = fields[0]
                    dest = fields[1]
                    gw_hex = fields[2]
                    if dest == "00000000" and gw_hex != "00000000":
                        # Convert 8-char hex (little-endian) to IPv4
                        octets = [
                            str(int(gw_hex[i : i + 2], 16))
                            for i in (6, 4, 2, 0)
                        ]
                        return ".".join(octets), iface
    except Exception:
        pass

    return None, None


def get_dns_resolvers() -> List[str]:
    """Retrieve configured DNS nameservers from /etc/resolv.conf."""
    resolvers: List[str] = []
    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] not in resolvers:
                        resolvers.append(parts[1])
    except Exception:
        pass
    return resolvers


def ping_host(host: str, timeout: float = 2.0) -> Tuple[bool, Optional[float], str]:
    """Ping a host using system ping with timeout.

    Returns:
        (success, latency_ms, detail_message)
    """
    cmd = ["ping", "-c", "1", "-W", str(max(1, int(timeout))), host]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 1.0,
        )
        out = proc.stdout + "\n" + proc.stderr
        if proc.returncode == 0:
            # Parse round-trip time: time=X.XX ms or rtt min/avg/max/mdev = .../avg/...
            m_time = re.search(r"time=([0-9.]+)\s*ms", out)
            if m_time:
                return True, float(m_time.group(1)), f"Responded in {float(m_time.group(1)):.1f} ms"
            m_rtt = re.search(r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*[0-9.]+/([0-9.]+)/", out)
            if m_rtt:
                return True, float(m_rtt.group(1)), f"Responded in {float(m_rtt.group(1)):.1f} ms"
            return True, None, "Host responded to ping"
        else:
            if "Destination Host Unreachable" in out:
                return False, None, "Destination host unreachable"
            elif "100% packet loss" in out or "0 received" in out:
                return False, None, "Request timed out (100% packet loss)"
            elif "Permission denied" in out:
                return False, None, "Ping permission denied"
            return False, None, f"Ping failed with exit code {proc.returncode}"
    except subprocess.TimeoutExpired:
        return False, None, f"Ping timed out after {timeout:.1f}s"
    except PermissionError:
        return False, None, "Admin permission required for raw ping"
    except Exception as e:
        return False, None, str(e)


def check_router(timeout: float = 2.0) -> Dict[str, Any]:
    """Stage 1: Check connectivity and ping latency to the local router / default gateway."""
    gw_ip, iface = get_default_gateway()
    if not gw_ip:
        return {
            "success": False,
            "target": "None",
            "interface": iface or "None",
            "latency_ms": None,
            "status_str": "✖ No Gateway",
            "detail": "No default gateway found (network disconnected)",
        }

    success, latency, msg = ping_host(gw_ip, timeout=timeout)
    if success:
        return {
            "success": True,
            "target": gw_ip,
            "interface": iface or "default",
            "latency_ms": latency,
            "status_str": "✔ Reachable",
            "detail": f"Router {gw_ip} active via {iface or 'network'}",
        }
    else:
        return {
            "success": False,
            "target": gw_ip,
            "interface": iface or "default",
            "latency_ms": None,
            "status_str": "✖ Unreachable",
            "detail": f"Cannot reach router {gw_ip} ({msg})",
        }


def check_dns(
    domains: Optional[List[str]] = None,
    timeout: float = 2.0,
) -> Dict[str, Any]:
    """Stage 2: Check DNS resolution latency for reliable public domain names."""
    if domains is None:
        domains = ["google.com", "cloudflare.com", "wikipedia.org"]

    resolvers = get_dns_resolvers()
    resolver_str = ", ".join(resolvers) if resolvers else "system default"

    for domain in domains:
        t0 = time.perf_counter()
        try:
            # Set default timeout for socket operations
            orig_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                addr_info = socket.getaddrinfo(
                    domain, 80, socket.AF_UNSPEC, socket.SOCK_STREAM
                )
            finally:
                socket.setdefaulttimeout(orig_timeout)

            latency_ms = (time.perf_counter() - t0) * 1000
            if addr_info and addr_info[0][4]:
                resolved_ip = addr_info[0][4][0]
                return {
                    "success": True,
                    "target": domain,
                    "resolved_ip": resolved_ip,
                    "resolvers": resolvers,
                    "latency_ms": latency_ms,
                    "status_str": "✔ Resolved",
                    "detail": f"Resolved {domain} to {resolved_ip}",
                }
        except socket.gaierror:
            continue
        except socket.timeout:
            continue
        except Exception:
            continue

    return {
        "success": False,
        "target": domains[0] if domains else "domain",
        "resolved_ip": None,
        "resolvers": resolvers,
        "latency_ms": None,
        "status_str": "✖ Resolution Failed",
        "detail": f"Failed to resolve domain names (resolvers: {resolver_str})",
    }


def check_internet_reachability(
    hosts: Optional[List[str]] = None,
    timeout: float = 2.0,
) -> Dict[str, Any]:
    """Stage 3: Check end-to-end internet connectivity via public anycast IPs.

    Attempts ICMP ping first; falls back to TCP handshake (port 53/443) if ICMP is blocked.
    """
    if hosts is None:
        hosts = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]

    for host in hosts:
        # 1. ICMP Ping check
        success, latency, msg = ping_host(host, timeout=timeout)
        if success:
            return {
                "success": True,
                "target": host,
                "method": "ICMP Ping",
                "latency_ms": latency,
                "status_str": "✔ Reachable",
                "detail": f"Public endpoint {host} reachable ({msg})",
            }

        # 2. TCP Fallback (in case ICMP echo is dropped by gateway or firewall)
        try:
            t0 = time.perf_counter()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            # Try DNS TCP port 53 or HTTPS 443
            res = sock.connect_ex((host, 53))
            latency_ms = (time.perf_counter() - t0) * 1000
            sock.close()
            if res == 0:
                return {
                    "success": True,
                    "target": host,
                    "method": "TCP (Port 53)",
                    "latency_ms": latency_ms,
                    "status_str": "✔ Reachable",
                    "detail": f"Public endpoint {host} reachable via TCP",
                }
        except Exception:
            pass

    return {
        "success": False,
        "target": hosts[0] if hosts else "public internet",
        "method": "ICMP/TCP",
        "latency_ms": None,
        "status_str": "✖ Offline / Blocked",
        "detail": "No response from public internet endpoints (1.1.1.1, 8.8.8.8)",
    }


def get_diagnostic_reason(results: Dict[str, Any]) -> str:
    """Produce the exact one-line answer to 'Why internet isn't working'."""
    router = results.get("router", {})
    dns = results.get("dns", {})
    internet = results.get("internet", {})

    r_ok = router.get("success", False)
    d_ok = dns.get("success", False)
    i_ok = internet.get("success", False)

    # 1. All systems green
    if r_ok and d_ok and i_ok:
        return "All systems operational — your internet connection is active and healthy!"

    # 2. Router failed
    if not r_ok:
        if router.get("target") in ("None", None, ""):
            return "You are not connected to any network (no local Wi-Fi or Ethernet connection detected)."
        gw = router.get("target", "router")
        if d_ok or i_ok:
            # Router dropped ICMP but external connection works
            return "Internet is working! (Note: Your local router blocks ping, but external traffic flows normally)."
        return f"Cannot reach your local router ({gw}) — check your Wi-Fi connection, Ethernet cable, or router power."

    # 3. Router OK, but both DNS and Internet failed
    if r_ok and not d_ok and not i_ok:
        return "Connected to your local router, but no internet access — your ISP may be down or the WAN cable is unplugged."

    # 4. Router OK, Internet OK, but DNS failed
    if r_ok and not d_ok and i_ok:
        resolvers = dns.get("resolvers", [])
        res_str = ", ".join(resolvers) if resolvers else "system default"
        return f"Connected to the internet, but DNS resolution failed — check your DNS servers ({res_str})."

    # 5. Router OK, DNS OK, but Internet IP ping/TCP failed
    if r_ok and d_ok and not i_ok:
        return "Connected to router and DNS is responding, but external internet endpoints are unreachable — traffic may be blocked by a firewall or captive portal."

    return "Internet connection is degraded or unstable — one or more verification stages failed."


def diagnose_internet(timeout: float = 2.0) -> Dict[str, Any]:
    """Execute the full 3-stage connectivity diagnosis and compute diagnostic reasoning."""
    router = check_router(timeout=timeout)
    dns = check_dns(timeout=timeout)
    internet = check_internet_reachability(timeout=timeout)

    results: Dict[str, Any] = {
        "router": router,
        "dns": dns,
        "internet": internet,
    }
    results["diagnostic_reason"] = get_diagnostic_reason(results)
    results["is_healthy"] = (
        router.get("success", False)
        and dns.get("success", False)
        and internet.get("success", False)
    )
    return results


def format_stage_pipeline_token(name: str, stage_data: Dict[str, Any]) -> str:
    """Format an individual stage token with emoji, success symbol, and latency."""
    success = stage_data.get("success", False)
    lat = stage_data.get("latency_ms")

    if success:
        symbol = "[bold green]✔[/bold green]"
        if lat is not None:
            lat_str = f"[green]({lat:.1f} ms)[/green]"
        else:
            lat_str = "[green](OK)[/green]"
        return f"[bold white]{name}[/bold white] {symbol} {lat_str}"
    else:
        symbol = "[bold red]✖[/bold red]"
        err_hint = "Offline" if "No Gateway" in stage_data.get("status_str", "") else "Failed"
        return f"[bold white]{name}[/bold white] {symbol} [red]({err_hint})[/red]"


def render_internet_check(console: Optional[Console] = None) -> None:
    """Render the full interactive/visual internet diagnostics report."""
    if console is None:
        console = Console()

    with console.status("[bold cyan]Diagnosing network: testing router, DNS, and internet reachability...[/bold cyan]"):
        data = diagnose_internet(timeout=2.0)

    router = data["router"]
    dns = data["dns"]
    internet = data["internet"]
    reason = data["diagnostic_reason"]
    is_healthy = data["is_healthy"]

    # 1. Visual Pipeline Banner
    t_router = format_stage_pipeline_token("Router", router)
    t_dns = format_stage_pipeline_token("DNS", dns)
    t_internet = format_stage_pipeline_token("Internet", internet)

    pipeline_str = f"   {t_router}   [bold cyan]➔[/bold cyan]   {t_dns}   [bold cyan]➔[/bold cyan]   {t_internet}   "

    banner_panel = Panel(
        pipeline_str,
        title="[bold cyan]📶 Internet Connection Pipeline[/bold cyan]",
        box=box.ROUNDED,
        border_style="green" if is_healthy else "yellow" if (internet.get("success") or dns.get("success")) else "red",
        padding=(1, 2),
    )
    console.print(banner_panel)

    # 2. Detailed Breakdown Table
    table = Table(
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        title="[bold]Detailed Stage Diagnostics[/bold]",
    )
    table.add_column("Stage", style="bold white", width=18)
    table.add_column("Target / Host", style="cyan", width=22)
    table.add_column("Latency", justify="right", width=12)
    table.add_column("Status", justify="center", width=14)
    table.add_column("Diagnostic Details", style="dim white")

    # Row 1: Router
    r_lat = f"{router['latency_ms']:.1f} ms" if router.get("latency_ms") is not None else "—"
    r_stat = f"[bold green]{router['status_str']}[/bold green]" if router.get("success") else f"[bold red]{router['status_str']}[/bold red]"
    r_target = f"{router.get('target', 'None')} ({router.get('interface', '')})" if router.get('target') != 'None' else "None"
    table.add_row("🏠 Local Router", r_target, r_lat, r_stat, router.get("detail", ""))

    # Row 2: DNS
    d_lat = f"{dns['latency_ms']:.1f} ms" if dns.get("latency_ms") is not None else "—"
    d_stat = f"[bold green]{dns['status_str']}[/bold green]" if dns.get("success") else f"[bold red]{dns['status_str']}[/bold red]"
    table.add_row("🔍 DNS Resolution", str(dns.get("target", "Domain")), d_lat, d_stat, dns.get("detail", ""))

    # Row 3: Internet
    i_lat = f"{internet['latency_ms']:.1f} ms" if internet.get("latency_ms") is not None else "—"
    i_stat = f"[bold green]{internet['status_str']}[/bold green]" if internet.get("success") else f"[bold red]{internet['status_str']}[/bold red]"
    table.add_row("🌍 Internet Access", str(internet.get("target", "Public IP")), i_lat, i_stat, internet.get("detail", ""))

    console.print(table)

    # 3. Diagnostic Verdict Panel: "Why internet isn't working" one line reply
    verdict_border = "green" if is_healthy else "yellow" if (internet.get("success") or dns.get("success")) else "red"
    verdict_panel = Panel(
        f"[bold white]{reason}[/bold white]",
        title="[bold yellow]💡 Why internet isn't working[/bold yellow]",
        box=box.ROUNDED,
        border_style=verdict_border,
        padding=(0, 2),
    )
    console.print(verdict_panel)
    console.print()
