"""Tests for CLI argument parsing, help output, and dispatching."""

import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EZCLI_BIN = REPO_ROOT / "ezcli"


class TestCLI(unittest.TestCase):
    def run_ezcli(self, *args):
        cmd = [sys.executable, str(EZCLI_BIN)] + list(args)
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
        )
        return proc

    def test_help_subcommand(self):
        res = self.run_ezcli("help")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Available Subcommands", res.stdout)
        self.assertIn("system-info", res.stdout)
        self.assertIn("stats", res.stdout)
        self.assertIn("disk-info", res.stdout)
        self.assertIn("big-files", res.stdout)
        self.assertIn("package-search", res.stdout)
        self.assertIn("package", res.stdout)
        self.assertIn("available-updates", res.stdout)
        self.assertIn("service-status", res.stdout)
        self.assertIn("network-info", res.stdout)
        self.assertIn("logs", res.stdout)

    def test_version_flag(self):
        res = self.run_ezcli("--version")
        self.assertEqual(res.returncode, 0)
        self.assertIn("v0.1.0", res.stdout)

    def test_unknown_subcommand(self):
        res = self.run_ezcli("foobar-unknown-command")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Unknown subcommand", res.stdout)

    def test_missing_required_argument(self):
        res = self.run_ezcli("package")
        self.assertEqual(res.returncode, 1)
        self.assertIn("requires argument", res.stdout)

    def test_system_info_direct(self):
        res = self.run_ezcli("system-info")
        self.assertEqual(res.returncode, 0)
        self.assertIn("System Information", res.stdout)
        self.assertIn("Distribution", res.stdout)

    def test_stats_direct(self):
        res = self.run_ezcli("stats")
        self.assertEqual(res.returncode, 0)
        self.assertIn("CPU Load", res.stdout)
        self.assertIn("Memory", res.stdout)

    def test_disk_info_direct(self):
        res = self.run_ezcli("disk-info")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Storage Partitions", res.stdout)

    def test_installed_packages_direct(self):
        res = self.run_ezcli("installed-packages")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed Packages", res.stdout)

    def test_installed_package_search_direct(self):
        res = self.run_ezcli("installed-package-search", "curl")
        self.assertEqual(res.returncode, 0)
        self.assertIn("curl", res.stdout)

    def test_installed_package_search_missing_arg(self):
        res = self.run_ezcli("installed-package-search")
        self.assertEqual(res.returncode, 1)
        self.assertIn("requires argument", res.stdout)


if __name__ == "__main__":
    unittest.main()


