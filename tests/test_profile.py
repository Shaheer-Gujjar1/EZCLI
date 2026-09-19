"""Unit tests for ez profile data collection and password changing."""

import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.profile_cli import get_user_profile_data, render_user_profile_card


class TestProfile(unittest.TestCase):
    @patch("pwd.getpwnam")
    @patch("getpass.getuser")
    @patch("grp.getgrall")
    @patch("grp.getgrgid")
    def test_get_user_profile_data(self, mock_getgrgid, mock_getgrall, mock_getuser, mock_getpwnam):
        mock_getuser.return_value = "testuser"

        pw_record = MagicMock()
        pw_record.pw_name = "testuser"
        pw_record.pw_gecos = "Test User,Room 101,123,456"
        pw_record.pw_dir = "/home/testuser"
        pw_record.pw_shell = "/bin/bash"
        pw_record.pw_uid = 1000
        pw_record.pw_gid = 1000
        mock_getpwnam.return_value = pw_record

        g1 = MagicMock()
        g1.gr_name = "sudo"
        g1.gr_mem = ["testuser"]

        g2 = MagicMock()
        g2.gr_name = "docker"
        g2.gr_mem = ["testuser"]

        mock_getgrall.return_value = [g1, g2]

        primary_g = MagicMock()
        primary_g.gr_name = "testuser"
        mock_getgrgid.return_value = primary_g

        data = get_user_profile_data()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["full_name"], "Test User")
        self.assertEqual(data["home_dir"], "/home/testuser")
        self.assertEqual(data["shell"], "/bin/bash")
        self.assertIn("sudo", data["groups"])
        self.assertIn("docker", data["groups"])
        self.assertTrue(data["is_sudo"])

    def test_render_user_profile_card(self):
        console = Console(record=True, width=80)
        data = {
            "username": "alice",
            "full_name": "Alice Smith",
            "uid": 1001,
            "gid": 1001,
            "home_dir": "/home/alice",
            "shell": "/bin/zsh",
            "groups": ["alice", "sudo"],
            "is_sudo": True,
            "sudo_label": "Administrator (Sudo group)",
        }
        render_user_profile_card(data, console)
        out = console.export_text()
        self.assertIn("Alice Smith", out)
        self.assertIn("/home/alice", out)
        self.assertIn("/bin/zsh", out)
        self.assertIn("Administrator", out)

    @patch("ezcli_app.elevation.run_elevated_helper")
    def test_elevated_user_chpasswd(self, mock_helper):
        from ezcli_app.elevation import elevated_user_chpasswd
        mock_helper.return_value = (True, {"success": True}, "")
        ok, err = elevated_user_chpasswd("alice", "supersecret123456789!@#")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        mock_helper.assert_called_once()
        args, kwargs = mock_helper.call_args
        self.assertEqual(kwargs["action"], "user_chpasswd")
        self.assertEqual(kwargs["params"]["username"], "alice")
        self.assertEqual(kwargs["params"]["new_password"], "supersecret123456789!@#")


if __name__ == "__main__":
    unittest.main()
