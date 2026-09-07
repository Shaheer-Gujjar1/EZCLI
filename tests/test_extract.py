"""Unit tests for EasyCLI extract-here and extract features."""

import os
import shutil
import tarfile
import tempfile
import unittest
import zipfile
from typing import Any, cast
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.extract_cli import (
    parse_extract_cli_args,
    render_extraction_success_card,
    run_cli_extract,
    run_cli_extract_here,
)
from ezcli_app.extract_engine import (
    extract_archive,
    get_archive_format,
    inspect_archive,
    sanitize_member_path,
    validate_extract_target,
)


class TestExtract(unittest.TestCase):
    """Test suite for extraction engine and CLI workflows."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dest_dir = os.path.join(self.temp_dir, "extracted_output")
        os.makedirs(self.dest_dir, exist_ok=True)
        self.console = Console(record=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_zip(self, filename: str = "sample.zip") -> str:
        zip_path = os.path.join(self.temp_dir, filename)
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "Hello World!")
            zf.writestr("nested/file.txt", "Nested content inside folder")
        return zip_path

    def _create_sample_tar(self, filename: str = "sample.tar.gz", mode: str = "w:gz") -> str:
        tar_path = os.path.join(self.temp_dir, filename)
        src_file = os.path.join(self.temp_dir, "_temp_src.txt")
        with open(src_file, "w") as f:
            f.write("Tarball payload content")

        with tarfile.open(tar_path, cast(Any, mode)) as tf:
            tf.add(src_file, arcname="document.txt")

        os.remove(src_file)
        return tar_path

    def test_get_archive_format(self):
        """Test archive format resolution from file paths."""
        self.assertEqual(get_archive_format("archive.zip"), ".zip")
        self.assertEqual(get_archive_format("/path/to/archive.tar.gz"), ".tar.gz")
        self.assertEqual(get_archive_format("bundle.tgz"), ".tgz")
        self.assertEqual(get_archive_format("archive.tar.xz"), ".tar.xz")
        self.assertEqual(get_archive_format("archive.txz"), ".txz")
        self.assertEqual(get_archive_format("archive.tar.bz2"), ".tar.bz2")
        self.assertEqual(get_archive_format("archive.tbz2"), ".tbz2")
        self.assertEqual(get_archive_format("archive.tar"), ".tar")
        self.assertEqual(get_archive_format("archive.7z"), ".7z")
        self.assertIsNone(get_archive_format("document.pdf"))
        self.assertIsNone(get_archive_format("folder/"))

    def test_validate_extract_target_valid(self):
        """Test validation of valid archive in current directory."""
        zip_path = self._create_sample_zip("valid.zip")
        is_valid, err, abs_p = validate_extract_target("valid.zip", cwd=self.temp_dir)
        self.assertTrue(is_valid)
        self.assertEqual(err, "")
        self.assertEqual(abs_p, zip_path)

    def test_validate_extract_target_subfolder_rejected(self):
        """Test that subfolder paths are rejected for direct extract-here."""
        sub_dir = os.path.join(self.temp_dir, "sub")
        os.makedirs(sub_dir, exist_ok=True)
        is_valid, err, _ = validate_extract_target("sub/valid.zip", cwd=self.temp_dir)
        self.assertFalse(is_valid)
        self.assertIn("Direct extraction ('ez extract-here') is restricted", err)
        self.assertIn("ez extract choose-directory", err)

    def test_validate_extract_target_not_found(self):
        """Test error when archive does not exist."""
        is_valid, err, _ = validate_extract_target("missing.zip", cwd=self.temp_dir)
        self.assertFalse(is_valid)
        self.assertIn("No such file in current directory", err)

    def test_validate_extract_target_directory_rejected(self):
        """Test that a directory is rejected as an archive target."""
        folder = os.path.join(self.temp_dir, "my_folder")
        os.makedirs(folder, exist_ok=True)
        is_valid, err, _ = validate_extract_target("my_folder", cwd=self.temp_dir)
        self.assertFalse(is_valid)
        self.assertIn("is a directory, not an archive file", err)

    def test_sanitize_member_path_valid(self):
        """Test safe path sanitization."""
        safe_path = sanitize_member_path(self.dest_dir, "folder/file.txt")
        self.assertTrue(safe_path.startswith(os.path.abspath(self.dest_dir)))

    def test_sanitize_member_path_zip_slip_blocked(self):
        """Test that Zip-Slip directory traversal attempts raise ValueError."""
        with self.assertRaises(ValueError):
            sanitize_member_path(self.dest_dir, "../../etc/passwd")

        with self.assertRaises(ValueError):
            sanitize_member_path(self.dest_dir, "/etc/shadow")

    def test_inspect_archive_zip(self):
        """Test archive inspection without extraction."""
        zip_path = self._create_sample_zip("inspect.zip")
        info = inspect_archive(zip_path)
        self.assertEqual(info["format"], ".zip")
        self.assertEqual(info["file_count"], 2)
        self.assertGreater(info["total_bytes"], 0)

    def test_extract_zip_success(self):
        """Test successful extraction of ZIP archive."""
        zip_path = self._create_sample_zip("data.zip")
        progress_calls = []

        def on_prog(cur, tot, name, b_cur, b_tot):
            progress_calls.append((cur, tot, name))

        ok, msg, stats = extract_archive(
            archive_path=zip_path,
            dest_dir=self.dest_dir,
            progress_callback=on_prog,
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "nested", "file.txt")))
        with open(os.path.join(self.dest_dir, "hello.txt")) as f:
            self.assertEqual(f.read(), "Hello World!")
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(stats["file_count"], 2)

    def test_extract_tar_gz_success(self):
        """Test successful extraction of .tar.gz archive."""
        tar_path = self._create_sample_tar("data.tar.gz", mode="w:gz")
        ok, msg, stats = extract_archive(
            archive_path=tar_path,
            dest_dir=self.dest_dir,
        )
        self.assertTrue(ok)
        extracted_file = os.path.join(self.dest_dir, "document.txt")
        self.assertTrue(os.path.isfile(extracted_file))
        with open(extracted_file) as f:
            self.assertEqual(f.read(), "Tarball payload content")

    def test_extract_tar_xz_success(self):
        """Test successful extraction of .tar.xz archive."""
        tar_path = self._create_sample_tar("data.tar.xz", mode="w:xz")
        ok, msg, stats = extract_archive(
            archive_path=tar_path,
            dest_dir=self.dest_dir,
        )
        self.assertTrue(ok)
        extracted_file = os.path.join(self.dest_dir, "document.txt")
        self.assertTrue(os.path.isfile(extracted_file))

    def test_extract_tar_bz2_success(self):
        """Test successful extraction of .tar.bz2 archive."""
        tar_path = self._create_sample_tar("data.tar.bz2", mode="w:bz2")
        ok, msg, stats = extract_archive(
            archive_path=tar_path,
            dest_dir=self.dest_dir,
        )
        self.assertTrue(ok)
        extracted_file = os.path.join(self.dest_dir, "document.txt")
        self.assertTrue(os.path.isfile(extracted_file))

    def test_extract_tar_plain_success(self):
        """Test successful extraction of plain uncompressed .tar archive."""
        tar_path = self._create_sample_tar("data.tar", mode="w")
        ok, msg, stats = extract_archive(
            archive_path=tar_path,
            dest_dir=self.dest_dir,
        )
        self.assertTrue(ok)
        extracted_file = os.path.join(self.dest_dir, "document.txt")
        self.assertTrue(os.path.isfile(extracted_file))

    def test_run_cli_extract_here_success(self):
        """Test direct CLI extract-here into current working directory."""
        zip_path = self._create_sample_zip("current.zip")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract_here(raw_args=["current.zip"], console=self.console)
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.temp_dir, "hello.txt")))
        finally:
            os.chdir(orig_cwd)

    def test_run_cli_extract_here_multiple_comma_separated(self):
        """Test extracting multiple comma-separated archives in current directory."""
        self._create_sample_zip("pack1.zip")
        self._create_sample_tar("pack2.tar.gz")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract_here(
                raw_args=["pack1.zip,", "pack2.tar.gz"],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.temp_dir, "hello.txt")))
            self.assertTrue(os.path.isfile(os.path.join(self.temp_dir, "document.txt")))
        finally:
            os.chdir(orig_cwd)

    def test_run_cli_extract_subfolder_rejected_in_direct_mode(self):
        """Test that subfolder paths are rejected for extract-here."""
        sub = os.path.join(self.temp_dir, "nested_sub")
        os.makedirs(sub, exist_ok=True)
        self._create_sample_zip("inside.zip")
        shutil.move(os.path.join(self.temp_dir, "inside.zip"), os.path.join(sub, "inside.zip"))

        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract_here(raw_args=["nested_sub/inside.zip"], console=self.console)
            output = self.console.export_text()
            self.assertIn("Direct Extraction Restricted", output)
        finally:
            os.chdir(orig_cwd)

    @patch("ezcli_app.explorer.explorer_app.run_destination_picker")
    @patch("ezcli_app.explorer.explorer_app.run_extract_picker")
    def test_run_cli_extract_choose_directory_flow(self, mock_extract_picker, mock_dest_picker):
        """Test ez extract choose-directory two-stage visual flow."""
        zip_path = self._create_sample_zip("chosen.zip")
        mock_extract_picker.return_value = [zip_path]
        mock_dest_picker.return_value = self.dest_dir

        run_cli_extract(raw_args=["choose-directory"], choose_dest=True, console=self.console)
        output = self.console.export_text()
        self.assertIn("Archive(s) Extracted Successfully", output)
        self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))

    def test_render_extraction_success_card(self):
        """Test rendering of extraction summary card."""
        render_extraction_success_card(
            archives=["/tmp/test.zip"],
            dest_dir="/tmp/output",
            total_files=5,
            total_dirs=1,
            total_bytes=1024,
            elapsed_seconds=0.42,
            elevated=False,
            console=self.console,
        )
        output = self.console.export_text()
        self.assertIn("test.zip", output)
        self.assertIn("5 file(s)", output)
        self.assertIn("0.42s", output)


    def test_parse_extract_cli_args_various_formats(self):
        """Test parse_extract_cli_args across various syntax patterns."""
        # 1. Single archive to destination
        arcs, dest, is_to = parse_extract_cli_args(["archive.zip", "to", "/tmp/dest"])
        self.assertEqual(arcs, ["archive.zip"])
        self.assertEqual(dest, "/tmp/dest")
        self.assertTrue(is_to)

        # 2. Comma separated archives to destination
        arcs, dest, is_to = parse_extract_cli_args(["arc1.zip,", "arc2.tar.gz", "to", "/tmp/dest"])
        self.assertEqual(arcs, ["arc1.zip", "arc2.tar.gz"])
        self.assertEqual(dest, "/tmp/dest")
        self.assertTrue(is_to)

        # 3. Archives to choose-directory
        arcs, dest, is_to = parse_extract_cli_args(["arc.zip", "to", "choose-directory"])
        self.assertEqual(arcs, ["arc.zip"])
        self.assertEqual(dest, "choose-directory")
        self.assertTrue(is_to)

        # 4. 'to' without explicit destination
        arcs, dest, is_to = parse_extract_cli_args(["arc.zip", "to"])
        self.assertEqual(arcs, ["arc.zip"])
        self.assertIsNone(dest)
        self.assertTrue(is_to)

        # 5. Visual picker only
        arcs, dest, is_to = parse_extract_cli_args(["choose-directory"])
        self.assertEqual(arcs, [])
        self.assertEqual(dest, "choose-directory")
        self.assertFalse(is_to)

    def test_run_cli_extract_to_specific_destination(self):
        """Test ez extract <file> to <destination> with explicit destination path."""
        self._create_sample_zip("pack.zip")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack.zip", "to", self.dest_dir],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))
        finally:
            os.chdir(orig_cwd)

    def test_run_cli_extract_multiple_archives_to_destination(self):
        """Test ez extract <file1>, <file2> to <destination> with comma separation."""
        self._create_sample_zip("pack1.zip")
        self._create_sample_tar("pack2.tar.gz")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack1.zip,", "pack2.tar.gz", "to", self.dest_dir],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))
            self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "document.txt")))
        finally:
            os.chdir(orig_cwd)

    @patch("ezcli_app.explorer.explorer_app.run_destination_picker")
    def test_run_cli_extract_to_choose_directory(self, mock_dest_picker):
        """Test ez extract <file> to choose-directory launches destination mini explorer."""
        self._create_sample_zip("pack.zip")
        mock_dest_picker.return_value = self.dest_dir
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack.zip", "to", "choose-directory"],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))
            mock_dest_picker.assert_called_once()
        finally:
            os.chdir(orig_cwd)

    def test_run_cli_extract_to_creates_nonexistent_dest_dir(self):
        """Test ez extract creates destination directory if it does not exist yet."""
        self._create_sample_zip("pack.zip")
        nested_dest = os.path.join(self.dest_dir, "nested_folder", "deeper")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack.zip", "to", nested_dest],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isdir(nested_dest))
            self.assertTrue(os.path.isfile(os.path.join(nested_dest, "hello.txt")))
        finally:
            os.chdir(orig_cwd)

    @patch("sys.stdin.isatty", return_value=False)
    def test_run_cli_extract_to_without_dest_non_interactive(self, mock_isatty):
        """Test ez extract <file> to in non-interactive environment shows clear guidance."""
        self._create_sample_zip("pack.zip")
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack.zip", "to"],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Missing destination directory after 'to'", output)
        finally:
            os.chdir(orig_cwd)

    @patch("rich.prompt.Prompt.ask")
    @patch("sys.stdin.isatty", return_value=True)
    def test_run_cli_extract_to_interactive_prompt(self, mock_isatty, mock_prompt):
        """Test ez extract <file> to interactively prompts and uses entered destination."""
        self._create_sample_zip("pack.zip")
        mock_prompt.return_value = self.dest_dir
        orig_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            run_cli_extract(
                raw_args=["pack.zip", "to"],
                console=self.console,
            )
            output = self.console.export_text()
            self.assertIn("Archive(s) Extracted Successfully", output)
            self.assertTrue(os.path.isfile(os.path.join(self.dest_dir, "hello.txt")))
        finally:
            os.chdir(orig_cwd)


if __name__ == "__main__":
    unittest.main()
