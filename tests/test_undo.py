"""Automated tests for undo engine (v0.2)."""

import os
import shutil
import tempfile
import unittest

from ezcli_app.file_engine import execute_file_operation
from ezcli_app.undo import (
    execute_undo,
    load_undo_history,
    peek_last_operation,
    pop_last_operation,
    save_undo_history,
)


class TestUndoEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="ezcli_test_undo_")
        self.src_dir = os.path.join(self.test_dir, "src")
        self.dst_dir = os.path.join(self.test_dir, "dst")
        os.makedirs(self.src_dir, exist_ok=True)
        os.makedirs(self.dst_dir, exist_ok=True)

        self.file1 = os.path.join(self.src_dir, "doc.txt")
        with open(self.file1, "w") as f:
            f.write("Important document")

        # Clear undo history before test
        self.original_history = load_undo_history()
        save_undo_history([])

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        # Restore original undo history
        save_undo_history(self.original_history)

    def test_undo_move(self):
        # 1. Move file
        success, msg, executed = execute_file_operation("move", [self.file1], self.dst_dir)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(self.file1))
        dst_file = os.path.join(self.dst_dir, "doc.txt")
        self.assertTrue(os.path.exists(dst_file))

        # 2. Inspect last operation
        last_op = peek_last_operation()
        self.assertIsNotNone(last_op)
        self.assertEqual(last_op["action"], "move")

        # 3. Execute undo
        u_success, u_msg, reverted = execute_undo(last_op)
        self.assertTrue(u_success)

        # 4. Verify file is back in source location
        self.assertTrue(os.path.exists(self.file1))
        self.assertFalse(os.path.exists(dst_file))

    def test_undo_copy(self):
        # Pre-existing file at destination that should NOT be deleted by undo
        dst_pre = os.path.join(self.dst_dir, "keep_me.txt")
        with open(dst_pre, "w") as f:
            f.write("I was already here!")

        # Copy new file
        success, msg, executed = execute_file_operation("copy", [self.file1], self.dst_dir)
        self.assertTrue(success)

        dst_file = os.path.join(self.dst_dir, "doc.txt")
        self.assertTrue(os.path.exists(dst_file))

        # Undo copy
        last_op = peek_last_operation()
        u_success, u_msg, reverted = execute_undo(last_op)
        self.assertTrue(u_success)

        # Newly copied file must be deleted
        self.assertFalse(os.path.exists(dst_file))
        # Original file in source must still exist
        self.assertTrue(os.path.exists(self.file1))
        # Pre-existing file at destination must NOT be deleted
        self.assertTrue(os.path.exists(dst_pre))

    def test_redo_move(self):
        from ezcli_app.undo import execute_redo
        # Move file
        success, msg, executed = execute_file_operation("move", [self.file1], self.dst_dir)
        self.assertTrue(success)
        last_op = peek_last_operation()

        # Undo
        u_success, u_msg, reverted = execute_undo(last_op)
        self.assertTrue(u_success)
        self.assertTrue(os.path.exists(self.file1))

        # Redo
        r_success, r_msg, reapplied = execute_redo(last_op)
        self.assertTrue(r_success)
        self.assertFalse(os.path.exists(self.file1))
        self.assertTrue(os.path.exists(os.path.join(self.dst_dir, "doc.txt")))

    def test_clipboard_lifecycle(self):
        from ezcli_app.undo import clear_clipboard, get_clipboard, set_clipboard
        set_clipboard("copy", [self.file1])
        clip = get_clipboard()
        self.assertIsNotNone(clip)
        self.assertEqual(clip["action"], "copy")
        self.assertIn(self.file1, clip["items"])

        clear_clipboard()
        self.assertIsNone(get_clipboard())


if __name__ == "__main__":
    unittest.main()
