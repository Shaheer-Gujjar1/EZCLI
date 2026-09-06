"""Unit tests for the Universal Internet Connectivity Checker (ez check-internet)."""

import json
import socket
import subprocess
import unittest
from unittest.mock import MagicMock, mock_open, patch

from rich.console import Console

from ezcli_app.internet_checker import (
    check_dns,
    check_internet_reachability,
    check_router,
    diagnose_internet,
    format_stage_pipeline_token,
    get_default_gateway,
    get_diagnostic_reason,
    get_dns_resolvers,
    ping_host,
    render_internet_check,
)


class TestInternetChecker(unittest.TestCase):
    """Test suite for internet connectivity diagnostics."""

    @patch("subprocess.run")
    def test_get_default_gateway_ip_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {"dst": "default", "gateway": "192.168.1.1", "dev": "wlp1s0"}
            ]),
        )
        gw, dev = get_default_gateway()
        self.assertEqual(gw, "192.168.1.1")
        self.assertEqual(dev, "wlp1s0")

    @patch("subprocess.run")
    def test_get_default_gateway_ip_text(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # ip -j fails
            MagicMock(
                returncode=0,
                stdout="default via 10.0.0.1 dev eth0 proto dhcp metric 100\n",
            ),
        ]
        gw, dev = get_default_gateway()
        self.assertEqual(gw, "10.0.0.1")
        self.assertEqual(dev, "eth0")

    @patch("subprocess.run")
    def test_get_default_gateway_proc_route(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
        ]
        # /proc/net/route with little-endian hex 0101A8C0 = 192.168.1.1
        proc_data = "Iface\tDestination\tGateway\tFlags\neth0\t00000000\t0101A8C0\t0003\n"
        with patch("builtins.open", mock_open(read_data=proc_data)):
            gw, dev = get_default_gateway()
            self.assertEqual(gw, "192.168.1.1")
            self.assertEqual(dev, "eth0")

    @patch("subprocess.run")
    def test_get_default_gateway_none(self, mock_run):
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),
            MagicMock(returncode=1, stdout=""),
        ]
        with patch("builtins.open", side_effect=FileNotFoundError):
            gw, dev = get_default_gateway()
            self.assertIsNone(gw)
            self.assertIsNone(dev)

    @patch("subprocess.run")
    def test_ping_host_success_time(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="64 bytes from 1.1.1.1: icmp_seq=1 ttl=59 time=18.4 ms\n",
            stderr="",
        )
        ok, latency, msg = ping_host("1.1.1.1")
        self.assertTrue(ok)
        self.assertEqual(latency, 18.4)
        self.assertIn("18.4 ms", msg)

    @patch("subprocess.run")
    def test_ping_host_success_rtt(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1 packets transmitted, 1 received\nrtt min/avg/max/mdev = 12.1/14.5/16.8/1.2 ms\n",
            stderr="",
        )
        ok, latency, msg = ping_host("8.8.8.8")
        self.assertTrue(ok)
        self.assertEqual(latency, 14.5)
        self.assertIn("14.5 ms", msg)

    @patch("subprocess.run")
    def test_ping_host_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="1 packets transmitted, 0 received, 100% packet loss\n",
            stderr="",
        )
        ok, latency, msg = ping_host("192.168.1.254")
        self.assertFalse(ok)
        self.assertIsNone(latency)
        self.assertIn("timed out", msg)

    @patch("ezcli_app.internet_checker.get_default_gateway")
    @patch("ezcli_app.internet_checker.ping_host")
    def test_check_router_success(self, mock_ping, mock_gw):
        mock_gw.return_value = ("192.168.1.1", "wlan0")
        mock_ping.return_value = (True, 2.5, "Responded in 2.5 ms")

        res = check_router()
        self.assertTrue(res["success"])
        self.assertEqual(res["target"], "192.168.1.1")
        self.assertEqual(res["latency_ms"], 2.5)
        self.assertIn("✔", res["status_str"])

    @patch("ezcli_app.internet_checker.get_default_gateway")
    def test_check_router_no_gateway(self, mock_gw):
        mock_gw.return_value = (None, None)

        res = check_router()
        self.assertFalse(res["success"])
        self.assertEqual(res["target"], "None")
        self.assertIn("No Gateway", res["status_str"])

    @patch("ezcli_app.internet_checker.get_dns_resolvers")
    @patch("socket.getaddrinfo")
    def test_check_dns_success(self, mock_gai, mock_res):
        mock_res.return_value = ["1.1.1.1"]
        mock_gai.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("142.250.190.46", 80))
        ]

        res = check_dns(domains=["google.com"])
        self.assertTrue(res["success"])
        self.assertEqual(res["resolved_ip"], "142.250.190.46")
        self.assertIsNotNone(res["latency_ms"])
        self.assertIn("✔", res["status_str"])

    @patch("ezcli_app.internet_checker.get_dns_resolvers")
    @patch("socket.getaddrinfo", side_effect=socket.gaierror(-2, "Name or service not known"))
    def test_check_dns_failure(self, mock_gai, mock_res):
        mock_res.return_value = ["192.168.1.1"]

        res = check_dns(domains=["google.com"])
        self.assertFalse(res["success"])
        self.assertIsNone(res["resolved_ip"])
        self.assertIn("Resolution Failed", res["status_str"])

    @patch("ezcli_app.internet_checker.ping_host")
    def test_check_internet_reachability_icmp(self, mock_ping):
        mock_ping.return_value = (True, 21.0, "Responded in 21.0 ms")

        res = check_internet_reachability(hosts=["1.1.1.1"])
        self.assertTrue(res["success"])
        self.assertEqual(res["method"], "ICMP Ping")
        self.assertEqual(res["latency_ms"], 21.0)
        self.assertIn("✔", res["status_str"])

    @patch("ezcli_app.internet_checker.ping_host", return_value=(False, None, "timed out"))
    @patch("socket.socket")
    def test_check_internet_reachability_tcp_fallback(self, mock_sock_cls, mock_ping):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0
        mock_sock_cls.return_value = mock_sock

        res = check_internet_reachability(hosts=["1.1.1.1"])
        self.assertTrue(res["success"])
        self.assertEqual(res["method"], "TCP (Port 53)")
        self.assertIsNotNone(res["latency_ms"])

    @patch("ezcli_app.internet_checker.ping_host", return_value=(False, None, "timed out"))
    @patch("socket.socket")
    def test_check_internet_reachability_failure(self, mock_sock_cls, mock_ping):
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 111  # Connection refused / timeout
        mock_sock_cls.return_value = mock_sock

        res = check_internet_reachability(hosts=["1.1.1.1"])
        self.assertFalse(res["success"])
        self.assertIsNone(res["latency_ms"])
        self.assertIn("Offline", res["status_str"])

    def test_get_diagnostic_reason_all_cases(self):
        # Case 1: All green
        r1 = {
            "router": {"success": True, "target": "192.168.1.1"},
            "dns": {"success": True},
            "internet": {"success": True},
        }
        self.assertIn("All systems operational", get_diagnostic_reason(r1))

        # Case 2: No network / gateway
        r2 = {
            "router": {"success": False, "target": "None"},
            "dns": {"success": False},
            "internet": {"success": False},
        }
        self.assertIn("not connected to any network", get_diagnostic_reason(r2))

        # Case 3: Router unreachable
        r3 = {
            "router": {"success": False, "target": "192.168.1.1"},
            "dns": {"success": False},
            "internet": {"success": False},
        }
        self.assertIn("Cannot reach your local router", get_diagnostic_reason(r3))

        # Case 4: Router OK, but DNS & Internet fail (ISP outage)
        r4 = {
            "router": {"success": True, "target": "192.168.1.1"},
            "dns": {"success": False},
            "internet": {"success": False},
        }
        self.assertIn("ISP may be down", get_diagnostic_reason(r4))

        # Case 5: Router & Internet OK, but DNS fails
        r5 = {
            "router": {"success": True, "target": "192.168.1.1"},
            "dns": {"success": False, "resolvers": ["192.168.1.1"]},
            "internet": {"success": True},
        }
        self.assertIn("DNS resolution failed", get_diagnostic_reason(r5))

        # Case 6: Router & DNS OK, but Internet fails (Firewall / captive portal)
        r6 = {
            "router": {"success": True, "target": "192.168.1.1"},
            "dns": {"success": True},
            "internet": {"success": False},
        }
        self.assertIn("firewall or captive portal", get_diagnostic_reason(r6))

        # Case 7: Router blocks ICMP, but DNS & Internet OK
        r7 = {
            "router": {"success": False, "target": "192.168.1.1"},
            "dns": {"success": True},
            "internet": {"success": True},
        }
        self.assertIn("Internet is working", get_diagnostic_reason(r7))

    def test_format_stage_pipeline_token(self):
        tok_ok = format_stage_pipeline_token("Router", {"success": True, "latency_ms": 1.5})
        self.assertIn("Router", tok_ok)
        self.assertIn("✔", tok_ok)
        self.assertIn("1.5 ms", tok_ok)

        tok_fail = format_stage_pipeline_token("DNS", {"success": False, "status_str": "✖ Failed"})
        self.assertIn("DNS", tok_fail)
        self.assertIn("✖", tok_fail)
        self.assertIn("Failed", tok_fail)

    @patch("ezcli_app.internet_checker.diagnose_internet")
    def test_render_internet_check_output(self, mock_diag):
        mock_diag.return_value = {
            "router": {
                "success": True,
                "target": "192.168.1.1",
                "interface": "wlan0",
                "latency_ms": 1.8,
                "status_str": "✔ Reachable",
                "detail": "Gateway active",
            },
            "dns": {
                "success": True,
                "target": "google.com",
                "resolved_ip": "142.250.190.46",
                "resolvers": ["1.1.1.1"],
                "latency_ms": 15.2,
                "status_str": "✔ Resolved",
                "detail": "Resolved to 142.250.190.46",
            },
            "internet": {
                "success": True,
                "target": "1.1.1.1",
                "latency_ms": 22.4,
                "status_str": "✔ Reachable",
                "detail": "Public endpoint verified",
            },
            "diagnostic_reason": "All systems operational — your internet connection is active and healthy!",
            "is_healthy": True,
        }

        console = Console(record=True, width=100)
        render_internet_check(console=console)
        output = console.export_text()

        self.assertIn("Internet Connection Pipeline", output)
        self.assertIn("Router", output)
        self.assertIn("DNS", output)
        self.assertIn("Internet", output)
        self.assertIn("1.8 ms", output)
        self.assertIn("15.2 ms", output)
        self.assertIn("22.4 ms", output)
        self.assertIn("Why internet isn't working", output)
        self.assertIn("All systems operational", output)


if __name__ == "__main__":
    unittest.main()
