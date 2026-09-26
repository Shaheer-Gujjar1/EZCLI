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
    """Fallback hardware driver detection using lspci -nnk and cpuinfo."""
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

    # 1. NVIDIA Graphics Card Detection
    nvidia_match = re.search(
        r"([0-9a-f]{2}:[0-9a-f]{2}\.[0-9a-f]).*(VGA|3D controller).*NVIDIA.*\[([0-9a-f]{4}:[0-9a-f]{4})\].*\n(?:.*\n)*?.*Kernel driver in use:\s*(\w+)",
        lspci_out,
        re.IGNORECASE,
    )
    if not nvidia_match:
        # Loose match without strict block ordering
        for block in lspci_out.split("\n\n"):
            if "NVIDIA" in block and ("VGA" in block or "3D" in block):
                dev_id = block.split()[0] if block.split() else "01:00.0"
                model_m = re.search(r"controller:\s+NVIDIA Corporation\s+(.+)$", block, re.MULTILINE)
                model = model_m.group(1).strip() if model_m else "NVIDIA Graphics Processor"
                driver_m = re.search(r"Kernel driver in use:\s*(\w+)", block)
                k_drv = driver_m.group(1) if driver_m else "nouveau"

                is_free = k_drv.lower() in ("nouveau", "none", "")
                installed_nvidia = is_package_installed("nvidia-driver-535") or is_package_installed("nvidia-driver-550")
                rec = "nvidia-driver-550"

                devices.append(
                    HardwareDeviceDriver(
                        device_id=dev_id,
                        model=model,
                        vendor="NVIDIA",
                        category="Graphics / GPU",
                        icon="🖥️",
                        current_driver=k_drv if not is_free else "nouveau (Open-Source)",
                        is_free_driver=is_free,
                        recommended_driver=rec,
                        available_drivers=["nvidia-driver-550", "nvidia-driver-535", "nvidia-driver-470"],
                        needs_driver=is_free and not installed_nvidia,
                        status_badge="Open-Source Active (Proprietary Recommended) ⚠️" if is_free else "Proprietary Active ✅",
                    )
                )
                break
    else:
        dev_id = nvidia_match.group(1)
        k_drv = nvidia_match.group(4)
        is_free = k_drv.lower() == "nouveau"
        devices.append(
            HardwareDeviceDriver(
                device_id=dev_id,
                model="NVIDIA Graphics Controller",
                vendor="NVIDIA",
                category="Graphics / GPU",
                icon="🖥️",
                current_driver=k_drv,
                is_free_driver=is_free,
                recommended_driver="nvidia-driver-550",
                available_drivers=["nvidia-driver-550", "nvidia-driver-535"],
                needs_driver=is_free,
                status_badge="Proprietary Recommended ⚠️" if is_free else "Proprietary Active ✅",
            )
        )

    # 2. Broadcom Wireless Detection
    for block in lspci_out.split("\n\n"):
        if "Broadcom" in block and ("Network" in block or "Wireless" in block):
            dev_id = block.split()[0] if block.split() else "02:00.0"
            model_m = re.search(r"controller:\s+Broadcom\s+(.+)$", block, re.MULTILINE)
            model = model_m.group(1).strip() if model_m else "Broadcom Wireless Network Adapter"
            driver_m = re.search(r"Kernel driver in use:\s*(\w+)", block)
            k_drv = driver_m.group(1) if driver_m else "b43 / bcma"

            is_wl_installed = is_package_installed("bcmwl-kernel-source")
            is_free = not is_wl_installed
            devices.append(
                HardwareDeviceDriver(
                    device_id=dev_id,
                    model=model,
                    vendor="Broadcom",
                    category="Wireless / Wi-Fi",
                    icon="📶",
                    current_driver=k_drv,
                    is_free_driver=is_free,
                    recommended_driver="bcmwl-kernel-source",
                    available_drivers=["bcmwl-kernel-source"],
                    needs_driver=not is_wl_installed,
                    status_badge="Broadcom STA Driver Recommended ⚠️" if not is_wl_installed else "Active ✅",
                )
            )
            break

    # 3. CPU Microcode Detection
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
                            status_badge="Up to date ✅" if installed else "Microcode Update Available ⚠️",
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
                            status_badge="Up to date ✅" if installed else "Microcode Update Available ⚠️",
                        )
                    )
    except Exception:
        pass

    return devices


def detect_hardware_drivers() -> List[HardwareDeviceDriver]:
    """Master hardware driver detector."""
    devices: List[HardwareDeviceDriver] = []
    if has_ubuntu_drivers():
        devices = parse_ubuntu_drivers_devices()

    if not devices:
        devices = detect_via_lspci()

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
