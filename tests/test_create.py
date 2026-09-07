"""Unit tests for EasyCLI create-folder and create-file features."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.create_cli import (
    run_cli_create_file,
    run_cli_create_folder,
    validate_item_name,
)
from ezcli_app.elevation import elevated_create_file
from ezcli_app.privileged_helper import helper_create_file


class TestCreateCLI(unittest.TestCase):
    """Tests for create-folder and create-file CLI and validation logic."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.console = Console(record=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_item_name_valid(self):
        """Test valid file and folder names."""
        valid_names = ["folder_name", "my-file.txt", "notes.md", "archive.tar.gz", "123"]
        for name in valid_names:
            is_valid, err = validate_item_name(name)
            self.assertTrue(is_valid, f"Expected {name} to be valid, got error: {err}")
            self.assertEqual(err, "")

    def test_validate_item_name_invalid(self):
        """Test invalid names (empty, path separators, reserved dots)."""
        invalid_names = [
            ("", "Name cannot be empty"),
            ("   ", "Name cannot be empty"),
            (".", "Name cannot be '.' or '..'"),
            ("..", "Name cannot be '.' or '..'"),
            ("folder/sub", "Path separators"),
            ("folder\\sub", "Path separators"),
            ("file\x00name", "invalid characters"),
        ]
        for name, expected_err_part in invalid_names:
            is_valid, err = validate_item_name(name)
            self.assertFalse(is_valid, f"Expected {name!r} to be invalid")
            self.assertIn(expected_err_part.lower(), err.lower())

    def test_create_folder_direct_success(self):
        """Test creating a folder directly in normal permissions."""
        target_path = os.path.join(self.temp_dir, "new_project")
        run_cli_create_folder(name=target_path, choose_dest=False, console=self.console)
        self.assertTrue(os.path.isdir(target_path))
        output = self.console.export_text()
        self.assertIn("Created folder successfully", output)

    def test_create_folder_already_exists(self):
        """Test creating a folder when it already exists."""
        target_path = os.path.join(self.temp_dir, "existing_folder")
        os.makedirs(target_path, exist_ok=True)
        run_cli_create_folder(name=target_path, choose_dest=False, console=self.console)
        output = self.console.export_text()
        self.assertIn("already exists", output)

    def test_create_file_direct_success(self):
        """Test creating a blank file directly."""
        target_path = os.path.join(self.temp_dir, "document.txt")
        run_cli_create_file(name=target_path, choose_dest=False, console=self.console)
        self.assertTrue(os.path.isfile(target_path))
        self.assertEqual(os.path.getsize(target_path), 0)
        output = self.console.export_text()
        self.assertIn("Created file successfully", output)

    def test_create_file_already_exists(self):
        """Test creating a file when an item with that name already exists."""
        target_path = os.path.join(self.temp_dir, "existing_file.txt")
        with open(target_path, "w") as f:
            f.write("content")
        run_cli_create_file(name=target_path, choose_dest=False, console=self.console)
        output = self.console.export_text()
        self.assertIn("already exists", output)

    @patch("ezcli_app.create_cli.elevated_make_dir")
    def test_create_folder_permission_error_triggers_elevation(self, mock_elevated):
        """Test that PermissionError offers and executes elevation."""
        target_path = os.path.join(self.temp_dir, "admin_folder")
        mock_elevated.return_value = True

        with patch("os.makedirs", side_effect=PermissionError("Permission denied")):
            with patch("rich.prompt.Confirm.ask", return_value=True):
                run_cli_create_folder(name=target_path, choose_dest=False, console=self.console)

        mock_elevated.assert_called_once_with(
            target_path,
            reason=f"Create folder '{target_path}'",
            console=self.console,
        )
        output = self.console.export_text()
        self.assertIn("Created folder successfully! 🔒 (Admin)", output)

    @patch("ezcli_app.create_cli.elevated_create_file")
    def test_create_file_permission_error_triggers_elevation(self, mock_elevated):
        """Test that PermissionError during file creation offers and executes elevation."""
        target_path = os.path.join(self.temp_dir, "admin_file.txt")
        mock_elevated.return_value = True

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("rich.prompt.Confirm.ask", return_value=True):
                run_cli_create_file(name=target_path, choose_dest=False, console=self.console)

        mock_elevated.assert_called_once_with(
            target_path,
            reason=f"Create blank file '{target_path}'",
            console=self.console,
        )
        output = self.console.export_text()
        self.assertIn("Created file successfully! 🔒 (Admin)", output)

    @patch("ezcli_app.explorer.explorer_app.ExplorerApp.run")
    def test_create_folder_choose_directory(self, mock_explorer_run):
        """Test choose-directory launches explorer to pick destination."""
        mock_explorer_run.return_value = self.temp_dir
        run_cli_create_folder(name="nested_folder", choose_dest=True, console=self.console)
        expected_path = os.path.join(self.temp_dir, "nested_folder")
        self.assertTrue(os.path.isdir(expected_path))

    @patch("ezcli_app.explorer.explorer_app.ExplorerApp.run")
    def test_create_file_choose_directory(self, mock_explorer_run):
        """Test choose-directory launches explorer to pick destination for file."""
        mock_explorer_run.return_value = self.temp_dir
        run_cli_create_file(name="script.py", choose_dest=True, console=self.console)
        expected_path = os.path.join(self.temp_dir, "script.py")
        self.assertTrue(os.path.isfile(expected_path))

    def test_privileged_helper_create_file(self):
        """Test helper_create_file creates a blank file securely."""
        target_path = os.path.join(self.temp_dir, "helper_file.conf")
        res = helper_create_file(target_path)
        self.assertTrue(res.get("success"))
        self.assertTrue(os.path.isfile(target_path))
        self.assertEqual(os.path.getsize(target_path), 0)

    @patch("ezcli_app.elevation.run_elevated_helper")
    def test_elevated_create_file(self, mock_helper):
        """Test elevated_create_file invokes run_elevated_helper."""
        mock_helper.return_value = (True, {"success": True}, "")
        ok = elevated_create_file("/etc/custom.conf", reason="Test file create", console=self.console)
        self.assertTrue(ok)
        mock_helper.assert_called_once_with(
            action="create_file",
            params={"path": "/etc/custom.conf"},
            reason="Test file create",
            task_description="Create file '/etc/custom.conf'",
            risk_level="high",
            skip_explanation=False,
            console=self.console,
        )

    def test_create_folder_multi_comma_separated(self):
        """Test creating multiple folders via comma-separated arguments."""
        run_cli_create_folder(
            raw_args=["proj_a,", "proj_b,", "proj_c"],
            dest_dir=self.temp_dir,
            console=self.console,
        )
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "proj_a")))
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "proj_b")))
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "proj_c")))
        output = self.console.export_text()
        self.assertIn("Created 3 folders successfully", output)

    def test_create_folder_multi_trailing_slashes(self):
        """Test creating multiple folders with trailing slashes."""
        run_cli_create_folder(
            raw_args=["assets/,", "components/"],
            dest_dir=self.temp_dir,
            console=self.console,
        )
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "assets")))
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "components")))
        output = self.console.export_text()
        self.assertIn("Created 2 folders successfully", output)

    def test_create_file_multi_comma_separated(self):
        """Test creating multiple blank files via comma-separated arguments."""
        run_cli_create_file(
            name="README.md, app.py, styles.css",
            dest_dir=self.temp_dir,
            console=self.console,
        )
        p1 = os.path.join(self.temp_dir, "README.md")
        p2 = os.path.join(self.temp_dir, "app.py")
        p3 = os.path.join(self.temp_dir, "styles.css")
        self.assertTrue(os.path.isfile(p1))
        self.assertTrue(os.path.isfile(p2))
        self.assertTrue(os.path.isfile(p3))
        self.assertEqual(os.path.getsize(p1), 0)
        self.assertEqual(os.path.getsize(p2), 0)
        self.assertEqual(os.path.getsize(p3), 0)
        output = self.console.export_text()
        self.assertIn("Created 3 blank files successfully", output)

    def test_create_folder_subfolder_path_rejected(self):
        """Test that subfolder paths are rejected in direct mode."""
        run_cli_create_folder(
            raw_args=["sub/my_dir/"],
            dest_dir=self.temp_dir,
            console=self.console,
        )
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "sub", "my_dir")))
        output = self.console.export_text()
        self.assertIn("Subfolder paths ('sub/my_dir/') are not permitted", output)

    def test_create_file_subfolder_path_rejected(self):
        """Test that subfolder paths for files are rejected in direct mode."""
        run_cli_create_file(
            raw_args=["sub/file.txt"],
            dest_dir=self.temp_dir,
            console=self.console,
        )
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "sub", "file.txt")))
        output = self.console.export_text()
        self.assertIn("Subfolder paths ('sub/file.txt') are not permitted", output)

    def test_create_multi_existing_item_blocks_all(self):
        """Test that if an item already exists, all creation is blocked (atomic)."""
        existing = os.path.join(self.temp_dir, "already_here.txt")
        with open(existing, "w") as f:
            f.write("data")
        new1 = os.path.join(self.temp_dir, "new1.txt")
        new2 = os.path.join(self.temp_dir, "new2.txt")

        run_cli_create_file(
            raw_args=["new1.txt,", "already_here.txt,", "new2.txt"],
            dest_dir=self.temp_dir,
            console=self.console,
        )
        self.assertFalse(os.path.exists(new1))
        self.assertFalse(os.path.exists(new2))
        output = self.console.export_text()
        self.assertIn("already exists", output)

    @patch("ezcli_app.explorer.explorer_app.ExplorerApp.run")
    def test_create_multi_with_choose_directory(self, mock_explorer_run):
        """Test creating multiple items with choose-directory destination."""
        mock_explorer_run.return_value = self.temp_dir
        run_cli_create_folder(
            raw_args=["mod1, mod2"],
            choose_dest=True,
            console=self.console,
        )
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "mod1")))
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "mod2")))


if __name__ == "__main__":
    unittest.main()

