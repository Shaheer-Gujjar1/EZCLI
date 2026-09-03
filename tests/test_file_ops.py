"""Automated tests for safe copy, move, and conflict operations (v0.2)."""

import os
import shutil
import tempfile
import unittest

from ezcli_app.file_engine import (
    compute_sha256,
    execute_file_operation,
    get_unique_destination_name,
    preview_file_operation,
)


class TestFileOperations(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ezcli_test_ops_")
        self.src_dir = os.path.join(self.test_dir, "src")
        self.dst_dir = os.path.join(self.test_dir, "dst")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dst_dir, exist_ok=True)

        # Create sample files
        self.file1 = os.path.join(self.src_dir, "hello.txt")
        with open(self.file1, "w") as f:
            f.write("Hello EasyCLI v0.2")

        self.sub_dir = os.path.join(self.src_dir, "sub")
        os.makedirs(self.sub_dir, exist_ok=True)
        self.file2 = os.path.join(self.sub_dir, "nested.txt")
        with open(self.file2, "w") as f:
            f.write("Nested file content")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_compute_sha256(self):
        chk = compute_sha256(self.file1)
        self.assertIsInstance(chk, str)
        self.assertEqual(len(chk), 64)

    def test_unique_destination_name(self):
        target = os.path.join(self.dst_dir, "sample.txt")
        with open(target, "w") as f:
            f.write("existing")

        new_name = get_unique_destination_name(target)
        self.assertEqual(os.path.basename(new_name), "sample (1).txt")

    def test_preview_operation(self):
        preview = preview_file_operation("copy", [self.file1, self.sub_dir], self.dst_dir)
        self.assertEqual(preview["count"], 2)
        self.assertGreater(preview["total_bytes"], 0)
        self.assertEqual(len(preview["collisions"]), 0)

    def test_copy_file_and_directory(self):
        success, msg, executed = execute_file_operation(
            action="copy",
            sources=[self.file1, self.sub_dir],
            destination=self.dst_dir,
            conflict_policy="overwrite",
        )
        self.assertTrue(success)
        self.assertEqual(len(executed), 2)

        copied_file = os.path.join(self.dst_dir, "hello.txt")
        self.assertTrue(os.path.exists(copied_file))
        with open(copied_file) as f:
            self.assertEqual(f.read(), "Hello EasyCLI v0.2")

        copied_sub = os.path.join(self.dst_dir, "sub", "nested.txt")
        self.assertTrue(os.path.exists(copied_sub))

    def test_conflict_skip(self):
        # Create colliding file at destination
        dst_hello = os.path.join(self.dst_dir, "hello.txt")
        with open(dst_hello, "w") as f:
            f.write("original destination content")

        success, msg, executed = execute_file_operation(
            action="copy",
            sources=[self.file1],
            destination=self.dst_dir,
            conflict_policy="skip",
        )
        self.assertTrue(success)
        # Should not have executed copy since it was skipped
        self.assertEqual(len(executed), 0)
        with open(dst_hello) as f:
            self.assertEqual(f.read(), "original destination content")

    def test_conflict_rename(self):
        dst_hello = os.path.join(self.dst_dir, "hello.txt")
        with open(dst_hello, "w") as f:
            f.write("original destination content")

        success, msg, executed = execute_file_operation(
            action="copy",
            sources=[self.file1],
            destination=self.dst_dir,
            conflict_policy="rename",
        )
        self.assertTrue(success)
        self.assertEqual(len(executed), 1)

        renamed_file = os.path.join(self.dst_dir, "hello (1).txt")
        self.assertTrue(os.path.exists(renamed_file))
        self.assertTrue(os.path.exists(dst_hello))

    def test_move_file(self):
        success, msg, executed = execute_file_operation(
            action="move",
            sources=[self.file1],
            destination=self.dst_dir,
        )
        self.assertTrue(success)
        # Source must be removed after move
        self.assertFalse(os.path.exists(self.file1))
        # Destination must exist
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "hello.txt")))


if __name__ == "__main__":
    unittest.main()
