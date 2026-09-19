"""Unit tests for ez fix-packages diagnostics and repairs."""

import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.fix_packages_cli import check_broken_packages


class TestFixPackages(unittest.TestCase):
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_clean_system(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/dpkg"

        # Mock dpkg --audit returning empty (clean)
        res_dpkg = MagicMock(returncode=0, stdout="", stderr="")
        # Mock apt-get --dry-run returning clean
        res_apt = MagicMock(returncode=0, stdout="0 upgraded, 0 newly installed, 0 to remove", stderr="")

        mock_run.side_effect = [res_dpkg, res_apt]

        with patch("os.path.isfile", return_value=False):
            diag = check_broken_packages()

        self.assertFalse(diag["is_broken"])
        self.assertEqual(diag["risk"], "NONE")
        self.assertEqual(diag["unconfigured"], [])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_unconfigured_packages_low_risk(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/dpkg"

        # Mock dpkg --audit showing unconfigured package
        audit_output = """The following packages are in a mess:
  libssl1.1:amd64       half-configured
"""
        res_dpkg = MagicMock(returncode=1, stdout=audit_output, stderr="")
        res_apt = MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = [res_dpkg, res_apt]

        with patch("os.path.isfile", return_value=False):
            diag = check_broken_packages()

        self.assertTrue(diag["is_broken"])
        self.assertEqual(diag["risk"], "LOW")
        self.assertIn("libssl1.1:amd64", diag["unconfigured"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_check_broken_with_removals_high_risk(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/dpkg"

        res_dpkg = MagicMock(returncode=0, stdout="", stderr="")
        apt_output = """Reading package lists...
Building dependency tree...
The following packages will be REMOVED:
  conflicting-pkg1
The following NEW packages will be installed:
  libnew1
0 upgraded, 1 newly installed, 1 to remove
"""
        res_apt = MagicMock(returncode=0, stdout=apt_output, stderr="")
        mock_run.side_effect = [res_dpkg, res_apt]

        with patch("os.path.isfile", return_value=False):
            diag = check_broken_packages()

        self.assertTrue(diag["is_broken"])
        self.assertEqual(diag["risk"], "HIGH")
        self.assertIn("conflicting-pkg1", diag["to_remove"])
        self.assertIn("libnew1", diag["to_install"])

    @patch("ezcli_app.elevation.run_elevated_helper")
    def test_elevated_fix_packages(self, mock_helper):
        from ezcli_app.elevation import elevated_fix_packages
        mock_helper.return_value = (True, {"success": True, "log": "Repaired successfully"}, "")
        ok, log, err = elevated_fix_packages()
        self.assertTrue(ok)
        self.assertEqual(log, "Repaired successfully")
        self.assertEqual(err, "")
        mock_helper.assert_called_once()


if __name__ == "__main__":
    unittest.main()
