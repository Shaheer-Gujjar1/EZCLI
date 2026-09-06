"""Unit tests for the EasyCLI Wi-Fi Manager (ez connect-wifi)."""

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.wifi.wifi_app import WifiApp, WifiPasswordModal
from ezcli_app.wifi.wifi_engine import (
    WifiManager,
    WifiNetwork,
    format_freq_band,
    format_security,
    format_signal_bars,
    parse_terse_line,
)
from textual.widgets import DataTable, Input


class TestWifiEngine(unittest.TestCase):
    """Test suite for Wi-Fi management backend."""

    def test_parse_terse_line(self):
        line = "*:404-Network-Unavailable:E0\\:61\\:4A\\:E0\\:8A\\:C5:Infra:157:5785 MHz:270 Mbit/s:72:▂▄▆_:WPA1 WPA2"
        fields = parse_terse_line(line)
        self.assertEqual(len(fields), 10)
        self.assertEqual(fields[0], "*")
        self.assertEqual(fields[1], "404-Network-Unavailable")
        self.assertEqual(fields[2], "E0:61:4A:E0:8A:C5")
        self.assertEqual(fields[5], "5785 MHz")
        self.assertEqual(fields[7], "72")
        self.assertEqual(fields[9], "WPA1 WPA2")

    def test_format_security(self):
        is_sec, disp = format_security("")
        self.assertFalse(is_sec)
        self.assertIn("Open", disp)

        is_sec, disp = format_security("--")
        self.assertFalse(is_sec)
        self.assertIn("Open", disp)

        is_sec, disp = format_security("WPA2")
        self.assertTrue(is_sec)
        self.assertIn("WPA2 Personal", disp)

        is_sec, disp = format_security("WPA1 WPA2")
        self.assertTrue(is_sec)
        self.assertIn("WPA2", disp)

        is_sec, disp = format_security("WPA3")
        self.assertTrue(is_sec)
        self.assertIn("WPA3 Personal", disp)

        is_sec, disp = format_security("WPA2 WPA3")
        self.assertTrue(is_sec)
        self.assertIn("WPA2/WPA3", disp)

        is_sec, disp = format_security("WEP")
        self.assertTrue(is_sec)
        self.assertIn("WEP", disp)

    def test_format_signal_bars(self):
        b100 = format_signal_bars(100)
        self.assertIn("▂▄▆█", b100)
        self.assertIn("100%", b100)
        self.assertIn("📶", b100)

        b65 = format_signal_bars(65)
        self.assertIn("▂▄▆_", b65)
        self.assertIn("65%", b65)

        b30 = format_signal_bars(30)
        self.assertIn("▂▄__", b30)
        self.assertIn("30%", b30)

        b10 = format_signal_bars(10)
        self.assertIn("▂___", b10)
        self.assertIn("10%", b10)

    def test_format_freq_band(self):
        self.assertEqual(format_freq_band("5785 MHz", "157"), "5 GHz (Ch 157)")
        self.assertEqual(format_freq_band("2412 MHz", "1"), "2.4 GHz (Ch 1)")
        self.assertEqual(format_freq_band("unknown", "6"), "Ch 6")

    @patch("shutil.which", return_value=None)
    def test_is_wifi_available_no_nmcli(self, mock_which):
        wm = WifiManager()
        ok, msg = wm.is_wifi_available()
        self.assertFalse(ok)
        self.assertIn("NetworkManager CLI", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_is_wifi_available_success(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="wlp1s0:wifi:connected\nlo:loopback:unmanaged\n",
        )
        wm = WifiManager()
        ok, msg = wm.is_wifi_available()
        self.assertTrue(ok)
        self.assertIn("available", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_is_wifi_available_no_device(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="enp0s31f6:ethernet:connected\nlo:loopback:unmanaged\n",
        )
        wm = WifiManager()
        ok, msg = wm.is_wifi_available()
        self.assertFalse(ok)
        self.assertIn("No Wi-Fi interface", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_get_active_wifi(self, mock_run, mock_which):
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="wlp1s0:wifi:connected:MyOfficeWifi\nenp0s31f6:ethernet:unavailable:\n",
            ),
            MagicMock(
                returncode=0,
                stdout="192.168.1.50/24\n",
            ),
        ]
        wm = WifiManager()
        active = wm.get_active_wifi()
        self.assertIsNotNone(active)
        self.assertEqual(active["ssid"], "MyOfficeWifi")
        self.assertEqual(active["interface"], "wlp1s0")
        self.assertEqual(active["ip"], "192.168.1.50")

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_scan_networks(self, mock_run, mock_which):
        sample_output = (
            " :Guest_Free:11\\:22\\:33\\:44\\:55\\:66:Infra:6:2437 MHz:54 Mbit/s:40:▂▄__:--\n"
            "*:HomeNet:AA\\:BB\\:CC\\:DD\\:EE\\:FF:Infra:157:5785 MHz:270 Mbit/s:85:▂▄▆█:WPA2\n"
            " :HomeNet:AA\\:BB\\:CC\\:DD\\:EE\\:00:Infra:1:2412 MHz:130 Mbit/s:50:▂▄__:WPA2\n"
            " :Work_Secure:00\\:11\\:22\\:33\\:44\\:55:Infra:149:5745 MHz:270 Mbit/s:90:▂▄▆█:WPA2 WPA3\n"
        )
        # First call is rescan (ignored), second call is list
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout=sample_output),
        ]
        wm = WifiManager()
        nets = wm.scan_networks(rescan=True)

        self.assertEqual(len(nets), 3)  # HomeNet deduplicated to best signal
        # Active HomeNet should be first
        self.assertEqual(nets[0].ssid, "HomeNet")
        self.assertTrue(nets[0].in_use)
        self.assertEqual(nets[0].signal, 85)

        # Work_Secure has higher signal than Guest_Free
        self.assertEqual(nets[1].ssid, "Work_Secure")
        self.assertEqual(nets[1].signal, 90)
        self.assertTrue(nets[1].is_secured)

        # Guest_Free is open
        self.assertEqual(nets[2].ssid, "Guest_Free")
        self.assertFalse(nets[2].is_secured)
        self.assertIn("Open", nets[2].security_display)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_connect_network_success(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="Connection successfully activated\n", stderr="")
        wm = WifiManager()
        ok, msg = wm.connect_network("HomeNet", "secret123")
        self.assertTrue(ok)
        self.assertIn("Successfully connected", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_connect_network_bad_password(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: Connection activation failed: (7) Secrets were required, but not provided.",
        )
        wm = WifiManager()
        ok, msg = wm.connect_network("HomeNet", "wrongpassword")
        self.assertFalse(ok)
        self.assertIn("Incorrect Wi-Fi password", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["nmcli"], timeout=10))
    def test_connect_network_timeout(self, mock_run, mock_which):
        wm = WifiManager()
        ok, msg = wm.connect_network("HomeNet", "pass", timeout=10.0)
        self.assertFalse(ok)
        self.assertIn("timed out", msg)

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_disconnect_wifi(self, mock_run, mock_which):
        mock_run.side_effect = [
            # get_active_wifi dev list
            MagicMock(returncode=0, stdout="wlp1s0:wifi:connected:HomeNet\n"),
            # dev show
            MagicMock(returncode=0, stdout="192.168.1.10/24\n"),
            # disconnect
            MagicMock(returncode=0, stdout="Device 'wlp1s0' successfully disconnected.\n"),
        ]
        wm = WifiManager()
        ok, msg = wm.disconnect_wifi()
        self.assertTrue(ok)
        self.assertIn("disconnected", msg.lower())


class TestWifiTuiApp(unittest.IsolatedAsyncioTestCase):
    """Test suite for Textual Wi-Fi Manager TUI App."""

    def test_password_modal_show_hide_toggle(self):
        net = WifiNetwork(
            ssid="SecureWifi",
            bssid="00:11:22:33:44:55",
            signal=80,
            bars="▂▄▆█ 80% 📶",
            security="WPA2",
            security_display="🔒 WPA2 Personal",
            is_secured=True,
            in_use=False,
            freq="5 GHz (Ch 36)",
            channel="36",
            rate="270 Mbit/s",
        )
        modal = WifiPasswordModal(network=net)
        self.assertEqual(modal.network.ssid, "SecureWifi")

        mock_input = MagicMock()
        mock_input.password = True
        mock_btn = MagicMock()
        mock_btn.id = "btn-toggle-pwd"
        with patch.object(modal, "query_one", return_value=mock_input):
            modal.on_button_pressed(MagicMock(button=mock_btn))
            self.assertFalse(mock_input.password)
            self.assertEqual(mock_btn.label, "🙈 Hide Password")

            modal.on_button_pressed(MagicMock(button=mock_btn))
            self.assertTrue(mock_input.password)
            self.assertEqual(mock_btn.label, "👁️ Show Password")

    def test_wifi_app_initialization(self):
        mock_manager = MagicMock()
        mock_manager.get_active_wifi.return_value = {
            "ssid": "TestWifi",
            "interface": "wlan0",
            "ip": "192.168.1.15",
            "signal": 90,
        }
        mock_manager.scan_networks.return_value = [
            WifiNetwork(
                ssid="TestWifi",
                bssid="AA:BB:CC:DD:EE:FF",
                signal=90,
                bars="▂▄▆█ 90% 📶",
                security="WPA2",
                security_display="🔒 WPA2 Personal",
                is_secured=True,
                in_use=True,
                freq="5 GHz (Ch 40)",
                channel="40",
                rate="300 Mbit/s",
            )
        ]

        app = WifiApp(manager=mock_manager)
        self.assertEqual(app.TITLE, "EasyCLI Wi-Fi Manager")
        self.assertIsNotNone(app.BINDINGS)

    async def test_wifi_app_pilot_run(self):
        mock_manager = MagicMock()
        mock_manager.get_active_wifi.return_value = {
            "ssid": "TestWifi",
            "interface": "wlan0",
            "ip": "192.168.1.15",
            "signal": 90,
        }
        mock_manager.scan_networks.return_value = [
            WifiNetwork(
                ssid="TestWifi",
                bssid="AA:BB:CC:DD:EE:FF",
                signal=90,
                bars="▂▄▆█ 90% 📶",
                security="WPA2",
                security_display="🔒 WPA2 Personal",
                is_secured=True,
                in_use=True,
                freq="5 GHz (Ch 40)",
                channel="40",
                rate="300 Mbit/s",
            ),
            WifiNetwork(
                ssid="CoffeeShop",
                bssid="11:22:33:44:55:66",
                signal=65,
                bars="▂▄▆_ 65% 📶",
                security="Open",
                security_display="🔓 Open (No Password)",
                is_secured=False,
                in_use=False,
                freq="2.4 GHz (Ch 6)",
                channel="6",
                rate="54 Mbit/s",
            ),
        ]

        app = WifiApp(manager=mock_manager)
        async with app.run_test() as pilot:
            self.assertTrue(app.is_running)
            table = app.query_one("#wifi-table", DataTable)
            self.assertTrue(app.is_mounted(table))
            self.assertEqual(table.row_count, 2)
            # Test search filtering
            search = app.query_one("#search-box", Input)
            search.value = "Coffee"
            await pilot.pause()
            self.assertEqual(table.row_count, 1)
            search.value = ""
            await pilot.pause()
            self.assertEqual(table.row_count, 2)
            # Press quit key
            await pilot.press("q")


if __name__ == "__main__":
    unittest.main()
