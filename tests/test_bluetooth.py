"""Unit tests for ez bluetooth engine and manager."""

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.bluetooth.bluetooth_engine import (
    BluetoothController,
    BluetoothDevice,
    BluetoothManager,
    detect_icon_and_type,
    format_rssi_bars,
)


class TestBluetooth(unittest.TestCase):
    def test_format_rssi_bars(self):
        self.assertEqual(format_rssi_bars(-50), "▂▄▆█")
        self.assertEqual(format_rssi_bars(-70), "▂▄▆_")
        self.assertEqual(format_rssi_bars(-80), "▂▄__")
        self.assertEqual(format_rssi_bars(-95), "▂___")
        self.assertEqual(format_rssi_bars(None, connected=True), "▂▄▆█")
        self.assertEqual(format_rssi_bars(None, connected=False), "▂▄__")

    def test_detect_icon_and_type(self):
        icon, dtype = detect_icon_and_type("audio-headset", "AirPods Pro")
        self.assertEqual(icon, "🎧")
        self.assertIn("Audio", dtype)

        icon, dtype = detect_icon_and_type("input-mouse", "Logitech MX Master")
        self.assertEqual(icon, "🖱️")
        self.assertIn("Mouse", dtype)

        icon, dtype = detect_icon_and_type("input-keyboard", "Keychron K2")
        self.assertEqual(icon, "⌨️")
        self.assertIn("Keyboard", dtype)

        icon, dtype = detect_icon_and_type("phone", "Pixel 8")
        self.assertEqual(icon, "📱")
        self.assertIn("Phone", dtype)

    @patch("subprocess.run")
    def test_get_controller_online(self, mock_run):
        mock_output = """Controller 00:11:22:33:44:55 (public)
Name: BlueZ Controller
Alias: BlueZ Controller
Class: 0x006c010c
Powered: yes
Discoverable: no
Pairable: yes
Discovering: yes
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        manager = BluetoothManager()
        manager.bin = "/usr/bin/bluetoothctl"

        ctrl = manager.get_controller()
        self.assertTrue(ctrl.available)
        self.assertEqual(ctrl.mac, "00:11:22:33:44:55")
        self.assertEqual(ctrl.name, "BlueZ Controller")
        self.assertTrue(ctrl.powered)
        self.assertTrue(ctrl.discovering)
        self.assertTrue(ctrl.pairable)

    @patch("subprocess.run")
    def test_get_controller_offline(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="No default controller available\n")
        manager = BluetoothManager()
        manager.bin = "/usr/bin/bluetoothctl"

        ctrl = manager.get_controller()
        self.assertFalse(ctrl.available)

    @patch("subprocess.run")
    def test_list_devices(self, mock_run):
        devices_out = "Device 11:22:33:44:55:66 Sony WH-1000XM4\nDevice AA:BB:CC:DD:EE:FF MX Anywhere\n"
        paired_out = "Device 11:22:33:44:55:66 Sony WH-1000XM4\n"
        info_out_sony = """Device 11:22:33:44:55:66 (public)
Name: Sony WH-1000XM4
Icon: audio-card
Paired: yes
Connected: yes
Trusted: yes
RSSI: -58
"""
        info_out_mouse = """Device AA:BB:CC:DD:EE:FF (public)
Name: MX Anywhere
Icon: input-mouse
Paired: no
Connected: no
Trusted: no
RSSI: -82
"""
        def run_side_effect(cmd, *args, **kwargs):
            if cmd[1] == "devices":
                return MagicMock(returncode=0, stdout=devices_out)
            elif cmd[1] == "paired-devices":
                return MagicMock(returncode=0, stdout=paired_out)
            elif cmd[1] == "info" and cmd[2] == "11:22:33:44:55:66":
                return MagicMock(returncode=0, stdout=info_out_sony)
            elif cmd[1] == "info" and cmd[2] == "AA:BB:CC:DD:EE:FF":
                return MagicMock(returncode=0, stdout=info_out_mouse)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = run_side_effect
        manager = BluetoothManager()
        manager.bin = "/usr/bin/bluetoothctl"

        devices = manager.list_devices()
        self.assertEqual(len(devices), 2)
        # Sony connected should be sorted first
        self.assertEqual(devices[0].mac, "11:22:33:44:55:66")
        self.assertTrue(devices[0].connected)
        self.assertTrue(devices[0].paired)
        self.assertEqual(devices[0].bars, "▂▄▆█")

        self.assertEqual(devices[1].mac, "AA:BB:CC:DD:EE:FF")
        self.assertFalse(devices[1].connected)

    @patch("subprocess.run")
    def test_connect_disconnect_remove(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Connection successful\n", stderr="")
        manager = BluetoothManager()
        manager.bin = "/usr/bin/bluetoothctl"

        ok, msg = manager.connect("11:22:33:44:55:66")
        self.assertTrue(ok)

        mock_run.return_value = MagicMock(returncode=0, stdout="Successful disconnected\n", stderr="")
        ok, msg = manager.disconnect("11:22:33:44:55:66")
        self.assertTrue(ok)

        mock_run.return_value = MagicMock(returncode=0, stdout="Device has been removed\n", stderr="")
        ok, msg = manager.remove("11:22:33:44:55:66")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
