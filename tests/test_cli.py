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
            stdin=subprocess.DEVNULL if input_str is None else None,
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
        self.assertIn("package-info", res.stdout)
        self.assertIn("available-updates", res.stdout)
        self.assertIn("service-status", res.stdout)
        self.assertIn("network-info", res.stdout)
        self.assertIn("logs", res.stdout)
        self.assertIn("compress", res.stdout)
        self.assertIn("extract", res.stdout)
        self.assertIn("time-machine", res.stdout)
        self.assertIn("ez <subcommand>", res.stdout)


    def test_version_command_retired(self):
        # 'ez version' is completely retired; running it returns unknown subcommand
        res = self.run_ez("version")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Unknown subcommand", res.stdout)
        res_target = self.run_ez("version", "bash")
        self.assertEqual(res_target.returncode, 1)
        self.assertIn("Unknown subcommand", res_target.stdout)

    def test_version_retired_from_features(self):
        from ezcli_app.config import FEATURES
        self.assertNotIn("version", [f.subcommand for f in FEATURES])
        self.assertNotIn("version", [f.id for f in FEATURES])

    def test_flags_rejected(self):
        # EasyCLI is completely flagless — all flags must be rejected
        for flag in ("--version", "-v", "-h", "--help", "-p", "--print-path", "-f"):
            res = self.run_ez(flag)
            self.assertEqual(res.returncode, 1, f"Flag '{flag}' should be rejected")
            self.assertIn("flagless", res.stdout.lower())

    def test_aliases_rejected(self):
        # All aliases must be rejected; only canonical subcommands are supported
        aliases = ["installed", "choose", "explorer", "new-folder", "new-file", "del", "remove", "version"]
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
        res = self.run_ez("service-status")
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
        # Backward compatibility alias
        res = self.run_ez("installed-packages")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed", res.stdout)

    def test_list_installed_packages_direct(self):
        res = self.run_ez("list-installed-packages")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed", res.stdout)

    def test_list_installed_packages_apps_filter(self):
        res = self.run_ez("list-installed-packages", "apps")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed Applications", res.stdout)

    def test_list_installed_packages_packages_filter(self):
        res = self.run_ez("list-installed-packages", "packages")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed Packages", res.stdout)

    def test_list_installed_packages_interactive_apps(self):
        res = self.run_ez("list-installed-packages", input_str="1\n")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Installed Applications", res.stdout)

    def test_list_installed_packages_interactive_packages(self):
        res = self.run_ez("list-installed-packages", input_str="2\n")
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

    def test_features_sorted_alphabetically(self):
        from ezcli_app.config import FEATURES
        subcommands = [f.subcommand for f in FEATURES]
        self.assertEqual(subcommands, sorted(subcommands))

    def test_adaptive_features_table(self):
        from rich.console import Console
        from ezcli_app.menu import build_features_table

        for w in (120, 85, 65, 45):
            c = Console(width=w, height=40, record=True)
            table = build_features_table(w)
            c.print(table)
            output = c.export_text()
            lines = [l for l in output.splitlines() if l.strip()]
            self.assertTrue(len(lines) > 0)
            max_len = max(len(l) for l in lines)
            self.assertLessEqual(
                max_len,
                w,
                f"Table rendered at width {w} exceeded boundary with line length {max_len}",
            )
            # Verify rounded borders intact on top and bottom
            self.assertTrue(any("╭" in l and "╮" in l for l in lines))
            self.assertTrue(any("╰" in l and "╯" in l for l in lines))

    def test_adaptive_header_panel(self):
        from rich.console import Console
        from ezcli_app.distro import detect_distro
        from ezcli_app.menu import build_header_panel

        distro = detect_distro()
        for w in (120, 80, 60, 45):
            c = Console(width=w, height=40, record=True)
            panel = build_header_panel(w, distro)
            c.print(panel)
            output = c.export_text()
            lines = [l for l in output.splitlines() if l.strip()]
            self.assertTrue(len(lines) > 0)
            max_len = max(len(l) for l in lines)
            self.assertLessEqual(
                max_len,
                w,
                f"Header panel rendered at width {w} exceeded boundary with line length {max_len}",
            )

    def test_terminal_resize_handler(self):
        import ezcli_app.menu as menu

        # When not in menu prompt, handler should be silent
        menu._in_menu_prompt = False
        menu._sigwinch_handler(0, None)

        # When in menu prompt, handler should raise TerminalResizeInterrupt
        menu._in_menu_prompt = True
        with self.assertRaises(menu.TerminalResizeInterrupt):
            menu._sigwinch_handler(0, None)
        self.assertFalse(menu._in_menu_prompt)

    def test_list_subcommand_direct(self):
        res = self.run_ez("list")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Name", res.stdout)
        self.assertIn("Size", res.stdout)
        self.assertIn("Modified", res.stdout)
        # Should include items from the repo
        self.assertIn("README.md", res.stdout)

    def test_list_subcommand_rejects_paths(self):
        res = self.run_ez("list", "/var")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Path Arguments Not Allowed", res.stdout)
        self.assertIn("ez list choose-directory", res.stdout)

    def test_time_machine_direct_list(self):
        res = self.run_ez("time-machine", "list")
        self.assertEqual(res.returncode, 0)
        self.assertIn("Time Machine", res.stdout)

    def test_time_machine_rejects_paths(self):
        res = self.run_ez("time-machine", "/var")
        self.assertEqual(res.returncode, 1)
        self.assertIn("Invalid Argument", res.stdout)
        self.assertIn("ez time-machine", res.stdout)


if __name__ == "__main__":
    unittest.main()



