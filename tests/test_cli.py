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
        self.assertIn("compress", res.stdout)
        self.assertIn("extract-here", res.stdout)
        self.assertIn("extract", res.stdout)
        self.assertIn("ez <subcommand>", res.stdout)

    def test_version_subcommand(self):
        from ezcli_app import __version__
        res = self.run_ez("version")
        self.assertEqual(res.returncode, 0)
        self.assertIn(f"v{__version__}", res.stdout)
        self.assertIn("EasyCLI (ez)", res.stdout)
        self.assertIn("ez version", res.stdout)

    def test_version_subcommand_with_target(self):
        res = self.run_ez("version", "bash")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Version Information: bash", res.stdout)
        self.assertIn("Binary", res.stdout)

    def test_flags_rejected(self):
        # EasyCLI is completely flagless — all flags must be rejected
        for flag in ("--version", "-v", "-h", "--help", "-p", "--print-path", "-f"):
            res = self.run_ez(flag)
            self.assertEqual(res.returncode, 1, f"Flag '{flag}' should be rejected")
            self.assertIn("flagless", res.stdout.lower())

    def test_aliases_rejected(self):
        # All aliases must be rejected; only canonical subcommands are supported
        aliases = ["installed", "choose", "explorer", "new-folder", "new-file", "del", "remove"]
        for alias in aliases:
            res = self.run_ez(alias)
            self.assertEqual(res.returncode, 1, f"Alias '{alias}' should be rejected")
            self.assertIn("Unknown subcommand", res.stdout)

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

    def test_copy_direct_file(self):
        res = self.run_ez("copy", "README.md")
        self.assertEqual(res.returncode, 0)
        self.assertIn("EasyCLI Clipboard", res.stdout)
        self.assertIn("COPY", res.stdout)
        self.assertIn("README.md", res.stdout)

    def test_copy_subfolder_rejected(self):
        res = self.run_ez("copy", "tests/test_cli.py")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Direct Targeting Restricted", res.stdout)
        self.assertIn("ez copy choose-directory", res.stdout)

    def test_check_internet_subcommand(self):
        res = self.run_ez("check-internet")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Internet Connection Pipeline", res.stdout)
        self.assertIn("Why internet isn't working", res.stdout)

    def test_connect_wifi_in_help(self):
        res = self.run_ez("help")
        self.assertEqual(res.returncode, 0)
        self.assertIn("connect-wifi", res.stdout)

    def test_search_file_in_help(self):
        res = self.run_ez("help")
        self.assertEqual(res.returncode, 0)
        self.assertIn("search-file", res.stdout)

    def test_search_file_usage_no_args(self):
        res = self.run_ez("search-file")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage:", res.stdout)
        self.assertIn("ez search-file <term>", res.stdout)

    def test_compress_in_help(self):
        res = self.run_ez("help")
        self.assertEqual(res.returncode, 0)
        self.assertIn("compress", res.stdout)


if __name__ == "__main__":
    unittest.main()
