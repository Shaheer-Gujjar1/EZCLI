"""Unit tests for 'ez update' and 'ez upgrade' privileged subcommands."""

import os
import subprocess
import unittest
from unittest.mock import MagicMock, mock_open, patch

from rich.console import Console

from ezcli_app.config import FEATURES_BY_SUBCOMMAND
from ezcli_app.privileged_helper import (
    dispatch_helper_request,
    helper_apt_simulate_upgrade,
    helper_apt_update,
    helper_apt_upgrade,
    helper_flatpak_update,
    helper_snap_refresh,
    helper_timeshift_snapshot,
)
from ezcli_app.upgrade_cli import (
    assess_upgrade_risk,
    check_flatpak_updates,
    check_snap_updates,
    run_cli_update,
    run_cli_upgrade,
)


class TestUpdateUpgradeHelper(unittest.TestCase):
    """Test privileged helper routines for package management."""

    @patch("subprocess.run")
    def test_helper_apt_update_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "Hit:1 http://archive.ubuntu.com/ubuntu noble InRelease\n"
            "Get:2 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]\n"
            "W: Skipping acquire of configured file 'main/binary-i386/Packages'\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_apt_update()
        self.assertTrue(res["success"])
        self.assertEqual(res["repos_hit"], 1)
        self.assertEqual(res["repos_get"], 1)
        self.assertEqual(len(res["warnings"]), 1)
        self.assertIn("Skipping acquire", res["warnings"][0])

    @patch("subprocess.run")
    def test_helper_apt_simulate_upgrade(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "The following packages will be upgraded:\n"
            "  curl libssl3\n"
            "The following NEW packages will be installed:\n"
            "  libssl-common\n"
            "The following packages have been kept back:\n"
            "  linux-image-generic\n"
            "2 upgraded, 1 newly installed, 0 to remove and 1 not upgraded.\n"
            "Need to get 14.5 MB of archives.\n"
            "After this operation, 1,200 kB of additional disk space will be used.\n"
        )
        mock_run.return_value = mock_proc

        res = helper_apt_simulate_upgrade()
        self.assertTrue(res["success"])
        self.assertEqual(res["upgraded_packages"], ["curl", "libssl3"])
        self.assertEqual(res["new_packages"], ["libssl-common"])
        self.assertEqual(res["kept_back_packages"], ["linux-image-generic"])
        self.assertEqual(res["download_size"], "14.5 MB")
        self.assertIn("additional disk space", res["disk_delta"])

    @patch("subprocess.run")
    def test_helper_apt_upgrade_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Processing triggers for libc-bin..."
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_apt_upgrade()
        self.assertTrue(res["success"])
        self.assertEqual(res["returncode"], 0)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_helper_snap_and_flatpak(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/snap"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "All snaps up to date."
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res_snap = helper_snap_refresh()
        self.assertTrue(res_snap["success"])

        mock_which.return_value = "/usr/bin/flatpak"
        res_fp = helper_flatpak_update()
        self.assertTrue(res_fp["success"])

    @patch("shutil.which")
    def test_helper_snap_and_flatpak_missing(self, mock_which):
        mock_which.return_value = None
        res_snap = helper_snap_refresh()
        self.assertTrue(res_snap["success"])
        self.assertTrue(res_snap.get("skipped", False))

        res_fp = helper_flatpak_update()
        self.assertTrue(res_fp["success"])
        self.assertTrue(res_fp.get("skipped", False))

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_helper_timeshift(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/timeshift"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Tagged snapshot '2026-09-06_00-00-00': ok"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = helper_timeshift_snapshot("Test snapshot")
        self.assertTrue(res["success"])

    def test_dispatch_helper_actions(self):
        with patch("ezcli_app.privileged_helper.helper_apt_update") as mock_up:
            mock_up.return_value = {"success": True}
            res = dispatch_helper_request({"action": "apt_update", "params": {}})
            self.assertTrue(res["success"])

        with patch("ezcli_app.privileged_helper.helper_apt_simulate_upgrade") as mock_sim:
            mock_sim.return_value = {"success": True}
            res = dispatch_helper_request({"action": "apt_simulate_upgrade", "params": {}})
            self.assertTrue(res["success"])


class TestUpdateUpgradeCLI(unittest.TestCase):
    """Test CLI workflows, rendering, and risk assessment."""

    def test_feature_registration(self):
        self.assertIn("update", FEATURES_BY_SUBCOMMAND)
        self.assertIn("upgrade", FEATURES_BY_SUBCOMMAND)
        self.assertIn("available-updates", FEATURES_BY_SUBCOMMAND)

        feat_update = FEATURES_BY_SUBCOMMAND["update"]
        self.assertEqual(feat_update.subcommand, "update")
        self.assertEqual(feat_update.icon, "🔄")

        feat_upgrade = FEATURES_BY_SUBCOMMAND["upgrade"]
        self.assertEqual(feat_upgrade.subcommand, "upgrade")
        self.assertEqual(feat_upgrade.icon, "⬆️")

    def test_assess_upgrade_risk(self):
        # Medium risk for regular packages
        level, reason = assess_upgrade_risk(["curl", "git"], "10 MB", [])
        self.assertEqual(level, "medium")

        # High risk for kernel
        level, reason = assess_upgrade_risk(["linux-image-generic"], "80 MB", [])
        self.assertEqual(level, "high")
        self.assertIn("Core system component", reason)

        # High risk for high volume
        level, reason = assess_upgrade_risk([f"pkg{i}" for i in range(50)], "200 MB", [])
        self.assertEqual(level, "high")
        self.assertIn("Large package volume", reason)

    @patch("ezcli_app.upgrade_cli.is_root", return_value=False)
    @patch("ezcli_app.upgrade_cli.explain_elevation", return_value=False)
    def test_run_cli_update_declined(self, mock_explain, mock_root):
        console = Console(record=True)
        run_cli_update(console=console)
        out = console.export_text()
        self.assertIn("cancelled", out.lower())

    @patch("ezcli_app.upgrade_cli.is_root", return_value=True)
    @patch("ezcli_app.upgrade_cli.elevated_apt_update")
    @patch("ezcli_app.upgrade_cli.collect_available_updates")
    def test_run_cli_update_success(self, mock_updates, mock_apt_up, mock_root):
        mock_apt_up.return_value = (True, {
            "success": True,
            "repos_hit": 5,
            "repos_get": 2,
            "warnings": ["Skipping acquire of main/binary-i386"],
        }, "")
        mock_updates.return_value = {"count": 3, "packages": []}

        console = Console(record=True)
        run_cli_update(console=console)
        out = console.export_text()

        self.assertIn("Software catalog refreshed successfully", out)
        self.assertIn("3 package(s) can be upgraded", out)
        self.assertIn("This was only an information refresh — nothing was installed", out)
        self.assertIn("You do not need to run this repeatedly", out)
        self.assertIn("Repository Notices", out)

    @patch("ezcli_app.upgrade_cli.is_root", return_value=True)
    @patch("ezcli_app.upgrade_cli.elevated_apt_update")
    @patch("ezcli_app.upgrade_cli.elevated_apt_simulate_upgrade")
    @patch("ezcli_app.upgrade_cli.check_flatpak_updates", return_value=[])
    @patch("ezcli_app.upgrade_cli.check_snap_updates", return_value=[])
    def test_run_cli_upgrade_no_updates(self, mock_snap, mock_fp, mock_sim, mock_up, mock_root):
        mock_up.return_value = (True, {"success": True}, "")
        mock_sim.return_value = (True, {
            "success": True,
            "upgraded_packages": [],
            "new_packages": [],
            "kept_back_packages": [],
            "download_size": "",
            "disk_delta": "",
        }, "")

        console = Console(record=True)
        run_cli_upgrade(console=console)
        out = console.export_text()

        self.assertIn("completely up to date", out)
        self.assertIn("Done. Run this only when you choose to — there is no daily obligation", out)

    @patch("ezcli_app.upgrade_cli.is_root", return_value=True)
    @patch("ezcli_app.upgrade_cli.elevated_apt_update")
    @patch("ezcli_app.upgrade_cli.elevated_apt_simulate_upgrade")
    @patch("ezcli_app.upgrade_cli.check_flatpak_updates", return_value=[])
    @patch("ezcli_app.upgrade_cli.check_snap_updates", return_value=[])
    @patch("rich.prompt.Confirm.ask", return_value=False)
    def test_run_cli_upgrade_user_cancels(self, mock_confirm, mock_snap, mock_fp, mock_sim, mock_up, mock_root):
        mock_up.return_value = (True, {"success": True}, "")
        mock_sim.return_value = (True, {
            "success": True,
            "upgraded_packages": ["curl", "git"],
            "new_packages": [],
            "kept_back_packages": ["linux-image-generic"],
            "download_size": "25 MB",
            "disk_delta": "5 MB will be used",
        }, "")

        console = Console(record=True)
        run_cli_upgrade(console=console)
        out = console.export_text()

        self.assertIn("Upgrade Impact Preview", out)
        self.assertIn("kept back", out.lower())
        self.assertIn("Upgrade cancelled by user", out)

    @patch("ezcli_app.upgrade_cli.is_root", return_value=True)
    @patch("ezcli_app.upgrade_cli.elevated_apt_update")
    @patch("ezcli_app.upgrade_cli.elevated_apt_simulate_upgrade")
    @patch("ezcli_app.upgrade_cli.elevated_apt_upgrade")
    @patch("ezcli_app.upgrade_cli.check_flatpak_updates", return_value=["org.mozilla.firefox"])
    @patch("ezcli_app.upgrade_cli.elevated_flatpak_update")
    @patch("ezcli_app.upgrade_cli.check_snap_updates", return_value=[])
    @patch("rich.prompt.Confirm.ask", return_value=True)
    @patch("os.path.exists")
    def test_run_cli_upgrade_full_flow(
        self,
        mock_exists,
        mock_confirm,
        mock_snap,
        mock_fp_up,
        mock_fp_list,
        mock_apt_up,
        mock_sim,
        mock_update,
        mock_root,
    ):
        mock_update.return_value = (True, {"success": True}, "")
        mock_sim.return_value = (True, {
            "success": True,
            "upgraded_packages": ["curl"],
            "new_packages": [],
            "kept_back_packages": [],
            "download_size": "2 MB",
            "disk_delta": "",
        }, "")
        mock_apt_up.return_value = (True, {"success": True}, "")
        mock_fp_up.return_value = (True, {"success": True}, "")

        # Simulate reboot required
        mock_exists.side_effect = lambda p: p == "/var/run/reboot-required"

        console = Console(record=True)
        run_cli_upgrade(console=console)
        out = console.export_text()

        self.assertIn("Upgrade Complete", out)
        self.assertIn("System Restart Recommended", out)
        self.assertIn("Done. Run this only when you choose to — there is no daily obligation", out)


if __name__ == "__main__":
    unittest.main()
