"""Unit tests for ez speedtest engine and calculation logic."""

import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.speedtest.speedtest_engine import (
    SpeedTestResult,
    calculate_rating,
    execute_speedtest,
    has_speedtest_cli,
    run_builtin_fallback_speedtest,
    run_speedtest_cli_tool,
)


class TestSpeedtest(unittest.TestCase):
    def test_calculate_rating(self):
        self.assertIn("Ultra Fast", calculate_rating(150.0, 15.0))
        self.assertIn("Fast", calculate_rating(75.0, 25.0))
        self.assertIn("Good", calculate_rating(35.0, 35.0))
        self.assertIn("Moderate", calculate_rating(12.0, 60.0))
        self.assertIn("Basic", calculate_rating(2.0, 120.0))
        self.assertIn("Disconnected", calculate_rating(0.0, 0.0))

    @patch("shutil.which")
    def test_has_speedtest_cli(self, mock_which):
        mock_which.return_value = "/usr/bin/speedtest-cli"
        self.assertTrue(has_speedtest_cli())

        mock_which.return_value = None
        self.assertFalse(has_speedtest_cli())

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/speedtest-cli")
    def test_run_speedtest_cli_tool_json(self, mock_which, mock_run):
        json_out = """{
            "download": 142500000.0,
            "upload": 48200000.0,
            "ping": 14.2,
            "server": {"name": "Frankfurt", "country": "Germany", "sponsor": "Vodafone"},
            "client": {"isp": "Deutsche Telekom"}
        }"""
        mock_run.return_value = MagicMock(returncode=0, stdout=json_out, stderr="")
        res = run_speedtest_cli_tool()

        self.assertEqual(res.ping_ms, 14.2)
        self.assertEqual(res.download_mbps, 142.5)
        self.assertEqual(res.upload_mbps, 48.2)
        self.assertEqual(res.server_name, "Vodafone")
        self.assertEqual(res.server_country, "Germany")
        self.assertEqual(res.isp, "Deutsche Telekom")
        self.assertIn("Ultra Fast", res.rating)

    @patch("urllib.request.urlopen")
    @patch("socket.socket")
    def test_run_builtin_fallback_speedtest(self, mock_socket, mock_urlopen):
        mock_socket_inst = MagicMock()
        mock_socket.return_value = mock_socket_inst

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"X" * 1_000_000
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = run_builtin_fallback_speedtest()
        self.assertGreater(res.ping_ms, 0)
        self.assertGreater(res.download_mbps, 0)
        self.assertGreater(res.upload_mbps, 0)
        self.assertIn("Cloudflare", res.server_name)
        self.assertTrue(len(res.rating) > 0)

    def test_speedtest_app_instantiation(self):
        from ezcli_app.speedtest.speedtest_tui import SpeedtestApp
        app = SpeedtestApp()
        self.assertFalse(app.test_in_progress)
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
