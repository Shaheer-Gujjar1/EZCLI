"""Tests for 'ez list' subcommand, Form 1 instant listing, and Form 2 components."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from ezcli_app.list_cli import (
    format_permissions_english,
    format_human_size,
    format_timestamp,
    scan_directory_entries,
    calculate_dir_size,
    run_cli_list,
)


class TestListSubcommand(unittest.TestCase):
    def test_format_permissions_english(self):
        # 0o755: rwxr-xr-x
        self.assertEqual(
            format_permissions_english(0o755),
            "You: read+write+exec · Others: read+exec"
        )
        # 0o644: rw-r--r--
        self.assertEqual(
            format_permissions_english(0o644),
            "You: read+write · Others: read-only"
        )
        # 0o700: rwx------
        self.assertEqual(
            format_permissions_english(0o700),
            "You: read+write+exec · Others: none"
        )
        # 0o600: rw-------
        self.assertEqual(
            format_permissions_english(0o600),
            "You: read+write · Others: none"
        )
        # 0o444: r--r--r--
        self.assertEqual(
            format_permissions_english(0o444),
            "You: read-only · Others: read-only"
        )
        # 0o000: ---------
        self.assertEqual(
            format_permissions_english(0o000),
            "You: none · Others: none"
        )

    def test_format_human_size(self):
        self.assertEqual(format_human_size(0), "0 B")
        self.assertEqual(format_human_size(512), "512 B")
        self.assertEqual(format_human_size(1024), "1.0 KB")
        self.assertEqual(format_human_size(1536), "1.5 KB")
        self.assertEqual(format_human_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_human_size(1024 * 1024 * 1024), "1.0 GB")

    def test_format_timestamp(self):
        ts = 1700000000.0
        formatted = format_timestamp(ts)
        self.assertRegex(formatted, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

    def test_scan_directory_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Create a regular file
            f1 = tmp_path / "hello.txt"
            f1.write_text("hello world")
            # Create a hidden file
            f2 = tmp_path / ".secret"
            f2.write_text("secret content")
            # Create a directory
            d1 = tmp_path / "mydir"
            d1.mkdir()
            (d1 / "nested.txt").write_text("nested data")

            # Scan with hidden files
            ok, entries_all, err = scan_directory_entries(str(tmp_path), show_hidden=True)
            self.assertTrue(ok)
            names_all = [e["name"] for e in entries_all]
            self.assertIn("hello.txt", names_all)
            self.assertIn(".secret", names_all)
            self.assertIn("mydir", names_all)

            # Check hidden flag
            secret_entry = next(e for e in entries_all if e["name"] == ".secret")
            self.assertTrue(secret_entry["is_hidden"])
            hello_entry = next(e for e in entries_all if e["name"] == "hello.txt")
            self.assertFalse(hello_entry["is_hidden"])
            self.assertFalse(hello_entry["is_dir"])
            dir_entry = next(e for e in entries_all if e["name"] == "mydir")
            self.assertTrue(dir_entry["is_dir"])

            # Scan without hidden files
            ok_no_h, entries_no_hidden, err_no_h = scan_directory_entries(str(tmp_path), show_hidden=False)
            self.assertTrue(ok_no_h)
            names_no_hidden = [e["name"] for e in entries_no_hidden]
            self.assertIn("hello.txt", names_no_hidden)
            self.assertIn("mydir", names_no_hidden)
            self.assertNotIn(".secret", names_no_hidden)

            self.assertNotIn(".secret", names_no_hidden)

    def test_calculate_dir_size(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "file1.bin").write_bytes(b"A" * 100)
            sub = tmp_path / "subdir"
            sub.mkdir()
            (sub / "file2.bin").write_bytes(b"B" * 200)

            total_size = calculate_dir_size(tmp_path)
            self.assertGreaterEqual(total_size, 300)

    def test_path_arguments_rejected(self):
        # ez list must strictly reject any path arguments with SystemExit(1)
        with self.assertRaises(SystemExit) as ctx:
            run_cli_list(["/var/log"])
        self.assertEqual(ctx.exception.code, 1)

        with self.assertRaises(SystemExit) as ctx2:
            run_cli_list(["some_folder"])
        self.assertEqual(ctx2.exception.code, 1)

        with self.assertRaises(SystemExit) as ctx3:
            run_cli_list(["arg1", "arg2"])
        self.assertEqual(ctx3.exception.code, 1)

    @patch("ezcli_app.list_cli.run_form2_choose_directory_tui")
    def test_choose_directory_dispatch(self, mock_form2):
        run_cli_list(["choose-directory"])
        mock_form2.assert_called_once()

    @patch("ezcli_app.list_cli.run_form1_instant_listing")
    @patch("ezcli_app.explorer.explorer_app.run_destination_picker")
    @patch("ezcli_app.main.check_textual_installed", return_value=True)
    def test_form2_prints_chosen_dir_listing(self, mock_chk, mock_picker, mock_form1):
        from ezcli_app.list_cli import run_form2_choose_directory_tui
        from rich.console import Console

        mock_picker.return_value = "/tmp"
        c = Console(record=True)
        with patch("sys.stdout.isatty", return_value=False):
            run_form2_choose_directory_tui(console=c)

        mock_form1.assert_called_once_with(target_dir="/tmp", console=c)

    @patch("ezcli_app.list_tui.run_list_tui_app")
    @patch("rich.prompt.Prompt.ask", return_value="i")
    @patch("ezcli_app.list_cli.run_form1_instant_listing")
    @patch("ezcli_app.explorer.explorer_app.run_destination_picker")
    @patch("ezcli_app.main.check_textual_installed", return_value=True)
    def test_form2_launches_inspector_on_i(self, mock_chk, mock_picker, mock_form1, mock_ask, mock_tui):
        from ezcli_app.list_cli import run_form2_choose_directory_tui
        from rich.console import Console

        mock_picker.return_value = "/tmp"
        c = Console(record=True)
        with patch("sys.stdout.isatty", return_value=True), patch("sys.stdin.isatty", return_value=True):
            run_form2_choose_directory_tui(console=c)

        mock_form1.assert_called_once_with(target_dir="/tmp", console=c)
        mock_tui.assert_called_once_with("/tmp")

    @patch("ezcli_app.list_cli.run_form1_instant_listing")
    @patch("ezcli_app.explorer.explorer_app.run_destination_picker")
    @patch("ezcli_app.main.check_textual_installed", return_value=True)
    def test_form2_cancelled_picker(self, mock_chk, mock_picker, mock_form1):
        from ezcli_app.list_cli import run_form2_choose_directory_tui
        from rich.console import Console

        mock_picker.return_value = None
        c = Console(record=True)
        run_form2_choose_directory_tui(console=c)

        mock_form1.assert_not_called()


if __name__ == "__main__":
    unittest.main()

