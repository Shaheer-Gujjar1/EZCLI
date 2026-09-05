"""Tests for the live stats system and process monitor."""

import os
import signal
import subprocess
import sys
import unittest

from ezcli_app.config import FEATURES_BY_SUBCOMMAND
from ezcli_app.stats.metrics import SystemMetricsCollector
from ezcli_app.stats.stats_app import StatsApp, make_gauge_markup


class TestStatsMetrics(unittest.TestCase):
    """Test the low-overhead Linux metrics engine."""

    def setUp(self):
        self.collector = SystemMetricsCollector()

    def test_cpu_percentages(self):
        overall, per_core = self.collector.get_cpu_percentages()
        self.assertIsInstance(overall, float)
        self.assertGreaterEqual(overall, 0.0)
        self.assertLessEqual(overall, 100.0)
        self.assertIsInstance(per_core, list)
        self.assertGreaterEqual(len(per_core), 1)
        for core in per_core:
            self.assertIn("core_id", core)
            self.assertIn("name", core)
            self.assertIn("percent", core)
            self.assertGreaterEqual(core["percent"], 0.0)
            self.assertLessEqual(core["percent"], 100.0)

    def test_memory_info(self):
        mem = self.collector.get_memory_info()
        self.assertIn("ram_total_bytes", mem)
        self.assertIn("ram_used_bytes", mem)
        self.assertIn("ram_percent", mem)
        self.assertIn("ram_used_str", mem)
        self.assertIn("swap_percent", mem)
        self.assertGreater(mem["ram_total_bytes"], 0)
        self.assertGreaterEqual(mem["ram_percent"], 0.0)
        self.assertLessEqual(mem["ram_percent"], 100.0)

    def test_uptime(self):
        sec, formatted = self.collector.get_uptime()
        self.assertGreater(sec, 0.0)
        self.assertTrue(len(formatted) > 0)

    def test_system_overview(self):
        overview = self.collector.get_system_overview()
        self.assertIn("hostname", overview)
        self.assertIn("os_name", overview)
        self.assertIn("kernel", overview)
        self.assertIn("cores", overview)
        self.assertIn("cpu_percent", overview)
        self.assertIn("ram_percent", overview)
        self.assertIn("load_1m", overview)

    def test_get_processes_and_filtering(self):
        procs, tasks = self.collector.get_processes(sort_by="cpu", reverse=True)
        self.assertGreater(len(procs), 0)
        self.assertGreater(tasks["total"], 0)

        # Check process structure
        first = procs[0]
        self.assertIn("pid", first)
        self.assertIn("user", first)
        self.assertIn("cpu", first)
        self.assertIn("mem", first)
        self.assertIn("rss_str", first)
        self.assertIn("comm", first)

        # Test filtering by current process PID
        my_pid = os.getpid()
        filtered_procs, _ = self.collector.get_processes(filter_text=str(my_pid))
        pids = [p["pid"] for p in filtered_procs]
        self.assertIn(my_pid, pids)

    def test_process_details(self):
        my_pid = os.getpid()
        details = self.collector.get_process_details(my_pid)
        self.assertTrue(details["exists"])
        self.assertEqual(details["pid"], my_pid)
        self.assertIn("python", details["cmdline"].lower())
        self.assertGreaterEqual(details["threads"], 1)

    def test_process_details_nonexistent(self):
        details = self.collector.get_process_details(99999999)
        self.assertFalse(details["exists"])

    def test_terminate_process_nonexistent(self):
        success, msg = self.collector.terminate_process(99999999, signal.SIGTERM)
        self.assertFalse(success)
        self.assertIn("no longer exists", msg)

    def test_make_gauge_markup(self):
        markup_low = make_gauge_markup(20.0, width=10)
        self.assertIn("bold green", markup_low)
        self.assertIn("20.0%", markup_low)

        markup_high = make_gauge_markup(95.0, width=10)
        self.assertIn("bold red", markup_high)
        self.assertIn("95.0%", markup_high)


class TestStatsCLI(unittest.TestCase):
    """Test CLI dispatch and registration for ez stats."""

    def test_feature_registration(self):
        self.assertIn("stats", FEATURES_BY_SUBCOMMAND)
        feat = FEATURES_BY_SUBCOMMAND["stats"]
        self.assertEqual(feat.subcommand, "stats")

    def test_stats_cli_non_tty_output(self):
        """When run without a TTY (e.g. piped or captured), it outputs the Rich summary card."""
        res = subprocess.run(
            [sys.executable, "-m", "ezcli_app.main", "stats"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("CPU Load", res.stdout)
        self.assertIn("Memory", res.stdout)


if __name__ == "__main__":
    unittest.main()
