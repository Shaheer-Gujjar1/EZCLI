"""Backend Wi-Fi management engine for EasyCLI.

Wraps nmcli to:
- Scan for nearby wireless networks with signal quality and security detection
- Check active Wi-Fi status and connection parameters
- Connect to open or password-protected networks
- Disconnect from active wireless connections
"""

from dataclasses import dataclass
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class WifiNetwork:
    """Represents a discovered wireless access point."""

    ssid: str
    bssid: str
    signal: int
    bars: str
    security: str
    security_display: str
    is_secured: bool
    in_use: bool
    freq: str
    channel: str
    rate: str


def parse_terse_line(line: str) -> List[str]:
    """Split a terse nmcli line by unescaped colons.

    In nmcli -t mode, colons within data fields are escaped with a backslash (\\:).
    """
    fields: List[str] = []
    current: List[str] = []
    escaped = False

    for ch in line:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(ch)
    fields.append("".join(current))
    return fields


def format_security(sec_raw: str) -> Tuple[bool, str]:
    """Format raw security string into a user-friendly badge with emoji.

    Returns:
        (is_secured, display_string)
    """
    sec = (sec_raw or "").strip()
    if not sec or sec in ("--", "none", "Open"):
        return False, "🔓 Open (No Password)"

    sec_upper = sec.upper()
    if "WPA3" in sec_upper and "WPA2" in sec_upper:
        return True, "🔒 WPA2/WPA3 Personal"
    elif "WPA3" in sec_upper:
        return True, "🔒 WPA3 Personal"
    elif "WPA2" in sec_upper:
        return True, "🔒 WPA2 Personal"
    elif "WPA1" in sec_upper or "WPA " in sec_upper:
        return True, "🔒 WPA Personal"
    elif "WEP" in sec_upper:
        return True, "🔒 WEP (Insecure)"
    elif "ENTERPRISE" in sec_upper or "802.1X" in sec_upper:
        return True, "🔒 Enterprise (802.1X)"
    else:
        return True, f"🔒 {sec}"


def format_signal_bars(signal: int) -> str:
    """Format signal percentage into aesthetic Unicode volume bars and emoji."""
    pct = max(0, min(100, signal))
    if pct >= 75:
        bars = "▂▄▆█"
        icon = "📶"
    elif pct >= 50:
        bars = "▂▄▆_"
        icon = "📶"
    elif pct >= 25:
        bars = "▂▄__"
        icon = "📶"
    else:
        bars = "▂___"
        icon = "📶"
    return f"{bars} {pct}% {icon}"


def format_freq_band(freq_str: str, channel: str) -> str:
    """Format frequency in MHz to user-friendly band title (e.g. 5 GHz, 2.4 GHz)."""
    m = re.search(r"(\d+)", freq_str)
    ch_str = f"Ch {channel}" if channel else ""
    if m:
        mhz = int(m.group(1))
        if mhz >= 5000:
            band = "5 GHz"
        elif mhz >= 2400:
            band = "2.4 GHz"
        else:
            band = f"{mhz} MHz"
        return f"{band} ({ch_str})" if ch_str else band
    return ch_str or freq_str


class WifiManager:
    """Manages wireless operations using nmcli with fallback handling."""

    def __init__(self) -> None:
        self.nmcli_path = shutil.which("nmcli")

    def is_wifi_available(self) -> Tuple[bool, str]:
        """Check if nmcli and wireless interface hardware are available."""
        if not self.nmcli_path:
            return False, "NetworkManager CLI ('nmcli') is not installed. Please install 'network-manager'."

        try:
            res = subprocess.run(
                [self.nmcli_path, "-t", "-f", "DEVICE,TYPE,STATE", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            if res.returncode == 0:
                has_wifi_dev = False
                for line in res.stdout.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[1] == "wifi":
                        has_wifi_dev = True
                        break
                if not has_wifi_dev:
                    return False, "No Wi-Fi interface detected on this machine."
                return True, "Wi-Fi is available."
        except Exception as e:
            return False, f"Unable to query network devices: {e}"

        return True, "Wi-Fi is available."

    def get_active_wifi(self) -> Optional[Dict[str, Any]]:
        """Retrieve details of the currently connected Wi-Fi network."""
        if not self.nmcli_path:
            return None

        try:
            res = subprocess.run(
                [self.nmcli_path, "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            if res.returncode != 0:
                return None

            active_dev = None
            active_con = None
            for line in res.stdout.splitlines():
                parts = parse_terse_line(line)
                if len(parts) >= 4 and parts[1] == "wifi" and "connected" in parts[2].lower():
                    active_dev = parts[0]
                    active_con = parts[3]
                    break

            if not active_con or active_con == "--" or not active_dev:
                return None

            nmcli_bin = self.nmcli_path
            dev_name = active_dev

            # Get IP and signal for active connection
            ip_addr = "Unknown"
            signal_pct = 0
            try:
                res_ip = subprocess.run(
                    [nmcli_bin, "-t", "-f", "IP4.ADDRESS", "dev", "show", dev_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3,
                )
                if res_ip.returncode == 0 and res_ip.stdout.strip():
                    ip_addr = res_ip.stdout.splitlines()[0].split("/")[0].strip()
            except Exception:
                pass

            return {
                "ssid": active_con,
                "interface": active_dev,
                "ip": ip_addr,
                "signal": signal_pct,
            }
        except Exception:
            return None

    def scan_networks(self, rescan: bool = True) -> List[WifiNetwork]:
        """Scan and return a list of available Wi-Fi networks sorted by signal strength."""
        if not self.nmcli_path:
            return []

        # Trigger background rescan if requested
        if rescan:
            try:
                subprocess.run(
                    [self.nmcli_path, "dev", "wifi", "rescan"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass

        try:
            res = subprocess.run(
                [
                    self.nmcli_path,
                    "-t",
                    "-f",
                    "IN-USE,SSID,BSSID,MODE,CHAN,FREQ,RATE,SIGNAL,BARS,SECURITY",
                    "dev",
                    "wifi",
                    "list",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=6,
            )
            if res.returncode != 0:
                return []

            networks: List[WifiNetwork] = []
            seen_ssids: Dict[str, WifiNetwork] = {}

            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                parts = parse_terse_line(line)
                if len(parts) < 10:
                    continue

                in_use_raw, ssid, bssid, mode, chan, freq, rate, signal_raw, bars_raw, sec_raw = (
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                    parts[4],
                    parts[5],
                    parts[6],
                    parts[7],
                    parts[8],
                    parts[9],
                )

                in_use = (in_use_raw.strip() == "*")
                ssid_clean = ssid.strip() or "[Hidden Network]"

                try:
                    signal_int = int(signal_raw.strip())
                except ValueError:
                    signal_int = 0

                is_sec, sec_disp = format_security(sec_raw)
                bars_formatted = format_signal_bars(signal_int)
                freq_band = format_freq_band(freq, chan)

                net = WifiNetwork(
                    ssid=ssid_clean,
                    bssid=bssid.strip(),
                    signal=signal_int,
                    bars=bars_formatted,
                    security=sec_raw.strip(),
                    security_display=sec_disp,
                    is_secured=is_sec,
                    in_use=in_use,
                    freq=freq_band,
                    channel=chan.strip(),
                    rate=rate.strip(),
                )

                # Keep the entry with highest signal or in-use status
                if ssid_clean not in seen_ssids:
                    seen_ssids[ssid_clean] = net
                else:
                    existing = seen_ssids[ssid_clean]
                    if net.in_use or (not existing.in_use and net.signal > existing.signal):
                        seen_ssids[ssid_clean] = net

            networks = list(seen_ssids.values())
            # Sort: active connection first, then by signal strength descending
            networks.sort(key=lambda n: (not n.in_use, -n.signal, n.ssid.lower()))
            return networks
        except Exception:
            return []

    def connect_network(
        self,
        ssid: str,
        password: Optional[str] = None,
        bssid: Optional[str] = None,
        timeout: float = 20.0,
    ) -> Tuple[bool, str]:
        """Connect to a specified Wi-Fi network.

        Returns:
            (success: bool, message: str)
        """
        if not self.nmcli_path:
            return False, "NetworkManager CLI ('nmcli') is not available."

        cmd = [self.nmcli_path, "dev", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])
        if bssid:
            cmd.extend(["bssid", bssid])

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            out = proc.stdout.strip() + " " + proc.stderr.strip()
            if proc.returncode == 0:
                return True, f"Successfully connected to '{ssid}'!"
            else:
                # Interpret common NetworkManager errors
                if "Secrets were required" in out or "passwords" in out.lower():
                    return False, "Connection failed: Incorrect Wi-Fi password."
                elif "timeout" in out.lower():
                    return False, "Connection timed out. Check router signal or password."
                elif "not found" in out.lower():
                    return False, f"Network '{ssid}' was not found. Please refresh and try again."
                elif "permission" in out.lower() or "authorization" in out.lower():
                    return False, "Permission denied by system policy to activate network connection."
                return False, f"Failed to connect: {out.strip()}"
        except subprocess.TimeoutExpired:
            return False, f"Connection timed out after {int(timeout)} seconds."
        except Exception as e:
            return False, f"Unexpected error connecting to '{ssid}': {e}"

    def disconnect_wifi(self, interface: Optional[str] = None) -> Tuple[bool, str]:
        """Disconnect the active Wi-Fi connection."""
        if not self.nmcli_path:
            return False, "NetworkManager CLI ('nmcli') is not available."

        active = self.get_active_wifi()
        if not active:
            return False, "No active Wi-Fi connection to disconnect."

        iface = interface or active.get("interface")
        if not iface:
            return False, "No wireless interface identified."

        try:
            proc = subprocess.run(
                [self.nmcli_path, "dev", "disconnect", iface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
            )
            if proc.returncode == 0:
                return True, f"Successfully disconnected from '{active.get('ssid', 'Wi-Fi')}."
            return False, f"Disconnect failed: {proc.stderr.strip() or proc.stdout.strip()}"
        except Exception as e:
            return False, f"Failed to disconnect: {e}"
