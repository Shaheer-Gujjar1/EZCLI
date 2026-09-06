"""Unit tests for 'ez uninstall <name>' subcommand and privileged helper routines."""

import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.config import FEATURES_BY_SUBCOMMAND
from ezcli_app.elevation import elevated_package_uninstall
from ezcli_app.privileged_helper import (
    dispatch_helper_request,
    helper_package_uninstall,
)
from ezcli_app.uninstall_cli import run_cli_uninstall


class TestUninstallHelper(unittest.TestCase):
    """Test privileged helper routines for package uninstallation."""

    @patch("subprocess.run")
    def test_helper_package_uninstall_apt(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Removing curl ... done"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_package_uninstall("apt", "curl")
        self.assertTrue(res["success"])
        self.assertEqual(res["returncode"], 0)
        cmd_called = mock_run.call_args[0][0]
        self.assertIn("apt-get", cmd_called)
        self.assertIn("remove", cmd_called)
        self.assertIn("curl", cmd_called)

    @patch("subprocess.run")
    def test_helper_package_uninstall_apt_purge(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Purging configuration files for nginx ..."
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_package_uninstall("apt", "nginx", purge=True)
        self.assertTrue(res["success"])
        cmd_called = mock_run.call_args[0][0]
        self.assertIn("purge", cmd_called)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_helper_package_uninstall_snap(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/snap"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "vlc removed"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_package_uninstall("snap", "vlc")
        self.assertTrue(res["success"])
        cmd_called = mock_run.call_args[0][0]
        self.assertEqual(cmd_called, ["snap", "remove", "vlc"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_helper_package_uninstall_flatpak(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/flatpak"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Uninstall complete."
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_package_uninstall("flatpak", "org.videolan.VLC")
        self.assertTrue(res["success"])
        cmd_called = mock_run.call_args[0][0]
        self.assertEqual(cmd_called, ["flatpak", "-y", "uninstall", "org.videolan.VLC"])

    def test_helper_package_uninstall_edge_cases(self):
        # Empty package name
        res_empty = helper_package_uninstall("apt", "")
        self.assertFalse(res_empty["success"])
        self.assertIn("No package specified", res_empty["error"])

        # Unsupported platform
        res_unsupp = helper_package_uninstall("yum", "curl")
        self.assertFalse(res_unsupp["success"])
        self.assertIn("Unsupported", res_unsupp["error"])

        # Missing runtime
        with patch("shutil.which", return_value=None):
            res_no_fp = helper_package_uninstall("flatpak", "org.videolan.VLC")
            self.assertFalse(res_no_fp["success"])
            self.assertIn("Flatpak is not installed", res_no_fp["error"])

            res_no_snap = helper_package_uninstall("snap", "vlc")
            self.assertFalse(res_no_snap["success"])
            self.assertIn("Snap is not installed", res_no_snap["error"])

    def test_dispatch_package_uninstall(self):
        with patch("ezcli_app.privileged_helper.helper_package_uninstall") as mock_un:
            mock_un.return_value = {"success": True}
            res = dispatch_helper_request({
                "action": "package_uninstall",
                "params": {"platform": "apt", "package": "curl", "purge": False, "timeout": 300},
            })
            self.assertTrue(res["success"])
            mock_un.assert_called_once_with("apt", "curl", False, 300)

    @patch("ezcli_app.elevation.run_elevated_helper")
    def test_elevated_package_uninstall(self, mock_helper):
        mock_helper.return_value = (True, {"success": True, "returncode": 0}, "")
        ok, res, err = elevated_package_uninstall("apt", "nginx")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        mock_helper.assert_called_once()
        self.assertEqual(mock_helper.call_args[1]["action"], "package_uninstall")
        self.assertEqual(mock_helper.call_args[1]["params"]["package"], "nginx")


class TestUninstallCLI(unittest.TestCase):
    """Test CLI workflows, warning card rendering, and single consent flow."""

    def test_feature_registration(self):
        self.assertIn("uninstall", FEATURES_BY_SUBCOMMAND)
        feat = FEATURES_BY_SUBCOMMAND["uninstall"]
        self.assertEqual(feat.subcommand, "uninstall")
        self.assertEqual(feat.icon, "🗑️")
        self.assertIn("apt remove", feat.wrapped_commands)

    @patch("ezcli_app.uninstall_cli.collect_installed_packages")
    def test_run_cli_uninstall_not_found(self, mock_collect):
        mock_collect.return_value = {"matches": [], "total_count": 0}

        console = Console(record=True)
        run_cli_uninstall(app_name="nonexistentappxyz", console=console)
        out = console.export_text()

        self.assertIn("Application Not Found", out)
        self.assertIn("No installed application named 'nonexistentappxyz' was found", out)

    @patch("ezcli_app.uninstall_cli.collect_installed_packages")
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_run_cli_uninstall_user_declined(self, mock_confirm, mock_collect):
        mock_collect.return_value = {
            "matches": [
                {
                    "name": "vlc",
                    "app_id": "vlc",
                    "version": "3.0.20",
                    "size": "45 MB",
                    "platform": "apt",
                    "platform_name": "APT",
                    "platform_icon": "📦",
                    "description": "Multimedia player",
                }
            ]
        }

        console = Console(record=True)
        with patch("ezcli_app.uninstall_cli.elevated_package_uninstall") as mock_elev:
            run_cli_uninstall(app_name="vlc", console=console)
            mock_elev.assert_not_called()

        out = console.export_text()
        self.assertIn("Confirm Uninstallation: vlc", out)
        self.assertIn("Uninstallation of 'vlc' cancelled by user", out)

    @patch("ezcli_app.uninstall_cli.collect_installed_packages")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.uninstall_cli.elevated_package_uninstall")
    def test_run_cli_uninstall_success_single_source(self, mock_elev, mock_confirm, mock_collect):
        mock_collect.return_value = {
            "matches": [
                {
                    "name": "htop",
                    "app_id": "htop",
                    "version": "3.3.0",
                    "size": "2.5 MB",
                    "platform": "apt",
                    "platform_name": "APT",
                    "platform_icon": "📦",
                    "description": "Interactive process viewer",
                }
            ]
        }
        mock_elev.return_value = (True, {"success": True}, "")

        console = Console(record=True)
        run_cli_uninstall(app_name="htop", console=console)
        out = console.export_text()

        self.assertIn("Confirm Uninstallation: htop", out)
        self.assertIn("Successfully uninstalled 'htop' via APT", out)
        mock_elev.assert_called_once_with(
            platform="apt",
            package="htop",
            skip_explanation=True,
            console=console,
        )

    @patch("ezcli_app.uninstall_cli.collect_installed_packages")
    @patch("rich.prompt.Prompt.ask", return_value="2")
    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("ezcli_app.uninstall_cli.elevated_package_uninstall")
    def test_run_cli_uninstall_multi_source_selection(
        self, mock_elev, mock_confirm, mock_prompt, mock_collect
    ):
        mock_collect.return_value = {
            "matches": [
                {
                    "name": "vlc",
                    "app_id": "vlc",
                    "version": "3.0.20",
                    "size": "45 MB",
                    "platform": "apt",
                    "platform_name": "APT",
                    "platform_icon": "📦",
                    "description": "Multimedia player",
                },
                {
                    "name": "VLC",
                    "app_id": "org.videolan.VLC",
                    "version": "3.0.21",
                    "size": "120 MB",
                    "platform": "flatpak",
                    "platform_name": "Flatpak",
                    "platform_icon": "🟣",
                    "description": "VLC media player",
                },
            ]
        }
        mock_elev.return_value = (True, {"success": True}, "")

        console = Console(record=True)
        run_cli_uninstall(app_name="vlc", console=console)
        out = console.export_text()

        # User selected 2 -> Flatpak
        self.assertIn("Multiple matching installations were found", out)
        self.assertIn("Successfully uninstalled 'VLC' via Flatpak", out)
        mock_elev.assert_called_once_with(
            platform="flatpak",
            package="org.videolan.VLC",
            skip_explanation=True,
            console=console,
        )


if __name__ == "__main__":
    unittest.main()
