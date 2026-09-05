"""Tests for EasyCLI shared privilege-elevation layer, simulated permission-denied scenarios, and automatic elevation."""

import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.elevation import (
    is_root,
    prompt_password_dots,
    wipe_password,
    explain_elevation,
    elevated_read_dir,
    elevated_run_command,
)
from ezcli_app.privileged_helper import (
    dispatch_helper_request,
    helper_file_copy,
    helper_file_delete,
    helper_file_move,
    helper_make_dir,
    helper_read_dir,
    helper_run_command,
)
from ezcli_app.collectors import collect_big_files, collect_logs
from ezcli_app.file_engine import is_destination_protected


class TestElevationBasics(unittest.TestCase):
    """Test basic functionality of the elevation module and helper."""

    def test_is_root(self):
        # Should return boolean without raising
        self.assertIsInstance(is_root(), bool)

    def test_prompt_password_non_interactive(self):
        # When sys.stdin is non-interactive / mocked
        with patch("sys.stdin", io.StringIO("secret_password\n")):
            pwd = prompt_password_dots("Password: ")
            self.assertEqual(pwd, "secret_password")

    def test_wipe_password(self):
        # Should execute safely
        wipe_password("some_secret")
        wipe_password(None)

    def test_helper_read_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "sample.txt")
            with open(test_file, "w") as f:
                f.write("hello")

            res = helper_read_dir(tmpdir)
            self.assertTrue(res.get("success"))
            entries = res.get("entries", [])
            names = [e["name"] for e in entries]
            self.assertIn("sample.txt", names)

    def test_helper_run_command_allowed(self):
        # du and cat are in the whitelist
        res = helper_run_command(["du", "-k", "--max-depth=0", "."])
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("returncode"), 0)

    def test_helper_run_command_forbidden(self):
        # Non-whitelisted command should be rejected defensively
        res = helper_run_command(["rm", "-rf", "/"])
        self.assertFalse(res.get("success"))
        self.assertIn("not permitted", res.get("error", "").lower())

    def test_helper_file_operations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "file_a.txt")
            dst = os.path.join(tmpdir, "file_b.txt")
            dst_move = os.path.join(tmpdir, "file_c.txt")

            with open(src, "w") as f:
                f.write("content")

            # Copy
            res_cp = helper_file_copy(src, dst)
            self.assertTrue(res_cp.get("success"))
            self.assertTrue(os.path.exists(dst))

            # Move
            res_mv = helper_file_move(dst, dst_move)
            self.assertTrue(res_mv.get("success"))
            self.assertFalse(os.path.exists(dst))
            self.assertTrue(os.path.exists(dst_move))

            # Delete
            res_del = helper_file_delete(dst_move)
            self.assertTrue(res_del.get("success"))
            self.assertFalse(os.path.exists(dst_move))

            # Make dir
            sub = os.path.join(tmpdir, "new_sub_dir")
            res_mkdir = helper_make_dir(sub)
            self.assertTrue(res_mkdir.get("success"))
            self.assertTrue(os.path.isdir(sub))

    def test_dispatch_helper_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            req = {"action": "make_dir", "params": {"path": os.path.join(tmpdir, "testdir")}}
            res = dispatch_helper_request(req)
            self.assertTrue(res.get("success"))

            req_unknown = {"action": "unsupported_action", "params": {}}
            res_unknown = dispatch_helper_request(req_unknown)
            self.assertFalse(res_unknown.get("success"))


class TestPermissionDeniedSimulations(unittest.TestCase):
    """Simulate partial and full permission-denied scenarios using restricted directories."""

    def setUp(self):
        self.test_root = tempfile.mkdtemp(prefix="ezcli_perm_test_")

    def tearDown(self):
        # Restore permissions so cleanup succeeds
        try:
            for root, dirs, files in os.walk(self.test_root):
                for d in dirs:
                    os.chmod(os.path.join(root, d), stat.S_IRWXU)
            os.chmod(self.test_root, stat.S_IRWXU)
            shutil.rmtree(self.test_root, ignore_errors=True)
        except Exception:
            pass

    def test_partial_permission_failure(self):
        """
        Scenario: Some data is accessible, but one subdirectory has permissions 0000.
        Expected: Available items are returned, plus partial_failure=True and inaccessible_paths noted.
        """
        # 1. Create accessible subdirectory with a file
        readable_dir = os.path.join(self.test_root, "accessible_folder")
        os.makedirs(readable_dir, exist_ok=True)
        sample_file = os.path.join(readable_dir, "data.txt")
        with open(sample_file, "w") as f:
            f.write("A" * 1024)

        # 2. Create restricted subdirectory with permissions 0000
        locked_dir = os.path.join(self.test_root, "locked_folder")
        os.makedirs(locked_dir, exist_ok=True)
        locked_file = os.path.join(locked_dir, "secret.txt")
        with open(locked_file, "w") as f:
            f.write("classified")
        os.chmod(locked_dir, 0o000)

        try:
            # Normal user scan
            result = collect_big_files(self.test_root, is_admin=False)
            self.assertTrue(result["exists"])
            self.assertTrue(len(result["items"]) >= 1)
            # Should detect partial failure due to locked_folder
            self.assertTrue(result["partial_failure"])
            self.assertTrue(len(result["inaccessible_paths"]) >= 1)
            self.assertFalse(result["full_failure"])
        finally:
            os.chmod(locked_dir, stat.S_IRWXU)

    def test_full_permission_failure(self):
        """
        Scenario: The target directory itself has permissions 0000.
        Expected: full_failure=True and 'Admin rights are required for this task.'
        """
        locked_root = os.path.join(self.test_root, "completely_locked")
        os.makedirs(locked_root, exist_ok=True)
        with open(os.path.join(locked_root, "inner.txt"), "w") as f:
            f.write("locked")
        os.chmod(locked_root, 0o000)

        try:
            result = collect_big_files(locked_root, is_admin=False)
            self.assertTrue(result["full_failure"])
            self.assertEqual(result["error"], "Admin rights are required for this task.")
            self.assertEqual(len(result["items"]), 0)
        finally:
            os.chmod(locked_root, stat.S_IRWXU)

    def test_is_destination_protected(self):
        """Test destination write protection detection."""
        # Current user's temp directory is writable
        self.assertFalse(is_destination_protected(self.test_root))

        # Restrict write permissions on a subfolder
        ro_dir = os.path.join(self.test_root, "readonly_dir")
        os.makedirs(ro_dir, exist_ok=True)
        os.chmod(ro_dir, 0o555)  # Read + Execute only (no write)

        try:
            target_sub = os.path.join(ro_dir, "sub")
            # If not root, writing to ro_dir is protected
            if not is_root():
                self.assertTrue(is_destination_protected(target_sub))
        finally:
            os.chmod(ro_dir, stat.S_IRWXU)


class TestAutomaticElevationCLI(unittest.TestCase):
    """Test that subcommands run cleanly and elevation is automatic with no --admin flag required."""

    def test_subcommands_run_without_flags(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ezcli_app.main", "system-info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("System Information", proc.stdout)

    def test_stats_run(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ezcli_app.main", "stats"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("System Resource Statistics", proc.stdout)

    def test_disk_info_run(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ezcli_app.main", "disk-info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Storage Partitions", proc.stdout)

    def test_help_has_no_admin_flag(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ezcli_app.main", "help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("--admin", proc.stdout)
        self.assertIn("Never run 'sudo ez'", proc.stdout)

    def test_big_files_choose_directory_dispatch(self):
        """Verify that 'ez big-files choose-directory' launches the explorer picker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "big_test.dat")
            with open(test_file, "wb") as f:
                f.write(b"0" * 1024)

            with patch("ezcli_app.main.check_textual_installed", return_value=True), \
                 patch("ezcli_app.explorer.explorer_app.ExplorerApp.run", return_value=tmpdir):
                from io import StringIO
                from rich.console import Console
                import ezcli_app.main as m

                with patch.object(sys, "argv", ["ez", "big-files", "choose-directory"]):
                    # Running main should call the picker and scan
                    with patch("ezcli_app.renderers.render_big_files") as mock_render:
                        m.main()
                        mock_render.assert_called_once()
                        # Verified that chosen directory from picker was passed to renderer
                        self.assertEqual(mock_render.call_args[0][1], tmpdir)

    def test_user_not_in_sudoers(self):
        """Verify that when a user is not in the sudoers file, a friendly English error is returned."""
        from ezcli_app.elevation import run_elevated_helper

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (
            "",
            "user is not in the sudoers file. This incident will be reported.\n",
        )

        with patch("ezcli_app.elevation.is_root", return_value=False), \
             patch("ezcli_app.elevation.prompt_password_dots", return_value="dummy_pass"), \
             patch("subprocess.Popen", return_value=mock_proc):

            success, data, err = run_elevated_helper(
                "read_dir",
                {"path": "/root"},
                skip_explanation=True,
            )
            self.assertFalse(success)
            self.assertEqual(err, "Your account does not have admin rights on this machine.")
            # Verify no retry occurred
            self.assertEqual(mock_proc.communicate.call_count, 1)

    def test_password_hygiene_and_timeout(self):
        """Verify that password is wiped and exceptions do not leak sensitive inputs or passwords."""
        from ezcli_app.elevation import run_elevated_helper

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd=["sudo"], timeout=30)

        with patch("ezcli_app.elevation.is_root", return_value=False), \
             patch("ezcli_app.elevation.prompt_password_dots", return_value="secret_super_pwd"), \
             patch("ezcli_app.elevation.wipe_password") as mock_wipe, \
             patch("subprocess.Popen", return_value=mock_proc):

            success, data, err = run_elevated_helper(
                "read_dir",
                {"path": "/root"},
                skip_explanation=True,
            )
            self.assertFalse(success)
            self.assertIn("timed out", err.lower())
            self.assertNotIn("secret_super_pwd", err)
            # Ensure wipe_password was called
            mock_wipe.assert_called()

    def test_elevation_session_context(self):
        """Verify ElevationSession sets and cleans up active session password."""
        from ezcli_app.elevation import ElevationSession, _ACTIVE_SESSION_PASSWORD
        import ezcli_app.elevation as elev

        session = ElevationSession("temp_pass")
        self.assertIsNone(elev._ACTIVE_SESSION_PASSWORD)
        with session:
            self.assertEqual(elev._ACTIVE_SESSION_PASSWORD, "temp_pass")
        self.assertIsNone(elev._ACTIVE_SESSION_PASSWORD)

    @patch("ezcli_app.elevation.is_root", return_value=False)
    @patch("ezcli_app.elevation.prompt_password_dots", return_value="correct_pass")
    @patch("subprocess.run")
    def test_authenticate_elevation_session_success(self, mock_sub, mock_prompt, mock_root):
        from ezcli_app.elevation import authenticate_elevation_session
        def fake_run(cmd, *args, **kwargs):
            if cmd == ["sudo", "-n", "true"]:
                return MagicMock(returncode=1)
            return MagicMock(returncode=0)
        mock_sub.side_effect = fake_run

        session = authenticate_elevation_session(skip_explanation=True)
        self.assertIsNotNone(session)
        self.assertEqual(session.password, "correct_pass")

    @patch("ezcli_app.elevation.is_root", return_value=False)
    @patch("subprocess.run")
    def test_authenticate_elevation_session_passwordless(self, mock_sub, mock_root):
        from ezcli_app.elevation import authenticate_elevation_session
        def fake_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0)
        mock_sub.side_effect = fake_run

        session = authenticate_elevation_session(skip_explanation=True)
        self.assertIsNotNone(session)
        self.assertEqual(session.password, "")

    @patch("ezcli_app.elevation.is_root", return_value=False)
    @patch("ezcli_app.elevation.prompt_password_dots", return_value="wrong_pass")
    @patch("subprocess.run")
    def test_authenticate_elevation_session_wrong_password_retry(self, mock_sub, mock_prompt, mock_root):
        from ezcli_app.elevation import authenticate_elevation_session
        def fake_run(cmd, *args, **kwargs):
            if cmd == ["sudo", "-n", "true"] or cmd == ["sudo", "-S", "-p", "", "true"]:
                return MagicMock(returncode=1, stderr="incorrect password")
            return MagicMock(returncode=0)
        mock_sub.side_effect = fake_run

        session = authenticate_elevation_session(skip_explanation=True)
        self.assertIsNone(session)
        self.assertEqual(mock_prompt.call_count, 3)

    @patch("ezcli_app.elevation.is_root", return_value=False)
    @patch("ezcli_app.elevation.prompt_password_dots", return_value=None)
    def test_authenticate_elevation_session_cancelled(self, mock_prompt, mock_root):
        from ezcli_app.elevation import authenticate_elevation_session
        session = authenticate_elevation_session(skip_explanation=True)
        self.assertIsNone(session)

    def test_lock_freshness_check(self):
        """Verify is_directory_locked reports true on restricted folders and false on accessible ones."""
        from ezcli_app.explorer.explorer_app import is_directory_locked

        with tempfile.TemporaryDirectory() as tmpdir:
            accessible_dir = os.path.join(tmpdir, "accessible")
            os.makedirs(accessible_dir)
            self.assertFalse(is_directory_locked(accessible_dir))

            restricted_dir = os.path.join(tmpdir, "restricted")
            os.makedirs(restricted_dir)
            try:
                os.chmod(restricted_dir, 0o000)
                self.assertTrue(is_directory_locked(restricted_dir))
            finally:
                os.chmod(restricted_dir, 0o755)


if __name__ == "__main__":
    unittest.main()
