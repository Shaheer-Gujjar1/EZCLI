"""Unit tests for ez drivers detection and installer engine."""

import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.drivers.drivers_engine import (
    HardwareDeviceDriver,
    detect_hardware_drivers,
    detect_via_lspci,
    install_all_drivers,
    install_driver_package,
    parse_ubuntu_drivers_devices,
    simulate_all_drivers_installation,
    simulate_driver_installation,
)


class TestDrivers(unittest.TestCase):
    @patch("subprocess.run")
    def test_parse_ubuntu_drivers_devices(self, mock_run):
        output = """== /sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0 ==
modalias : pci:v000010DEd000028E0sv00001043sd00001BC2bc03sc00i00
vendor   : NVIDIA Corporation
model    : AD106M [GeForce RTX 4060 Max-Q]
driver   : nvidia-driver-535 - distro non-free
driver   : nvidia-driver-550 - distro non-free recommended
driver   : xserver-xorg-video-nouveau - distro free builtin
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=output)
        with patch("ezcli_app.drivers.drivers_engine.is_package_installed", return_value=False):
            devices = parse_ubuntu_drivers_devices()
            self.assertEqual(len(devices), 1)
            d = devices[0]
            self.assertEqual(d.vendor, "NVIDIA Corporation")
            self.assertIn("GeForce RTX 4060", d.model)
            self.assertEqual(d.recommended_driver, "nvidia-driver-550")
            self.assertTrue(d.needs_driver)
            self.assertEqual(d.category, "Graphics / GPU")

    @patch("subprocess.run")
    def test_detect_via_lspci_nvidia_and_broadcom(self, mock_run):
        lspci_output = """01:00.0 VGA compatible controller: NVIDIA Corporation GA106 [GeForce RTX 3060] [10de:2503] (rev a1)
\tSubsystem: Micro-Star International Co., Ltd. [MSI] Device 3971
\tKernel driver in use: nouveau
\tKernel modules: nvidiafb, nouveau

02:00.0 Network controller: Broadcom Inc. and subsidiaries BCM4360 802.11ac Wireless Network Adapter [14e4:43a0] (rev 03)
\tSubsystem: Apple Inc. Device 0111
\tKernel driver in use: bcma-pci-bridge
\tKernel modules: bcma, wl
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=lspci_output)
        with patch("ezcli_app.drivers.drivers_engine.is_package_installed", return_value=False):
            with patch("os.path.exists", return_value=False):
                devices = detect_via_lspci()
                self.assertTrue(len(devices) >= 2)

                gpu = next((d for d in devices if d.vendor == "NVIDIA"), None)
                self.assertIsNotNone(gpu)
                self.assertTrue(gpu.is_free_driver)
                self.assertTrue(gpu.needs_driver)
                self.assertEqual(gpu.recommended_driver, "nvidia-driver-550")

                wifi = next((d for d in devices if d.vendor == "Broadcom"), None)
                self.assertIsNotNone(wifi)
                self.assertEqual(wifi.recommended_driver, "bcmwl-kernel-source")
                self.assertTrue(wifi.needs_driver)

    @patch("subprocess.run")
    def test_simulate_driver_installation(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0 upgraded, 14 newly installed, 0 to remove and 0 not upgraded.\nNeed to get 145 MB of archives.",
            stderr="",
        )
        sim = simulate_driver_installation("nvidia-driver-550")
        self.assertTrue(sim["success"])
        self.assertEqual(sim["new_packages"], 14)
        self.assertEqual(sim["download_size"], "145 MB")
        self.assertEqual(sim["target_package"], "nvidia-driver-550")

    @patch("subprocess.run")
    def test_simulate_all_drivers_installation(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0 upgraded, 18 newly installed, 0 to remove and 0 not upgraded.\nNeed to get 180 MB of archives.",
            stderr="",
        )
        sim = simulate_all_drivers_installation(["nvidia-driver-550", "intel-microcode"])
        self.assertTrue(sim["success"])
        self.assertEqual(sim["new_packages"], 18)
        self.assertEqual(sim["download_size"], "180 MB")
        self.assertEqual(len(sim["packages"]), 2)

    @patch("ezcli_app.drivers.drivers_engine.elevated_package_install")
    def test_install_all_drivers(self, mock_install):
        mock_install.return_value = True
        success, msg = install_all_drivers(["nvidia-driver-550", "bcmwl-kernel-source"])
        self.assertTrue(success)
        mock_install.assert_called_once_with(
            ["nvidia-driver-550", "bcmwl-kernel-source"],
            reason="Install recommended proprietary hardware drivers (nvidia-driver-550, bcmwl-kernel-source)",
            task_description="Install Recommended Hardware Drivers",
            console=None,
        )


if __name__ == "__main__":
    unittest.main()

