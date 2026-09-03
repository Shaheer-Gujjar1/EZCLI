"""Tests for CLI argument parsing, help output, and dispatching."""

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EZCLI_BIN = REPO_ROOT / "ezcli"


class TestCLI(unittest.TestCase):
    def run_ezcli(self, *args, input_str=None):
        cmd = [sys.executable, str(EZCLI_BIN)] + list(args)
        proc = subprocess.run(
            cmd,
            input=input_str,
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

    def test_copy_and_undo_cli(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="ezcli_cli_test_") as tmp:
            src = os.path.join(tmp, "hello.txt")
            dst = os.path.join(tmp, "copied.txt")
            with open(src, "w") as f:
                f.write("test content")

            # ezcli copy -y src dst
            res = self.run_ezcli("copy", "-y", src, dst)
            self.assertEqual(res.returncode, 0)
            self.assertTrue(os.path.exists(dst))

            # ezcli undo (piping 'y' for confirmation)
            res_undo = self.run_ezcli("undo", input_str="y\n")
            self.assertEqual(res_undo.returncode, 0)
            self.assertFalse(os.path.exists(dst))


if __name__ == "__main__":
    unittest.main()



