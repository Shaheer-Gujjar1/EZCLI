"""Unit tests for ez permissions & ownership engine."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.permissions.permissions_engine import (
    FilePermissions,
    apply_permissions,
    calculate_octal,
    calculate_symbolic,
    check_dangerous_permissions,
    get_file_permissions,
)


class TestPermissions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_file = os.path.join(self.temp_dir, "testfile.txt")
        with open(self.sample_file, "w") as f:
            f.write("hello world\n")
        os.chmod(self.sample_file, 0o644)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_octal(self):
        self.assertEqual(calculate_octal(True, True, True, True, False, True, True, False, True), "0755")
        self.assertEqual(calculate_octal(True, True, False, True, False, False, True, False, False), "0644")
        self.assertEqual(calculate_octal(True, True, True, True, True, True, True, True, True), "0777")
        self.assertEqual(calculate_octal(True, True, False, True, True, False, True, True, False), "0666")

    def test_calculate_symbolic(self):
        self.assertEqual(
            calculate_symbolic(False, True, True, True, True, False, True, True, False, True),
            "-rwxr-xr-x",
        )
        self.assertEqual(
            calculate_symbolic(True, True, True, True, True, False, True, True, False, True),
            "drwxr-xr-x",
        )
        self.assertEqual(
            calculate_symbolic(False, True, True, False, True, False, False, True, False, False),
            "-rw-r--r--",
        )

    def test_check_dangerous_permissions(self):
        # 0777 is dangerous
        is_dang, reason = check_dangerous_permissions(True, True, True, True, True, True, True, True, True)
        self.assertTrue(is_dang)
        self.assertIn("0777", reason)

        # 0666 is dangerous
        is_dang, reason = check_dangerous_permissions(True, True, False, True, True, False, True, True, False)
        self.assertTrue(is_dang)
        self.assertIn("0666", reason)

        # 0755 is safe
        is_dang, _ = check_dangerous_permissions(True, True, True, True, False, True, True, False, True)
        self.assertFalse(is_dang)

    def test_get_file_permissions(self):
        perms = get_file_permissions(self.sample_file)
        self.assertEqual(perms.octal, "0644")
        self.assertEqual(perms.symbolic, "-rw-r--r--")
        self.assertFalse(perms.is_dir)
        self.assertTrue(perms.owner_r)
        self.assertTrue(perms.owner_w)
        self.assertFalse(perms.owner_x)
        self.assertTrue(perms.group_r)
        self.assertFalse(perms.group_w)
        self.assertTrue(perms.other_r)
        self.assertFalse(perms.is_dangerous)

    def test_apply_permissions_unprivileged(self):
        ok, msg = apply_permissions(self.sample_file, "0755")
        self.assertTrue(ok)
        perms = get_file_permissions(self.sample_file)
        self.assertEqual(perms.octal, "0755")

    @patch("ezcli_app.permissions.permissions_engine.elevated_run_command")
    def test_apply_permissions_elevated_fallback(self, mock_elevated):
        mock_elevated.return_value = (True, "mode of /etc/shadow changed", "")
        with patch("os.chmod", side_effect=PermissionError("Permission denied")):
            ok, msg = apply_permissions("/etc/shadow", "0600")
            self.assertTrue(ok)
            mock_elevated.assert_called_once()
            self.assertIn("chmod", mock_elevated.call_args[1]["cmd"])


if __name__ == "__main__":
    unittest.main()
