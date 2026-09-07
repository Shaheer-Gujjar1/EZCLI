"""Automated tests for ez compress command (v0.5)."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile
import tarfile

from ezcli_app.compress_engine import (
    SUPPORTED_FORMATS,
    calculate_targets_summary,
    compress_targets,
    suggest_archive_name,
    validate_compress_target,
)
from ezcli_app.compress_cli import run_cli_compress, render_compression_success_card
from ezcli_app.compress_tui import prompt_format_cli, FORMAT_OPTIONS
from ezcli_app.file_engine import normalize_target_args
from rich.console import Console


class TestCompressEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ezcli_test_compress_")
        self.cwd_dir = os.path.join(self.test_dir, "cwd")
        os.makedirs(self.cwd_dir, exist_ok=True)

        # Create sample files & directory in cwd
        self.file1 = os.path.join(self.cwd_dir, "file1.txt")
        with open(self.file1, "w") as f:
            f.write("Hello EasyCLI Compress v0.5!\n" * 50)

        self.file2 = os.path.join(self.cwd_dir, "file2.json")
        with open(self.file2, "w") as f:
            f.write('{"status": "ok", "app": "ezcli"}\n' * 20)

        self.sub_dir = os.path.join(self.cwd_dir, "my_folder")
        os.makedirs(self.sub_dir, exist_ok=True)
        self.nested_file = os.path.join(self.sub_dir, "nested.md")
        with open(self.nested_file, "w") as f:
            f.write("# Nested Document\n" * 30)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_normalize_target_args(self):
        # Space-separated
        self.assertEqual(normalize_target_args(["a.txt", "b.txt"]), ["a.txt", "b.txt"])
        # Comma-separated with trailing commas
        self.assertEqual(
            normalize_target_args(["a.txt,", "b.txt,", "folder1/"]),
            ["a.txt", "b.txt", "folder1/"],
        )
        # Comma-separated single string
        self.assertEqual(normalize_target_args(["a.txt,b.txt"]), ["a.txt", "b.txt"])
        # Empty and whitespace
        self.assertEqual(normalize_target_args(["  ", "a.txt , b.txt "]), ["a.txt", "b.txt"])

    def test_validate_compress_target_valid_file(self):
        is_valid, msg, path, is_dir = validate_compress_target("file1.txt", cwd=self.cwd_dir)
        self.assertTrue(is_valid)
        self.assertEqual(path, self.file1)
        self.assertFalse(is_dir)

    def test_validate_compress_target_valid_folder(self):
        is_valid, msg, path, is_dir = validate_compress_target("my_folder/", cwd=self.cwd_dir)
        self.assertTrue(is_valid)
        self.assertEqual(path, self.sub_dir)
        self.assertTrue(is_dir)

    def test_validate_compress_target_file_with_trailing_slash_fails(self):
        is_valid, msg, path, is_dir = validate_compress_target("file1.txt/", cwd=self.cwd_dir)
        self.assertFalse(is_valid)
        self.assertIn("trailing slash", msg)

    def test_validate_compress_target_subfolder_rejected(self):
        # Subfolder paths directly targeted must be rejected
        is_valid, msg, path, is_dir = validate_compress_target("my_folder/nested.md", cwd=self.cwd_dir)
        self.assertFalse(is_valid)
        self.assertIn("Direct compress is restricted", msg)
        self.assertIn("ez compress choose-directory", msg)

    def test_validate_compress_target_parent_traversal_rejected(self):
        is_valid, msg, path, is_dir = validate_compress_target("../outside.txt", cwd=self.cwd_dir)
        self.assertFalse(is_valid)
        self.assertIn("Direct compress is restricted", msg)

    def test_validate_compress_target_nonexistent(self):
        is_valid, msg, path, is_dir = validate_compress_target("ghost.txt", cwd=self.cwd_dir)
        self.assertFalse(is_valid)
        self.assertIn("Cannot find", msg)

    def test_validate_compress_target_choose_directory(self):
        is_valid, msg, path, is_dir = validate_compress_target("choose-directory", cwd=self.cwd_dir)
        self.assertTrue(is_valid)
        self.assertEqual(path, "choose-directory")

    def test_suggest_archive_name(self):
        self.assertEqual(suggest_archive_name([self.file1], ".zip"), "file1.zip")
        self.assertEqual(suggest_archive_name([self.sub_dir], ".tar.gz"), "my_folder.tar.gz")
        self.assertEqual(suggest_archive_name([self.file1, self.file2], ".7z"), "archive.7z")
        self.assertEqual(suggest_archive_name([], ".tar.xz"), "archive.tar.xz")

    def test_calculate_targets_summary(self):
        summary = calculate_targets_summary([self.file1, self.sub_dir])
        self.assertGreater(summary["total_bytes"], 0)
        self.assertEqual(summary["file_count"], 2)  # file1 + nested.md
        self.assertGreaterEqual(summary["dir_count"], 1)  # my_folder

    def test_compress_zip(self):
        out_zip = os.path.join(self.test_dir, "test_archive.zip")
        progress_calls = []

        def on_prog(idx, tot, name, cur_b, tot_b):
            progress_calls.append((idx, name))

        ok, msg, stats = compress_targets(
            targets=[self.file1, self.sub_dir],
            output_path=out_zip,
            format_type=".zip",
            progress_callback=on_prog,
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_zip))
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(stats["format"], "ZIP Archive")
        self.assertGreater(stats["compressed_bytes"], 0)

        # Inspect zip archive contents
        with zipfile.ZipFile(out_zip, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("file1.txt", namelist)
            self.assertTrue(any("nested.md" in n for n in namelist))

    def test_compress_tar_gz(self):
        out_tar = os.path.join(self.test_dir, "test_archive.tar.gz")
        ok, msg, stats = compress_targets(
            targets=[self.file1, self.file2],
            output_path=out_tar,
            format_type=".tar.gz",
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_tar))
        with tarfile.open(out_tar, "r:gz") as tf:
            names = tf.getnames()
            self.assertIn("file1.txt", names)
            self.assertIn("file2.json", names)

    def test_compress_tar_xz(self):
        out_xz = os.path.join(self.test_dir, "test_archive.tar.xz")
        ok, msg, stats = compress_targets(
            targets=[self.file1],
            output_path=out_xz,
            format_type=".tar.xz",
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_xz))
        with tarfile.open(out_xz, "r:xz") as tf:
            self.assertIn("file1.txt", tf.getnames())

    def test_compress_tar_bz2(self):
        out_bz2 = os.path.join(self.test_dir, "test_archive.tar.bz2")
        ok, msg, stats = compress_targets(
            targets=[self.file2],
            output_path=out_bz2,
            format_type=".tar.bz2",
        )
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(out_bz2))
        with tarfile.open(out_bz2, "r:bz2") as tf:
            self.assertIn("file2.json", tf.getnames())

    @patch("shutil.which", return_value="/usr/bin/7z")
    @patch("subprocess.run")
    def test_compress_7z(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="Everything is Ok\n", stderr="")
        out_7z = os.path.join(self.test_dir, "test_archive.7z")
        # Touch output file to simulate 7z output
        with open(out_7z, "w") as f:
            f.write("7z_data")

        ok, msg, stats = compress_targets(
            targets=[self.file1],
            output_path=out_7z,
            format_type=".7z",
        )
        self.assertTrue(ok)
        self.assertEqual(stats["format"], "7-Zip Archive")

    @patch("shutil.which", return_value=None)
    def test_compress_7z_missing_binary(self, mock_which):
        out_7z = os.path.join(self.test_dir, "test_archive.7z")
        ok, msg, stats = compress_targets(
            targets=[self.file1],
            output_path=out_7z,
            format_type=".7z",
        )
        self.assertFalse(ok)
        self.assertIn("7-Zip is not installed", msg)

    def test_compress_invalid_format(self):
        out_rar = os.path.join(self.test_dir, "test.rar")
        ok, msg, stats = compress_targets([self.file1], out_rar, ".rar")
        self.assertFalse(ok)
        self.assertIn("Unsupported compression format", msg)


class TestCompressCLI(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ezcli_test_compress_cli_")
        self.orig_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create files
        with open("doc1.txt", "w") as f:
            f.write("Document 1 test")
        with open("doc2.txt", "w") as f:
            f.write("Document 2 test")

        self.console = Console(record=True)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("ezcli_app.compress_cli.run_format_selector")
    def test_run_cli_compress_direct_success(self, mock_selector):
        mock_selector.return_value = {"format": ".zip", "archive_name": "bundle.zip"}
        run_cli_compress(targets=["doc1.txt", "doc2.txt"], console=self.console)

        output = self.console.export_text()
        self.assertIn("Archive Created Successfully", output)
        self.assertTrue(os.path.exists("bundle.zip"))

    @patch("ezcli_app.compress_cli.run_format_selector")
    def test_run_cli_compress_comma_separated(self, mock_selector):
        mock_selector.return_value = {"format": ".zip", "archive_name": "comma_bundle.zip"}
        run_cli_compress(targets=["doc1.txt,", "doc2.txt"], console=self.console)

        output = self.console.export_text()
        self.assertIn("Archive Created Successfully", output)
        self.assertTrue(os.path.exists("comma_bundle.zip"))

    def test_run_cli_compress_subfolder_rejected(self):
        os.makedirs("sub", exist_ok=True)
        with open("sub/inner.txt", "w") as f:
            f.write("inner")

        run_cli_compress(targets=["sub/inner.txt"], console=self.console)
        output = self.console.export_text()
        self.assertIn("Direct Compress Restricted", output)
        self.assertIn("ez compress choose-directory", output)

    @patch("ezcli_app.compress_cli.run_format_selector")
    def test_run_cli_compress_user_cancelled(self, mock_selector):
        mock_selector.return_value = None
        run_cli_compress(targets=["doc1.txt"], console=self.console)
        output = self.console.export_text()
        self.assertIn("Compression cancelled", output)

    @patch("ezcli_app.compress_cli.Prompt.ask", return_value="c")
    @patch("ezcli_app.compress_cli.run_format_selector")
    def test_run_cli_compress_conflict_cancel(self, mock_selector, mock_ask):
        # Pre-create bundle.zip
        with open("bundle.zip", "w") as f:
            f.write("existing")

        mock_selector.return_value = {"format": ".zip", "archive_name": "bundle.zip"}
        run_cli_compress(targets=["doc1.txt"], console=self.console)
        output = self.console.export_text()
        self.assertIn("File already exists", output)
        self.assertIn("Compression cancelled", output)

    @patch("ezcli_app.compress_cli.Prompt.ask", return_value="r")
    @patch("ezcli_app.compress_cli.run_format_selector")
    def test_run_cli_compress_conflict_rename(self, mock_selector, mock_ask):
        with open("bundle.zip", "w") as f:
            f.write("existing")

        mock_selector.return_value = {"format": ".zip", "archive_name": "bundle.zip"}
        run_cli_compress(targets=["doc1.txt"], console=self.console)
        output = self.console.export_text()
        self.assertIn("Archive Created Successfully", output)
        self.assertTrue(os.path.exists("bundle (1).zip"))

    @patch("ezcli_app.compress_cli.run_format_selector")
    @patch("ezcli_app.explorer.explorer_app.run_compress_picker")
    def test_run_cli_compress_choose_directory(self, mock_picker, mock_selector):
        mock_picker.return_value = [os.path.abspath("doc1.txt")]
        mock_selector.return_value = {"format": ".zip", "archive_name": "picked.zip"}

        run_cli_compress(targets=["choose-directory"], console=self.console)
        output = self.console.export_text()
        self.assertIn("Archive Created Successfully", output)
        self.assertTrue(os.path.exists("picked.zip"))

    @patch("ezcli_app.compress_tui.Prompt.ask")
    def test_prompt_format_cli(self, mock_ask):
        mock_ask.side_effect = ["1", "my_backup.zip"]
        res = prompt_format_cli(["doc1.txt"], console=self.console)
        self.assertIsNotNone(res)
        assert res is not None
        self.assertEqual(res["format"], ".zip")
        self.assertEqual(res["archive_name"], "my_backup.zip")

    @patch("ezcli_app.compress_tui.Prompt.ask")
    def test_prompt_format_cli_cancel(self, mock_ask):
        mock_ask.return_value = "q"
        res = prompt_format_cli(["doc1.txt"], console=self.console)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
