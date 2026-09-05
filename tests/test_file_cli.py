"""Unit tests for direct copy, move, and paste CLI workflows in EasyCLI."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.file_cli import (
    run_cli_paste,
    run_cli_stage,
    validate_direct_stage_target,
)
from ezcli_app.undo import clear_clipboard, get_clipboard, set_clipboard


class TestFileCLIDirect(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ez_test_file_cli_")
        self.console = Console(record=True)
        clear_clipboard()

        # Create sample file and folder in test_dir
        self.sample_file = os.path.join(self.test_dir, "document.txt")
        with open(self.sample_file, "w") as f:
            f.write("test content")

        self.sample_folder = os.path.join(self.test_dir, "my_folder")
        os.makedirs(self.sample_folder, exist_ok=True)

        self.sub_folder = os.path.join(self.test_dir, "nested_dir")
        os.makedirs(self.sub_folder, exist_ok=True)
        self.sub_file = os.path.join(self.sub_folder, "inside.txt")
        with open(self.sub_file, "w") as f:
            f.write("inside content")

    def tearDown(self):
        clear_clipboard()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # Validations for Direct Staging Targets
    # --------------------------------------------------------------------------
    def test_validate_valid_file(self):
        valid, err, path, is_dir = validate_direct_stage_target("document.txt", cwd=self.test_dir)
        self.assertTrue(valid)
        self.assertEqual(err, "")
        self.assertEqual(path, self.sample_file)
        self.assertFalse(is_dir)

    def test_validate_valid_folder_without_slash(self):
        valid, err, path, is_dir = validate_direct_stage_target("my_folder", cwd=self.test_dir)
        self.assertTrue(valid)
        self.assertEqual(err, "")
        self.assertEqual(path, self.sample_folder)
        self.assertTrue(is_dir)

    def test_validate_valid_folder_with_slash(self):
        valid, err, path, is_dir = validate_direct_stage_target("my_folder/", cwd=self.test_dir)
        self.assertTrue(valid)
        self.assertEqual(err, "")
        self.assertEqual(path, self.sample_folder)
        self.assertTrue(is_dir)

    def test_validate_file_with_trailing_slash_rejected(self):
        valid, err, path, is_dir = validate_direct_stage_target("document.txt/", cwd=self.test_dir)
        self.assertFalse(valid)
        self.assertIn("trailing slash", err)

    def test_validate_nonexistent_item_rejected(self):
        valid, err, path, is_dir = validate_direct_stage_target("ghost.txt", cwd=self.test_dir)
        self.assertFalse(valid)
        self.assertIn("Cannot find", err)

    def test_validate_subfolder_path_rejected(self):
        valid, err, path, is_dir = validate_direct_stage_target("nested_dir/inside.txt", cwd=self.test_dir)
        self.assertFalse(valid)
        self.assertIn("current directory", err)
        self.assertIn("choose-directory", err)

    def test_validate_parent_traversal_rejected(self):
        valid, err, path, is_dir = validate_direct_stage_target("../outside.txt", cwd=self.test_dir)
        self.assertFalse(valid)
        self.assertIn("current directory", err)

    def test_validate_empty_rejected(self):
        valid, err, path, is_dir = validate_direct_stage_target("", cwd=self.test_dir)
        self.assertFalse(valid)
        self.assertIn("cannot be empty", err)

    def test_validate_choose_directory_marker(self):
        valid, err, path, is_dir = validate_direct_stage_target("choose-directory", cwd=self.test_dir)
        self.assertTrue(valid)
        self.assertEqual(path, "choose-directory")

    # --------------------------------------------------------------------------
    # Staging Tests (ez copy and ez move)
    # --------------------------------------------------------------------------
    @patch("ezcli_app.file_cli.run_source_picker")
    def test_stage_direct_file_no_picker(self, mock_picker: MagicMock):
        with patch("os.getcwd", return_value=self.test_dir):
            run_cli_stage("copy", targets=["document.txt"], console=self.console)
            mock_picker.assert_not_called()
            clip = get_clipboard()
            self.assertIsNotNone(clip)
            self.assertEqual(clip["action"], "copy")
            self.assertEqual(clip["items"], [self.sample_file])

    @patch("ezcli_app.file_cli.run_source_picker")
    def test_stage_direct_folder_no_picker(self, mock_picker: MagicMock):
        with patch("os.getcwd", return_value=self.test_dir):
            run_cli_stage("move", targets=["my_folder/"], console=self.console)
            mock_picker.assert_not_called()
            clip = get_clipboard()
            self.assertIsNotNone(clip)
            self.assertEqual(clip["action"], "move")
            self.assertEqual(clip["items"], [self.sample_folder])

    @patch("ezcli_app.file_cli.run_source_picker")
    def test_stage_subfolder_rejected_no_picker(self, mock_picker: MagicMock):
        with patch("os.getcwd", return_value=self.test_dir):
            run_cli_stage("copy", targets=["nested_dir/inside.txt"], console=self.console)
            mock_picker.assert_not_called()
            clip = get_clipboard()
            self.assertIsNone(clip)
            output = self.console.export_text()
            self.assertIn("Direct Targeting Restricted", output)

    @patch("ezcli_app.file_cli.run_source_picker", return_value=["/dummy/path"])
    def test_stage_no_args_launches_picker(self, mock_picker: MagicMock):
        with patch("os.getcwd", return_value=self.test_dir):
            run_cli_stage("copy", targets=None, console=self.console)
            mock_picker.assert_called_once()

    @patch("ezcli_app.file_cli.run_source_picker", return_value=["/dummy/path"])
    def test_stage_choose_directory_launches_picker(self, mock_picker: MagicMock):
        with patch("os.getcwd", return_value=self.test_dir):
            run_cli_stage("copy", targets=["choose-directory"], console=self.console)
            mock_picker.assert_called_once()

    # --------------------------------------------------------------------------
    # Paste Tests (ez paste and ez paste choose-directory)
    # --------------------------------------------------------------------------
    @patch("ezcli_app.file_cli.run_destination_picker")
    def test_paste_empty_clipboard(self, mock_picker: MagicMock):
        clear_clipboard()
        run_cli_paste(choose_dest=False, console=self.console)
        mock_picker.assert_not_called()
        output = self.console.export_text()
        self.assertIn("clipboard is currently empty", output.lower())

    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.file_cli.run_destination_picker")
    def test_paste_current_directory_no_picker(self, mock_picker: MagicMock, mock_confirm: MagicMock):
        # Stage file
        set_clipboard("copy", [self.sample_file])

        # Create destination directory
        paste_dir = os.path.join(self.test_dir, "paste_target")
        os.makedirs(paste_dir, exist_ok=True)

        with patch("os.getcwd", return_value=paste_dir):
            run_cli_paste(choose_dest=False, console=self.console)
            # Must NOT launch picker
            mock_picker.assert_not_called()
            # File should now exist at paste_dir/document.txt
            dest_file = os.path.join(paste_dir, "document.txt")
            self.assertTrue(os.path.exists(dest_file))
            with open(dest_file) as f:
                self.assertEqual(f.read(), "test content")

    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.file_cli.run_destination_picker")
    def test_paste_choose_directory_launches_picker(self, mock_picker: MagicMock, mock_confirm: MagicMock):
        paste_dir = os.path.join(self.test_dir, "custom_target")
        os.makedirs(paste_dir, exist_ok=True)
        mock_picker.return_value = paste_dir

        set_clipboard("copy", [self.sample_file])

        run_cli_paste(choose_dest=True, console=self.console)
        mock_picker.assert_called_once()
        dest_file = os.path.join(paste_dir, "document.txt")
        self.assertTrue(os.path.exists(dest_file))


if __name__ == "__main__":
    unittest.main()
