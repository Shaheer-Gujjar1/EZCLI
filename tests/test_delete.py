"""Unit tests for ez delete subcommand, safety consent, non-force-first logic, and auto-elevation."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.delete_cli import (
    delete_single_item,
    run_cli_delete,
    validate_direct_delete_target,
)
from ezcli_app.elevation import elevated_file_delete
from ezcli_app.privileged_helper import helper_file_delete


class TestDeleteCLI(unittest.TestCase):
    """Tests for delete command, direct validations, force prompts, and elevation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.console = Console(record=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_direct_delete_subfolder_rejected(self):
        """Verify subfolder paths are rejected with guidance to use choose-directory."""
        invalid_cases = [
            "folder/sub/",
            "folder/sub",
            "a/b/c.txt",
            "../sibling.txt",
            "/tmp/arbitrary.txt",
        ]
        for case in invalid_cases:
            valid, err, _, _ = validate_direct_delete_target(case, cwd=self.temp_dir)
            self.assertFalse(valid, f"Expected {case} to be rejected")
            self.assertIn("current directory", err.lower())
            self.assertIn("choose-directory", err)

    def test_validate_direct_delete_valid_file(self):
        """Verify valid file in current directory is accepted."""
        test_file = os.path.join(self.temp_dir, "report.pdf")
        with open(test_file, "w") as f:
            f.write("content")

        valid, err, resolved, is_dir = validate_direct_delete_target("report.pdf", cwd=self.temp_dir)
        self.assertTrue(valid, f"Unexpected error: {err}")
        self.assertEqual(resolved, test_file)
        self.assertFalse(is_dir)

    def test_validate_direct_delete_valid_folder(self):
        """Verify valid folder with trailing slash in current directory is accepted."""
        test_folder = os.path.join(self.temp_dir, "my_data")
        os.makedirs(test_folder)

        valid, err, resolved, is_dir = validate_direct_delete_target("my_data/", cwd=self.temp_dir)
        self.assertTrue(valid, f"Unexpected error: {err}")
        self.assertEqual(resolved, test_folder)
        self.assertTrue(is_dir)

    def test_delete_file_direct_success(self):
        """Test safe non-forced deletion of a regular file."""
        test_file = os.path.join(self.temp_dir, "temp.log")
        with open(test_file, "w") as f:
            f.write("log data")

        success, msg = delete_single_item(test_file, is_dir=False, console=self.console)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(test_file))

    def test_delete_empty_folder_direct_success(self):
        """Test safe non-forced deletion of an empty directory."""
        empty_folder = os.path.join(self.temp_dir, "empty_dir")
        os.makedirs(empty_folder)

        success, msg = delete_single_item(empty_folder, is_dir=True, console=self.console)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(empty_folder))

    def test_delete_non_empty_folder_force_refused(self):
        """Test that non-empty directory is skipped when user refuses forced deletion."""
        non_empty = os.path.join(self.temp_dir, "non_empty_dir")
        os.makedirs(non_empty)
        with open(os.path.join(non_empty, "item.txt"), "w") as f:
            f.write("keep me")

        # Refuse force
        with patch("rich.prompt.Confirm.ask", return_value=False):
            success, msg = delete_single_item(non_empty, is_dir=True, console=self.console)

        self.assertFalse(success)
        self.assertIn("force refused", msg.lower())
        self.assertTrue(os.path.exists(non_empty))

    def test_delete_non_empty_folder_force_accepted(self):
        """Test that non-empty directory is deleted when user consents to forced deletion."""
        non_empty = os.path.join(self.temp_dir, "non_empty_dir")
        os.makedirs(non_empty)
        with open(os.path.join(non_empty, "item.txt"), "w") as f:
            f.write("delete me")

        # Consent to force
        with patch("rich.prompt.Confirm.ask", return_value=True):
            success, msg = delete_single_item(non_empty, is_dir=True, console=self.console)

        self.assertTrue(success)
        self.assertIn("forcefully", msg.lower())
        self.assertFalse(os.path.exists(non_empty))

    def test_run_cli_delete_consent_refused(self):
        """Test that user declining initial deletion confirmation cancels operation."""
        test_file = os.path.join(self.temp_dir, "sensitive.key")
        with open(test_file, "w") as f:
            f.write("key")

        # Mock current working directory
        with patch("os.getcwd", return_value=self.temp_dir):
            with patch("rich.prompt.Confirm.ask", return_value=False):
                run_cli_delete(args=["sensitive.key"], console=self.console)

        # File must NOT have been deleted
        self.assertTrue(os.path.exists(test_file))
        output = self.console.export_text()
        self.assertIn("cancelled by user", output.lower())

    def test_run_cli_delete_direct_file_confirmed(self):
        """Test direct file deletion executes and shows summary card when confirmed."""
        test_file = os.path.join(self.temp_dir, "target.txt")
        with open(test_file, "w") as f:
            f.write("data")

        with patch("os.getcwd", return_value=self.temp_dir):
            with patch("rich.prompt.Confirm.ask", return_value=True):
                run_cli_delete(args=["target.txt"], console=self.console)

        self.assertFalse(os.path.exists(test_file))
        output = self.console.export_text()
        self.assertIn("Deleted 1 of 1 Item(s)", output)

    @patch("ezcli_app.explorer.explorer_app.run_delete_picker")
    def test_run_cli_delete_choose_directory_dispatch(self, mock_picker):
        """Test that choose-directory launches the mini explorer picker."""
        test_file = os.path.join(self.temp_dir, "picked.csv")
        with open(test_file, "w") as f:
            f.write("a,b,c")

        mock_picker.return_value = [test_file]
        with patch("rich.prompt.Confirm.ask", return_value=True):
            run_cli_delete(args=["choose-directory"], console=self.console)

        mock_picker.assert_called_once()
        self.assertFalse(os.path.exists(test_file))

    @patch("ezcli_app.delete_cli.elevated_file_delete")
    def test_delete_permission_error_triggers_elevation(self, mock_elevated):
        """Test that permission error triggers admin rights prompt and elevated delete."""
        test_file = os.path.join(self.temp_dir, "sys.conf")
        with open(test_file, "w") as f:
            f.write("conf")

        mock_elevated.return_value = (True, "")

        with patch("os.remove", side_effect=PermissionError("Permission denied")):
            with patch("rich.prompt.Confirm.ask", return_value=True):
                success, msg = delete_single_item(test_file, is_dir=False, console=self.console)

        self.assertTrue(success)
        mock_elevated.assert_called_once()

    def test_helper_file_delete_non_force_vs_force(self):
        """Test privileged helper honors non-force on non-empty directories."""
        folder = os.path.join(self.temp_dir, "helper_test_dir")
        os.makedirs(folder)
        with open(os.path.join(folder, "child.txt"), "w") as f:
            f.write("child")

        # 1. Non-forced delete on non-empty folder must fail
        res_unforced = helper_file_delete(folder, is_dir=True, force=False)
        self.assertFalse(res_unforced.get("success"))
        self.assertTrue(os.path.exists(folder))

        # 2. Forced delete on non-empty folder must succeed
        res_forced = helper_file_delete(folder, is_dir=True, force=True)
        self.assertTrue(res_forced.get("success"))
        self.assertFalse(os.path.exists(folder))


if __name__ == "__main__":
    unittest.main()
