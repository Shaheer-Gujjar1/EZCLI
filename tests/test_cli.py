"""Tests for CLI argument parsing, help output, and dispatching."""

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EZ_BIN = REPO_ROOT / "ez"


class TestCLI(unittest.TestCase):
    def run_ez(self, *args, input_str=None):
        cmd = [sys.executable, str(EZ_BIN)] + list(args)
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
        res = self.run_ez("help")
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
        self.assertIn("ez <subcommand>", res.stdout)

    def test_version_flag(self):
        from ezcli_app import __version__
        res = self.run_ez("--version")
        self.assertEqual(res.returncode, 0)
        self.assertIn(f"v{__version__}", res.stdout)
        self.assertIn("EasyCLI (ez)", res.stdout)

    def test_unknown_subcommand(self):
        res = self.run_ez("foobar-unknown-command")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Unknown subcommand", res.stdout)
        self.assertIn("ez help", res.stdout)

    def test_missing_required_argument(self):
        res = self.run_ez("package")
        self.assertEqual(res.returncode, 1)
        self.assertIn("requires argument", res.stdout)

    def test_system_info_direct(self):
        res = self.run_ez("system-info")
        self.assertEqual(res.returncode, 0)
        self.assertIn("System Information", res.stdout)
        self.assertIn("Distribution", res.stdout)

    def test_stats_direct(self):
        res = self.run_ez("stats")
        self.assertEqual(res.returncode, 0)
        self.assertIn("CPU Load", res.stdout)
        self.assertIn("Memory", res.stdout)

    def test_disk_info_direct(self):
        res = self.run_ez("disk-info")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Storage Partitions", res.stdout)

    def test_installed_packages_direct(self):
        res = self.run_ez("installed-packages")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed Packages", res.stdout)

    def test_installed_package_search_direct(self):
        res = self.run_ez("installed-package-search", "curl")
        self.assertEqual(res.returncode, 0)
        self.assertIn("curl", res.stdout)

    def test_paste_empty_clipboard(self):
        from ezcli_app.undo import clear_clipboard
        clear_clipboard()
        res = self.run_ez("paste")
        self.assertEqual(res.returncode, 0)
        self.assertIn("clipboard is currently empty", res.stdout.lower())

    def test_undo_and_redo_empty_states(self):
        from ezcli_app.undo import save_redo_history, save_undo_history
        save_undo_history([])
        save_redo_history([])

        res_undo = self.run_ez("undo")
        self.assertEqual(res_undo.returncode, 0)
        self.assertIn("no recent", res_undo.stdout.lower())

        res_redo = self.run_ez("redo")
        self.assertEqual(res_redo.returncode, 0)
        self.assertIn("no undone", res_redo.stdout.lower())


if __name__ == "__main__":
    unittest.main()
