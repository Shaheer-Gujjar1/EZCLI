"""Unit tests for ez startup-apps engine and toggles."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ezcli_app.startup_apps.startup_engine import (
    StartupItem,
    is_service_critical,
    parse_desktop_file,
    toggle_login_app,
)


class TestStartupApps(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_is_service_critical(self):
        self.assertTrue(is_service_critical("NetworkManager.service"))
        self.assertTrue(is_service_critical("dbus.service"))
        self.assertTrue(is_service_critical("gdm3.service"))
        self.assertTrue(is_service_critical("systemd-logind.service"))
        self.assertTrue(is_service_critical("ssh.service"))
        self.assertFalse(is_service_critical("bluetooth.service"))
        self.assertFalse(is_service_critical("cups.service"))
        self.assertFalse(is_service_critical("nginx.service"))

    def test_parse_desktop_file(self):
        f = Path(self.temp_dir) / "app.desktop"
        f.write_text(
            "[Desktop Entry]\n"
            "Name=Test Application\n"
            "Comment=Starts on login\n"
            "Exec=/usr/bin/testapp\n"
            "Hidden=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
        data = parse_desktop_file(f)
        self.assertIsNotNone(data)
        self.assertEqual(data["Name"], "Test Application")
        self.assertEqual(data["Comment"], "Starts on login")
        self.assertEqual(data["Exec"], "/usr/bin/testapp")
        self.assertEqual(data["Hidden"], "false")

    def test_toggle_login_app_enable_disable(self):
        autostart_dir = Path(self.temp_dir) / ".config" / "autostart"
        autostart_dir.mkdir(parents=True)

        desktop_file = autostart_dir / "myapp.desktop"
        desktop_file.write_text(
            "[Desktop Entry]\n"
            "Name=MyApp\n"
            "Exec=/usr/bin/myapp\n"
            "Hidden=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )

        item = StartupItem(
            id="myapp.desktop",
            name="MyApp",
            description="Sample app",
            item_type="login",
            state="Enabled",
            exec_cmd="/usr/bin/myapp",
            file_path=str(desktop_file),
            is_critical=False,
        )

        with patch("pathlib.Path.home", return_value=Path(self.temp_dir)):
            # Toggle from Enabled -> Disabled
            ok, msg = toggle_login_app(item)
            self.assertTrue(ok)
            self.assertEqual(item.state, "Disabled")
            content = desktop_file.read_text(encoding="utf-8")
            self.assertIn("Hidden=true", content)
            self.assertIn("X-GNOME-Autostart-enabled=false", content)

            # Toggle from Disabled -> Enabled
            ok, msg = toggle_login_app(item)
            self.assertTrue(ok)
            self.assertEqual(item.state, "Enabled")
            content = desktop_file.read_text(encoding="utf-8")
            self.assertIn("Hidden=false", content)
            self.assertIn("X-GNOME-Autostart-enabled=true", content)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_scan_boot_services(self, mock_run, mock_which):
        from ezcli_app.startup_apps.startup_engine import scan_boot_services
        mock_which.return_value = "/bin/systemctl"

        mock_out = """cron.service                               enabled         enabled
NetworkManager.service                     enabled         enabled
bluetooth.service                          disabled        enabled
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_out, stderr="")

        items = scan_boot_services()
        self.assertEqual(len(items), 3)

        nm = next(it for it in items if it.name == "NetworkManager")
        self.assertTrue(nm.is_critical)
        self.assertEqual(nm.state, "Enabled")

        cron = next(it for it in items if it.name == "cron")
        self.assertFalse(cron.is_critical)
        self.assertEqual(cron.state, "Enabled")

        bt = next(it for it in items if it.name == "bluetooth")
        self.assertEqual(bt.state, "Disabled")

    @patch("ezcli_app.elevation.run_elevated_helper")
    def test_elevated_toggle_service(self, mock_helper):
        from ezcli_app.elevation import elevated_toggle_service
        mock_helper.return_value = (True, {"success": True}, "")
        ok, err = elevated_toggle_service("cron.service", enable=False)
        self.assertTrue(ok)
        mock_helper.assert_called_once()
        args, kwargs = mock_helper.call_args
        self.assertEqual(kwargs["action"], "toggle_service")
        self.assertEqual(kwargs["params"]["unit"], "cron.service")
        self.assertEqual(kwargs["params"]["enable"], False)


if __name__ == "__main__":
    unittest.main()
