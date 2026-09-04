"""Unit tests for EasyCLI Mini Editor ('ezcli edit-file')."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.edit_cli import (
    is_binary_file,
    validate_direct_edit_target,
    run_cli_edit_file,
)
from ezcli_app.privileged_helper import helper_file_write, helper_file_read


class TestMiniEditorValidation(unittest.TestCase):
    """Test validation rules for 'ezcli edit-file'."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.console = Console(record=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_choose_directory_accepted(self) -> None:
        is_valid, resolved, err = validate_direct_edit_target("", cwd=self.test_dir)
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "choose-directory")
        self.assertIsNone(err)

        is_valid, resolved, err = validate_direct_edit_target("choose-directory", cwd=self.test_dir)
        self.assertTrue(is_valid)
        self.assertEqual(resolved, "choose-directory")
        self.assertIsNone(err)

    def test_reject_subfolder_paths(self) -> None:
        """Direct file editing cannot target subdirectories or parent directories."""
        sub_dir = os.path.join(self.test_dir, "sub")
        os.makedirs(sub_dir)

        is_valid, _, err = validate_direct_edit_target("sub/file.txt", cwd=self.test_dir)
        self.assertFalse(is_valid)
        self.assertIn("restricted to files in your current directory", err or "")

        is_valid, _, err = validate_direct_edit_target("../outside.py", cwd=self.test_dir)
        self.assertFalse(is_valid)
        self.assertIn("restricted to files in your current directory", err or "")

        is_valid, _, err = validate_direct_edit_target("/etc/hosts", cwd=self.test_dir)
        self.assertFalse(is_valid)
        self.assertIn("restricted to files in your current directory", err or "")

    def test_reject_directory_target(self) -> None:
        """Cannot open a directory as a file."""
        sub_folder = os.path.join(self.test_dir, "my_folder")
        os.makedirs(sub_folder)

        is_valid, _, err = validate_direct_edit_target("my_folder", cwd=self.test_dir)
        self.assertFalse(is_valid)
        self.assertIn("it is a directory", err or "")

    def test_accept_valid_current_dir_file(self) -> None:
        """Files in the current directory are accepted."""
        test_file = os.path.join(self.test_dir, "notes.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        is_valid, resolved, err = validate_direct_edit_target("notes.txt", cwd=self.test_dir)
        self.assertTrue(is_valid)
        self.assertEqual(resolved, test_file)
        self.assertIsNone(err)

    def test_accept_new_file_target(self) -> None:
        """Non-existent files in current directory are accepted as new files."""
        expected_path = os.path.join(self.test_dir, "new_script.py")
        is_valid, resolved, err = validate_direct_edit_target("new_script.py", cwd=self.test_dir)
        self.assertTrue(is_valid)
        self.assertEqual(resolved, expected_path)
        self.assertIsNone(err)

    def test_reject_binary_file(self) -> None:
        """Binary files are rejected to prevent corruption."""
        bin_file = os.path.join(self.test_dir, "image.png")
        with open(bin_file, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

        is_valid, _, err = validate_direct_edit_target("image.png", cwd=self.test_dir)
        self.assertFalse(is_valid)
        self.assertIn("Cannot edit binary file", err or "")

    def test_binary_detection_heuristics(self) -> None:
        """is_binary_file properly identifies binary vs text files."""
        # Extension check
        self.assertTrue(is_binary_file("archive.zip"))
        self.assertTrue(is_binary_file("program.bin"))
        self.assertTrue(is_binary_file("photo.jpg"))

        # Text file
        txt_path = os.path.join(self.test_dir, "clean.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("Hello world!\nLine 2\n")
        self.assertFalse(is_binary_file(txt_path))

        # Text file with embedded null byte
        null_path = os.path.join(self.test_dir, "corrupt.txt")
        with open(null_path, "wb") as f:
            f.write(b"Hello\x00World")
        self.assertTrue(is_binary_file(null_path))


class TestPrivilegedHelperFileIO(unittest.TestCase):
    """Test privileged helper file read/write operations."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_helper_file_write_and_read(self) -> None:
        target_path = os.path.join(self.test_dir, "system.conf")
        content = "KEY=VALUE\nPORT=8080\n"

        write_res = helper_file_write(target_path, content)
        self.assertTrue(write_res["success"])
        self.assertTrue(os.path.exists(target_path))

        read_res = helper_file_read(target_path)
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["content"], content)


class TestCliEditDispatch(unittest.TestCase):
    """Test CLI dispatch and error handling in run_cli_edit_file."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.console = Console(record=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch("ezcli_app.edit_cli.run_mini_editor")
    def test_open_existing_file(self, mock_editor: MagicMock) -> None:
        test_file = os.path.join(self.test_dir, "config.ini")
        with open(test_file, "w") as f:
            f.write("[Settings]\ntheme = dark\n")

        with patch("os.getcwd", return_value=self.test_dir):
            class Args:
                target = "config.ini"

            run_cli_edit_file(Args(), console=self.console)
            mock_editor.assert_called_once()
            args, kwargs = mock_editor.call_args
            self.assertEqual(kwargs.get("file_path") or args[0], test_file)
            self.assertEqual(kwargs.get("initial_content"), "[Settings]\ntheme = dark\n")
            self.assertFalse(kwargs.get("is_new_file"))

    @patch("ezcli_app.edit_cli.run_mini_editor")
    def test_open_new_file(self, mock_editor: MagicMock) -> None:
        with patch("os.getcwd", return_value=self.test_dir):
            class Args:
                target = "script.py"

            run_cli_edit_file(Args(), console=self.console)
            mock_editor.assert_called_once()
            args, kwargs = mock_editor.call_args
            self.assertTrue(kwargs.get("is_new_file"))
            self.assertEqual(kwargs.get("initial_content"), "")

    @patch("ezcli_app.edit_cli.run_file_picker")
    @patch("ezcli_app.edit_cli.run_mini_editor")
    def test_picker_selection(self, mock_editor: MagicMock, mock_picker: MagicMock) -> None:
        chosen = os.path.join(self.test_dir, "chosen.txt")
        with open(chosen, "w") as f:
            f.write("from picker")
        mock_picker.return_value = chosen

        class Args:
            target = "choose-directory"

        run_cli_edit_file(Args(), console=self.console)
        mock_picker.assert_called_once()
        mock_editor.assert_called_once()
        args, kwargs = mock_editor.call_args
        self.assertEqual(kwargs.get("file_path") or args[0], chosen)
        self.assertEqual(kwargs.get("initial_content"), "from picker")

    @patch("ezcli_app.edit_cli.run_file_picker", return_value=None)
    @patch("ezcli_app.edit_cli.run_mini_editor")
    def test_picker_cancelled(self, mock_editor: MagicMock, mock_picker: MagicMock) -> None:
        class Args:
            target = "choose-directory"

        run_cli_edit_file(Args(), console=self.console)
        mock_picker.assert_called_once()
        mock_editor.assert_not_called()
        output = self.console.export_text()
        self.assertIn("File selection cancelled", output)

    @patch("ezcli_app.edit_cli.run_mini_editor")
    def test_subfolder_rejected(self, mock_editor: MagicMock) -> None:
        with patch("os.getcwd", return_value=self.test_dir):
            class Args:
                target = "sub/file.txt"

            run_cli_edit_file(Args(), console=self.console)
            mock_editor.assert_not_called()
            output = self.console.export_text()
            self.assertIn("Editing Restricted", output)

    @patch("ezcli_app.edit_cli.run_mini_editor")
    @patch("ezcli_app.edit_cli.elevated_file_read")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    def test_permission_denied_read_elevated(
        self, mock_ask: MagicMock, mock_elevated_read: MagicMock, mock_editor: MagicMock
    ) -> None:
        test_file = os.path.join(self.test_dir, "shadow.txt")
        with open(test_file, "w") as f:
            f.write("secret")
        mock_elevated_read.return_value = (True, "elevated secret content", "")

        with patch("os.getcwd", return_value=self.test_dir):
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                class Args:
                    target = "shadow.txt"

                run_cli_edit_file(Args(), console=self.console)
                mock_ask.assert_called_once()
                mock_elevated_read.assert_called_once()
                mock_editor.assert_called_once()
                _, kwargs = mock_editor.call_args
                self.assertEqual(kwargs.get("initial_content"), "elevated secret content")
                self.assertTrue(kwargs.get("is_admin"))

    @patch("ezcli_app.edit_cli.run_mini_editor")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_permission_denied_read_declined(self, mock_ask: MagicMock, mock_editor: MagicMock) -> None:
        test_file = os.path.join(self.test_dir, "shadow.txt")
        with open(test_file, "w") as f:
            f.write("secret")

        with patch("os.getcwd", return_value=self.test_dir):
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                class Args:
                    target = "shadow.txt"

                run_cli_edit_file(Args(), console=self.console)
                mock_ask.assert_called_once()
                mock_editor.assert_not_called()
                output = self.console.export_text()
                self.assertIn("Elevation cancelled", output)


class TestEditorAppLogic(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_language_detection(self) -> None:
        from ezcli_app.editor.editor_app import EditorApp

        app_py = EditorApp("file.py")
        self.assertEqual(app_py.detect_language(), "python")

        app_sh = EditorApp("script.sh")
        self.assertEqual(app_sh.detect_language(), "bash")

        app_txt = EditorApp("notes.txt")
        self.assertIsNone(app_txt.detect_language())

    def test_toggle_wrap(self) -> None:
        from ezcli_app.editor.editor_app import EditorApp

        app = EditorApp("file.txt")
        initial = app.soft_wrap_enabled
        mock_ta = MagicMock()
        mock_notify = MagicMock()
        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_ta)
        app.notify = mock_notify
        app.update_status_bar = mock_status
        app.action_toggle_wrap()
        self.assertEqual(app.soft_wrap_enabled, not initial)
        self.assertEqual(mock_ta.soft_wrap, not initial)


if __name__ == "__main__":
    unittest.main()
