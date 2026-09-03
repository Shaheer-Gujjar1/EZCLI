"""Tests for defensive data collectors."""

import os
import unittest
from ezcli_app.collectors import (
    format_bytes,
    collect_system_info,
    collect_stats,
    collect_disk_info,
    collect_big_files,
    collect_package_search,
    collect_package_info,
    collect_available_updates,
    collect_service_status,
    collect_network_info,
    collect_logs,
    collect_installed_packages,
)


class TestCollectors(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024 * 5), "5.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 2), "2.0 GB")

    def test_collect_system_info(self):
        info = collect_system_info()
        self.assertIn("os_name", info)
        self.assertIn("hostname", info)
        self.assertIn("kernel", info)
        self.assertIn("uptime", info)
        self.assertNotEqual(info["hostname"], "")
        self.assertNotEqual(info["kernel"], "")

    def test_collect_stats(self):
        stats = collect_stats()
        self.assertGreaterEqual(stats["cpu_cores"], 1)
        self.assertGreaterEqual(stats["ram_percent"], 0.0)
        self.assertLessEqual(stats["ram_percent"], 100.0)
        self.assertIn("ram_total_str", stats)
        self.assertIn("ram_used_str", stats)

    def test_collect_disk_info(self):
        disks = collect_disk_info()
        # On a Linux system there is always at least one root mount or persistent mount
        self.assertIsInstance(disks, list)
        for d in disks:
            self.assertIn("mount", d)
            self.assertIn("percent", d)
            self.assertNotIn("tmpfs", d["filesystem"])
            self.assertNotIn("devtmpfs", d["filesystem"])

    def test_collect_big_files_valid_and_invalid(self):
        # Valid directory (current repo directory)
        res = collect_big_files(".", limit=5)
        self.assertTrue(res["exists"])
        self.assertEqual(res["error"], "")
        self.assertIsInstance(res["items"], list)

        # Non-existent directory
        res_bad = collect_big_files("/definitely/does/not/exist/12345")
        self.assertFalse(res_bad["exists"])
        self.assertIn("does not exist", res_bad["error"])

    def test_collect_package_search(self):
        # Search for a ubiquitous package
        res = collect_package_search("curl", limit=5)
        self.assertEqual(res["term"], "curl")
        self.assertIsInstance(res["packages"], list)
        if res["packages"]:
            self.assertIn("name", res["packages"][0])

    def test_collect_package_info(self):
        # Package curl is standard
        res = collect_package_info("curl")
        self.assertEqual(res["name"], "curl")
        self.assertTrue(res["found"])
        self.assertIn("is_installed", res)

        # Non-existent package
        res_none = collect_package_info("non_existent_fake_package_xyz_999")
        self.assertFalse(res_none["found"])
        self.assertIn("not found", res_none["error"])

    def test_collect_available_updates(self):
        res = collect_available_updates()
        self.assertIn("updates", res)
        self.assertIn("count", res)
        self.assertIn("is_stale", res)
        self.assertIn("last_updated_str", res)

    def test_collect_service_status(self):
        # Service NetworkManager or dbus
        res = collect_service_status("dbus")
        self.assertEqual(res["service"], "dbus")
        self.assertIn(res["active_state"], ["active", "inactive", "failed", "unknown"])

        # Non-existent service
        res_bad = collect_service_status("non_existent_service_xyz_999")
        self.assertIn(res_bad["active_state"], ["inactive", "unknown", "not-found", "failed"])

    def test_collect_network_info(self):
        net = collect_network_info()
        self.assertIn("interfaces", net)
        self.assertIn("default_gateway", net)
        self.assertIn("online_state", net)
        self.assertIsInstance(net["interfaces"], list)

    def test_collect_logs(self):
        logs = collect_logs(lines_count=5)
        self.assertIn("logs", logs)
        self.assertIn("permission_limited", logs)
        self.assertIsInstance(logs["logs"], list)

    def test_collect_installed_packages(self):
        # All packages
        res = collect_installed_packages()
        self.assertGreater(res["total_apt"], 0)
        self.assertGreater(res["total_count"], 0)
        self.assertIsInstance(res["matches"], list)

        # Filtered packages
        res_curl = collect_installed_packages("curl")
        self.assertGreater(len(res_curl["matches"]), 0)
        self.assertTrue(any("curl" in p["name"].lower() for p in res_curl["matches"]))

        # Non-matching filter
        res_none = collect_installed_packages("definitelynotaninstalledpkgxyz123")
        self.assertEqual(len(res_none["matches"]), 0)


if __name__ == "__main__":
    unittest.main()

