"""Backend engine for Bluetooth management wrapping bluetoothctl for EasyCLI."""

from dataclasses import dataclass
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BluetoothDevice:
    """Represents a discovered or paired Bluetooth device."""
    mac: str
    name: str
    device_type: str = "Generic Device"
    icon: str = "📡"
    paired: bool = False
    connected: bool = False
    trusted: bool = False
    blocked: bool = False
    rssi: Optional[int] = None
    bars: str = "----"


@dataclass
class BluetoothController:
    """Represents the host system's primary Bluetooth adapter."""
    available: bool
    mac: str = ""
    name: str = ""
    powered: bool = False
    discovering: bool = False
    pairable: bool = False
    raw_status: str = ""


def format_rssi_bars(rssi: Optional[int], connected: bool = False) -> str:
    """Format an RSSI integer into visual signal bars matching the Wi-Fi manager."""
    if rssi is None:
        return "▂▄▆█" if connected else "▂▄__"

    if rssi >= -60:
        return "▂▄▆█"
    elif rssi >= -75:
        return "▂▄▆_"
    elif rssi >= -85:
        return "▂▄__"
    else:
        return "▂___"


def detect_icon_and_type(icon_str: str, name: str) -> Tuple[str, str]:
    """Map bluetooth icon name or device name to an emoji icon and friendly label."""
    s = (icon_str or "").lower()
    n = (name or "").lower()

    if "audio" in s or "headset" in s or "headphone" in s or "earbuds" in n or "airpod" in n or "buds" in n:
        return "🎧", "Audio / Headset"
    elif "phone" in s or "smartphone" in s or "android" in n or "iphone" in n:
        return "📱", "Phone"
    elif "input-keyboard" in s or "keyboard" in n:
        return "⌨️", "Keyboard"
    elif "input-mouse" in s or "mouse" in n or "trackpad" in n:
        return "🖱️", "Mouse / Pointer"
    elif "computer" in s or "laptop" in n or "pc" in n:
        return "💻", "Computer"
    elif "input-gaming" in s or "controller" in n or "gamepad" in n:
        return "🎮", "Game Controller"
    elif "printer" in s:
        return "🖨️", "Printer"
    else:
        return "📡", "Wireless Device"


class BluetoothManager:
    """Manager for Bluetooth controller and devices."""

    def __init__(self) -> None:
        self.bin = shutil.which("bluetoothctl")

    def is_available(self) -> bool:
        return self.bin is not None

    def get_controller(self) -> BluetoothController:
        """Fetch current Bluetooth controller status."""
        if not self.is_available():
            return BluetoothController(available=False)

        try:
            proc = subprocess.run(
                [self.bin, "show"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            output = proc.stdout
            if "No default controller available" in output or not output.strip():
                return BluetoothController(available=False)

            mac_match = re.search(r"Controller\s+([0-9A-F:]{17})", output, re.IGNORECASE)
            name_match = re.search(r"Name:\s+(.+)$", output, re.MULTILINE)
            powered_match = re.search(r"Powered:\s+(yes|no)", output, re.IGNORECASE)
            discovering_match = re.search(r"Discovering:\s+(yes|no)", output, re.IGNORECASE)
            pairable_match = re.search(r"Pairable:\s+(yes|no)", output, re.IGNORECASE)

            return BluetoothController(
                available=True,
                mac=mac_match.group(1) if mac_match else "",
                name=name_match.group(1).strip() if name_match else "Bluetooth Adapter",
                powered=powered_match.group(1).lower() == "yes" if powered_match else False,
                discovering=discovering_match.group(1).lower() == "yes" if discovering_match else False,
                pairable=pairable_match.group(1).lower() == "yes" if pairable_match else False,
                raw_status=output,
            )
        except Exception:
            return BluetoothController(available=False)

    def scan_devices(self, timeout: int = 4) -> None:
        """Trigger an active device scan."""
        if not self.is_available():
            return
        try:
            subprocess.run(
                [self.bin, f"--timeout={timeout}", "scan", "on"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout + 2,
            )
        except Exception:
            pass

    def get_device_info(self, mac: str, fallback_name: str = "") -> BluetoothDevice:
        """Query detailed information for a specific MAC address."""
        if not self.is_available():
            return BluetoothDevice(mac=mac, name=fallback_name)

        try:
            proc = subprocess.run(
                [self.bin, "info", mac],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3,
            )
            out = proc.stdout

            name_m = re.search(r"Name:\s+(.+)$", out, re.MULTILINE)
            alias_m = re.search(r"Alias:\s+(.+)$", out, re.MULTILINE)
            paired_m = re.search(r"Paired:\s+(yes|no)", out, re.IGNORECASE)
            connected_m = re.search(r"Connected:\s+(yes|no)", out, re.IGNORECASE)
            trusted_m = re.search(r"Trusted:\s+(yes|no)", out, re.IGNORECASE)
            blocked_m = re.search(r"Blocked:\s+(yes|no)", out, re.IGNORECASE)
            icon_m = re.search(r"Icon:\s+(.+)$", out, re.MULTILINE)
            rssi_m = re.search(r"RSSI:\s+([-\d]+)", out, re.MULTILINE)

            name = (alias_m.group(1) if alias_m else "") or (name_m.group(1) if name_m else "") or fallback_name or mac
            paired = paired_m.group(1).lower() == "yes" if paired_m else False
            connected = connected_m.group(1).lower() == "yes" if connected_m else False
            trusted = trusted_m.group(1).lower() == "yes" if trusted_m else False
            blocked = blocked_m.group(1).lower() == "yes" if blocked_m else False
            icon_str = icon_m.group(1).strip() if icon_m else ""
            rssi_val = int(rssi_m.group(1)) if rssi_m else None

            icon, dev_type = detect_icon_and_type(icon_str, name)
            bars = format_rssi_bars(rssi_val, connected=connected)

            return BluetoothDevice(
                mac=mac,
                name=name,
                device_type=dev_type,
                icon=icon,
                paired=paired,
                connected=connected,
                trusted=trusted,
                blocked=blocked,
                rssi=rssi_val,
                bars=bars,
            )
        except Exception:
            return BluetoothDevice(mac=mac, name=fallback_name or mac)

    def list_devices(self) -> List[BluetoothDevice]:
        """Fetch all discovered, paired, or known devices."""
        if not self.is_available():
            return []

        devices: List[BluetoothDevice] = []
        macs_seen = set()

        try:
            # Query devices
            proc = subprocess.run(
                [self.bin, "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            for line in proc.stdout.splitlines():
                m = re.match(r"Device\s+([0-9A-F:]{17})\s*(.*)$", line.strip(), re.IGNORECASE)
                if m:
                    mac = m.group(1)
                    raw_name = m.group(2).strip()
                    if mac not in macs_seen:
                        macs_seen.add(mac)
                        dev = self.get_device_info(mac, fallback_name=raw_name)
                        devices.append(dev)

            # Query paired-devices to ensure none missed
            proc_p = subprocess.run(
                [self.bin, "paired-devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4,
            )
            for line in proc_p.stdout.splitlines():
                m = re.match(r"Device\s+([0-9A-F:]{17})\s*(.*)$", line.strip(), re.IGNORECASE)
                if m:
                    mac = m.group(1)
                    raw_name = m.group(2).strip()
                    if mac not in macs_seen:
                        macs_seen.add(mac)
                        dev = self.get_device_info(mac, fallback_name=raw_name)
                        devices.append(dev)

        except Exception:
            pass

        # Sort: connected first, paired second, then by name
        devices.sort(key=lambda d: (not d.connected, not d.paired, d.name.lower()))
        return devices

    def connect(self, mac: str) -> Tuple[bool, str]:
        """Connect to a Bluetooth device."""
        if not self.is_available():
            return False, "bluetoothctl is not installed."
        try:
            proc = subprocess.run([self.bin, "connect", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
            if proc.returncode == 0 or "Connection successful" in proc.stdout:
                return True, "Connected successfully."
            return False, proc.stderr.strip() or proc.stdout.strip() or "Connection failed."
        except Exception as e:
            return False, str(e)

    def disconnect(self, mac: str) -> Tuple[bool, str]:
        """Disconnect from a Bluetooth device."""
        if not self.is_available():
            return False, "bluetoothctl is not installed."
        try:
            proc = subprocess.run([self.bin, "disconnect", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            return True, proc.stdout.strip() or "Disconnected."
        except Exception as e:
            return False, str(e)

    def pair(self, mac: str) -> Tuple[bool, str]:
        """Pair with a Bluetooth device."""
        if not self.is_available():
            return False, "bluetoothctl is not installed."
        try:
            # Trust device first to facilitate automatic reconnects
            subprocess.run([self.bin, "trust", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=4)
            proc = subprocess.run([self.bin, "pair", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if proc.returncode == 0 or "Pairing successful" in proc.stdout:
                return True, "Pairing successful."
            return False, proc.stderr.strip() or proc.stdout.strip() or "Pairing failed."
        except Exception as e:
            return False, str(e)

    def remove(self, mac: str) -> Tuple[bool, str]:
        """Remove/unpair a Bluetooth device."""
        if not self.is_available():
            return False, "bluetoothctl is not installed."
        try:
            proc = subprocess.run([self.bin, "remove", mac], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            return True, proc.stdout.strip() or "Device removed."
        except Exception as e:
            return False, str(e)

    def toggle_power(self, power_on: bool) -> Tuple[bool, str]:
        """Turn Bluetooth radio ON or OFF."""
        if not self.is_available():
            return False, "bluetoothctl is not installed."
        try:
            arg = "on" if power_on else "off"
            proc = subprocess.run([self.bin, "power", arg], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
            return True, f"Bluetooth powered {arg}."
        except Exception as e:
            return False, str(e)
