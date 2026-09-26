"""Backend engine for proprietary hardware driver detection and installation."""

from dataclasses import dataclass, field
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ..elevation import elevated_package_install, elevated_run_command


@dataclass
class HardwareDeviceDriver:
    """Represents a hardware component and its driver recommendations."""
    device_id: str
    model: str
    vendor: str
    category: str
    icon: str
    current_driver: str
    is_free_driver: bool
    recommended_driver: str
    available_drivers: List[str] = field(default_factory=list)
    needs_driver: bool = False
    status_badge: str = ""


def has_ubuntu_drivers() -> bool:
    """Check if ubuntu-drivers CLI is available."""
    return shutil.which("ubuntu-drivers") is not None


def is_package_installed(pkg_name: str) -> bool:
    """Check if a package is installed via dpkg-query."""
    try:
        proc = subprocess.run(
            ["dpkg-query", "-W", "-f=${Status}", pkg_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        return "install ok installed" in proc.stdout
    except Exception:
        return False


def parse_ubuntu_drivers_devices() -> List[HardwareDeviceDriver]:
    """Parse `ubuntu-drivers devices` output."""
    devices: List[HardwareDeviceDriver] = []
    try:
        proc = subprocess.run(
            ["ubuntu-drivers", "devices"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []

        current_dev: Dict[str, Any] = {}
        for line in proc.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("== /sys/"):
                if current_dev and current_dev.get("model"):
                    devices.append(_create_device_from_dict(current_dev))
                current_dev = {
                    "sys_path": line_str.strip("= "),
                    "drivers": [],
                    "recommended": "",
                }
            elif ":" in line_str and current_dev:
                key, val = line_str.split(":", 1)
                key = key.strip()
                val = val.strip()
                if key == "vendor":
                    current_dev["vendor"] = val
                elif key == "model":
                    current_dev["model"] = val
                elif key == "driver":
                    driver_name = val.split()[0]
                    current_dev["drivers"].append(driver_name)
                    if "recommended" in val:
                        current_dev["recommended"] = driver_name

        if current_dev and current_dev.get("model"):
            devices.append(_create_device_from_dict(current_dev))

    except Exception:
        pass

    return devices


def _create_device_from_dict(data: Dict[str, Any]) -> HardwareDeviceDriver:
    vendor = data.get("vendor", "Unknown")
    model = data.get("model", "Hardware Component")
    drivers = data.get("drivers", [])
    rec = data.get("recommended", "") or (drivers[0] if drivers else "")

    category = "Graphics / GPU" if "nvidia" in rec or "geforce" in model.lower() else "Hardware Component"
    icon = "🖥️" if "Graphics" in category else "⚙️"

    # Check which driver is currently active
    current_driver = "Open-Source (Built-in)"
    is_free = True
    needs_driver = bool(rec)

    for d in drivers:
        if is_package_installed(d):
            current_driver = d
            is_free = False
            needs_driver = False
            break

    status_badge = "Proprietary Active ✅" if not is_free else ("Driver Recommended ⚠️" if needs_driver else "Open Source Active")

    return HardwareDeviceDriver(
        device_id=data.get("sys_path", "pci:00"),
        model=model,
        vendor=vendor,
        category=category,
        icon=icon,
        current_driver=current_driver,
        is_free_driver=is_free,
        recommended_driver=rec,
        available_drivers=drivers,
        needs_driver=needs_driver,
        status_badge=status_badge,
    )


def detect_via_lspci() -> List[HardwareDeviceDriver]:
    """Comprehensive hardware driver detection using lspci -nnk and cpuinfo (Driver Booster engine)."""
    devices: List[HardwareDeviceDriver] = []
    try:
        proc = subprocess.run(
            ["lspci", "-nnk"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        lspci_out = proc.stdout
    except Exception:
        lspci_out = ""

    blocks: List[str] = []
    current_block: List[str] = []
    for line in lspci_out.splitlines():
        if re.match(r"^[0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]", line):
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
        if line.strip() or current_block:
            current_block.append(line)
    if current_block:
        blocks.append("\n".join(current_block))

    # If strict regex block parsing didn't find blocks, fallback to double newline
    if not blocks and lspci_out.strip():
        blocks = [b.strip() for b in lspci_out.split("\n\n") if b.strip()]

    for block in blocks:
        first_line = block.splitlines()[0]
        dev_id_m = re.match(r"^([0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f])\s+(.+)$", first_line)
        if not dev_id_m:
            continue
        dev_id, desc = dev_id_m.group(1), dev_id_m.group(2)
        driver_m = re.search(r"Kernel driver in use:\s*([^\s\n]+)", block)
        k_drv = driver_m.group(1) if driver_m else ""

        # Determine hardware category & icon
        if any(k in desc for k in ["VGA compatible controller", "3D controller", "Display controller"]):
            category = "Display Adapters"
            icon = "🖥️"
        elif any(k in desc for k in ["Network controller", "Wireless"]):
            category = "Network & Wi-Fi"
            icon = "📶"
        elif "Ethernet controller" in desc:
            category = "Ethernet Adapters"
            icon = "🌐"
        elif "Audio device" in desc or "Audio controller" in desc:
            category = "Sound & Audio"
            icon = "🔊"
        elif any(k in desc for k in ["Non-Volatile memory", "SATA", "RAID", "Mass storage"]):
            category = "Storage Controllers"
            icon = "💾"
        elif "Card Reader" in desc or "Unassigned class" in desc:
            category = "Card Readers & Peripherals"
            icon = "🔌"
        elif not k_drv and not any(k in desc.lower() for k in ["bridge", "smbus", "controller [0580]"]):
            category = "System Hardware"
            icon = "⚙️"
        else:
            continue

        model = desc
        if ":" in desc:
            model = desc.split(":", 1)[1].strip()
        model = re.sub(r"\s*\(rev\s+[0-9a-f]+\)", "", model).strip()

        # Vendor extraction
        vendor = "Unknown"
        for v in ["NVIDIA", "Intel", "Broadcom", "Realtek", "AMD", "Qualcomm", "SK hynix"]:
            if v.lower() in desc.lower() or v.lower() in block.lower():
                vendor = v
                break

        if "NVIDIA" in block or vendor == "NVIDIA":
            is_free = k_drv.lower() in ("nouveau", "none", "")
            installed_nvidia = is_package_installed("nvidia-driver-535") or is_package_installed("nvidia-driver-550")
            rec = "nvidia-driver-550"
            needs_driver = is_free and not installed_nvidia
            status_badge = "UPDATE AVAILABLE ⚠️" if needs_driver else "OPTIMAL & ACTIVE ✅"
            devices.append(
                HardwareDeviceDriver(
                    device_id=dev_id,
                    model=model,
                    vendor="NVIDIA",
                    category="Display Adapters",
                    icon="🖥️",
                    current_driver=k_drv or "nouveau (Generic)",
                    is_free_driver=is_free,
                    recommended_driver=rec,
                    available_drivers=["nvidia-driver-550", "nvidia-driver-535", "nvidia-driver-470"],
                    needs_driver=needs_driver,
                    status_badge=status_badge,
                )
            )
        elif vendor == "Broadcom" and ("Network" in desc or "Wireless" in desc):
            is_wl_installed = is_package_installed("bcmwl-kernel-source")
            rec = "bcmwl-kernel-source"
            needs_driver = not is_wl_installed
            status_badge = "UPDATE AVAILABLE ⚠️" if needs_driver else "OPTIMAL & ACTIVE ✅"
            devices.append(
                HardwareDeviceDriver(
                    device_id=dev_id,
                    model=model,
                    vendor="Broadcom",
                    category="Network & Wi-Fi",
                    icon="📶",
                    current_driver=k_drv or "b43 / bcma",
                    is_free_driver=not is_wl_installed,
                    recommended_driver=rec,
                    available_drivers=["bcmwl-kernel-source"],
                    needs_driver=needs_driver,
                    status_badge=status_badge,
                )
            )
        else:
            needs_driver = not bool(k_drv)
            status_badge = "MISSING 🚫" if needs_driver else "OPTIMAL & ACTIVE ✅"
            rec = "linux-firmware" if needs_driver else f"{k_drv} (Active)"
            devices.append(
                HardwareDeviceDriver(
                    device_id=dev_id,
                    model=model,
                    vendor=vendor,
                    category=category,
                    icon=icon,
                    current_driver=k_drv or "None (Missing Driver)",
                    is_free_driver=True,
                    recommended_driver=rec,
                    available_drivers=[rec],
                    needs_driver=needs_driver,
                    status_badge=status_badge,
                )
            )

    # CPU Microcode Firmware Detection
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                c_info = f.read()
                if "GenuineIntel" in c_info:
                    installed = is_package_installed("intel-microcode")
                    devices.append(
                        HardwareDeviceDriver(
                            device_id="cpu:intel",
                            model="Intel Processor Microcode Firmware",
                            vendor="Intel",
                            category="Processor Microcode",
                            icon="⚙️",
                            current_driver="intel-microcode" if installed else "Generic Kernel Microcode",
                            is_free_driver=not installed,
                            recommended_driver="intel-microcode",
                            available_drivers=["intel-microcode"],
                            needs_driver=not installed,
                            status_badge="OPTIMAL & ACTIVE ✅" if installed else "UPDATE AVAILABLE ⚠️",
                        )
                    )
                elif "AuthenticAMD" in c_info:
                    installed = is_package_installed("amd64-microcode")
                    devices.append(
                        HardwareDeviceDriver(
                            device_id="cpu:amd",
                            model="AMD Processor Microcode Firmware",
                            vendor="AMD",
                            category="Processor Microcode",
                            icon="⚙️",
                            current_driver="amd64-microcode" if installed else "Generic Kernel Microcode",
                            is_free_driver=not installed,
                            recommended_driver="amd64-microcode",
                            available_drivers=["amd64-microcode"],
                            needs_driver=not installed,
                            status_badge="OPTIMAL & ACTIVE ✅" if installed else "UPDATE AVAILABLE ⚠️",
                        )
                    )
    except Exception:
        pass

    return devices


def detect_hardware_drivers() -> List[HardwareDeviceDriver]:
    """Master hardware driver detector combining proprietary and system scan."""
    devices: List[HardwareDeviceDriver] = []
    if has_ubuntu_drivers():
        devices = parse_ubuntu_drivers_devices()

    lspci_devs = detect_via_lspci()
    if not devices:
        devices = lspci_devs
    else:
        existing_models = {d.model.lower() for d in devices}
        existing_ids = {d.device_id for d in devices}
        for d in lspci_devs:
            if d.device_id not in existing_ids and not any(m in d.model.lower() for m in existing_models):
                devices.append(d)

    return devices


def simulate_driver_installation(driver_package: str) -> Dict[str, Any]:
    """Simulate apt installation for a driver package."""
    try:
        proc = subprocess.run(
            ["apt-get", "install", "-s", "-y", driver_package],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        out = proc.stdout
        packages_m = re.search(r"(\d+)\s+upgraded,\s+(\d+)\s+newly installed", out)
        disk_m = re.search(r"Need to get\s+([\d\.]+\s+[kKmMgG]?B)", out)

        new_pkgs = int(packages_m.group(2)) if packages_m else 1
        download_size = disk_m.group(1) if disk_m else "Approx. 50-400 MB"

        return {
            "success": proc.returncode == 0,
            "new_packages": new_pkgs,
            "download_size": download_size,
            "target_package": driver_package,
            "raw_output": out,
        }
    except Exception as e:
        return {
            "success": False,
            "new_packages": 1,
            "download_size": "Standard driver package",
            "target_package": driver_package,
            "error": str(e),
        }


def simulate_all_drivers_installation(driver_packages: List[str]) -> Dict[str, Any]:
    """Simulate apt installation for multiple driver packages in a single batch."""
    if not driver_packages:
        return {"success": True, "new_packages": 0, "download_size": "0 B", "packages": []}

    unique_pkgs = list(dict.fromkeys(driver_packages))
    try:
        proc = subprocess.run(
            ["apt-get", "install", "-s", "-y"] + unique_pkgs,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=12,
        )
        out = proc.stdout
        packages_m = re.search(r"(\d+)\s+upgraded,\s+(\d+)\s+newly installed", out)
        disk_m = re.search(r"Need to get\s+([\d\.]+\s+[kKmMgG]?B)", out)

        new_pkgs = int(packages_m.group(2)) if packages_m else len(unique_pkgs)
        download_size = disk_m.group(1) if disk_m else "Approx. 50-300 MB"

        return {
            "success": proc.returncode == 0,
            "new_packages": new_pkgs,
            "download_size": download_size,
            "packages": unique_pkgs,
            "raw_output": out,
        }
    except Exception as e:
        return {
            "success": False,
            "new_packages": len(unique_pkgs),
            "download_size": "Approx. 50-300 MB",
            "packages": unique_pkgs,
            "error": str(e),
        }


def install_all_drivers(driver_packages: List[str], console: Optional[Any] = None) -> Tuple[bool, str]:
    """Install multiple recommended driver packages in a single 1-click batch operation."""
    if not driver_packages:
        return True, "All system hardware is already using optimal drivers."

    unique_pkgs = list(dict.fromkeys(driver_packages))
    success = elevated_package_install(
        unique_pkgs,
        reason=f"Install recommended proprietary hardware drivers ({', '.join(unique_pkgs)})",
        task_description="Install Recommended Hardware Drivers",
        console=console,
    )
    if success:
        return True, f"Successfully installed {len(unique_pkgs)} driver package(s). Please reboot your system to activate."
    return False, "Failed to complete driver installation."


def install_driver_package(driver_package: str, console: Optional[Any] = None) -> Tuple[bool, str]:
    """Install driver package with elevated administrative permissions."""
    success = elevated_package_install(
        [driver_package],
        reason=f"Install recommended proprietary hardware driver '{driver_package}'",
        task_description="Install Hardware Driver",
        console=console,
    )
    if success:
        return True, f"Hardware driver '{driver_package}' installed successfully. A system reboot is recommended."
    return False, f"Failed to install driver '{driver_package}'."
