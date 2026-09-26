"""Unit tests for ez shortcuts engine and shell configuration."""

import os
import shutil
import tempfile
import unittest

from ezcli_app.shortcuts.shortcuts_engine import (
    ShortcutItem,
    add_or_update_shortcut,
    delete_shortcut,
    ensure_backup_created,
    parse_shortcuts,
    validate_shortcut_name,
)


class TestShortcuts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.rc_file = os.path.join(self.temp_dir, ".bashrc")
        with open(self.rc_file, "w", encoding="utf-8") as f:
            f.write("# ~/.bashrc sample\nexport PATH=$PATH:/usr/local/bin\nalias ll='ls -la'\n")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_shortcut_name(self):
        ok, msg = validate_shortcut_name("c")
        self.assertTrue(ok)

        ok, msg = validate_shortcut_name("update-all")
        self.assertTrue(ok)

        ok, msg = validate_shortcut_name("my_app")
        self.assertTrue(ok)

        ok, msg = validate_shortcut_name("")
        self.assertFalse(ok)

        ok, msg = validate_shortcut_name("bad name with space")
        self.assertFalse(ok)

        # Built-in shadow protection
        ok, msg = validate_shortcut_name("cd")
        self.assertFalse(ok)
        self.assertIn("built-in", msg)

    def test_ensure_backup_created(self):
        self.assertTrue(ensure_backup_created(self.rc_file))
        backup_file = f"{self.rc_file}.ezcli.bak"
        self.assertTrue(os.path.exists(backup_file))

    def test_parse_shortcuts(self):
        shortcuts = parse_shortcuts(self.rc_file)
        self.assertEqual(len(shortcuts), 1)
        self.assertEqual(shortcuts[0].name, "ll")
        self.assertEqual(shortcuts[0].command, "ls -la")

    def test_add_and_update_shortcut(self):
        ok, msg = add_or_update_shortcut(self.rc_file, "c", "clear")
        self.assertTrue(ok)

        shortcuts = parse_shortcuts(self.rc_file)
        names = [s.name for s in shortcuts]
        self.assertIn("c", names)
        self.assertIn("ll", names)

        # Update existing
        ok, msg = add_or_update_shortcut(self.rc_file, "c", "clear && ls")
        self.assertTrue(ok)

        updated_shortcuts = parse_shortcuts(self.rc_file)
        c_item = next(s for s in updated_shortcuts if s.name == "c")
        self.assertEqual(c_item.command, "clear && ls")

    def test_delete_shortcut(self):
        add_or_update_shortcut(self.rc_file, "quick-test", "echo 'testing'")
        self.assertIn("quick-test", [s.name for s in parse_shortcuts(self.rc_file)])

        ok, msg = delete_shortcut(self.rc_file, "quick-test")
        self.assertTrue(ok)
        self.assertNotIn("quick-test", [s.name for s in parse_shortcuts(self.rc_file)])

    def test_user_facing_no_alias_terminology(self):
        # Verify that error messages and labels in shortcuts_engine never use the forbidden word
        _, msg1 = validate_shortcut_name("cd")
        self.assertNotIn("alias", msg1.lower())

        _, msg2 = validate_shortcut_name("invalid name")
        self.assertNotIn("alias", msg2.lower())


if __name__ == "__main__":
    unittest.main()
