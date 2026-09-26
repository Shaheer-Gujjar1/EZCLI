"""Unit tests for ez firewall engine and CLI commands."""

import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.firewall.firewall_engine import (
    FirewallRule,
    FirewallStatus,
    add_firewall_rule,
    delete_firewall_rule,
    get_firewall_status,
    is_ufw_installed,
    parse_ufw_status_output,
    toggle_firewall,
)


class TestFirewall(unittest.TestCase):
    def test_parse_ufw_status_output(self):
        sample_output = """Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 80/tcp                     ALLOW IN    Anywhere
[ 3] 443                        ALLOW IN    Anywhere
[ 4] 21                         DENY IN     Anywhere
[ 5] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
"""
        active, in_def, out_def, rules, has_ssh = parse_ufw_status_output(sample_output)

        self.assertTrue(active)
        self.assertEqual(in_def, "deny")
        self.assertEqual(out_def, "allow")
        self.assertEqual(len(rules), 5)
        self.assertTrue(has_ssh)

        self.assertEqual(rules[0].index, 1)
        self.assertEqual(rules[0].to_port, "22/tcp")
        self.assertEqual(rules[0].action, "ALLOW")
        self.assertEqual(rules[0].direction, "IN")
        self.assertEqual(rules[0].from_ip, "Anywhere")
        self.assertFalse(rules[0].v6)

        self.assertEqual(rules[3].index, 4)
        self.assertEqual(rules[3].to_port, "21")
        self.assertEqual(rules[3].action, "DENY")

        self.assertTrue(rules[4].v6)

    def test_parse_inactive_status_no_ssh(self):
        sample_output = """Status: inactive
"""
        active, in_def, out_def, rules, has_ssh = parse_ufw_status_output(sample_output)
        self.assertFalse(active)
        self.assertEqual(len(rules), 0)
        self.assertFalse(has_ssh)

    @patch("shutil.which")
    def test_is_ufw_installed(self, mock_which):
        mock_which.return_value = "/usr/sbin/ufw"
        self.assertTrue(is_ufw_installed())

        mock_which.return_value = None
        with patch("os.path.exists", return_value=False):
            self.assertFalse(is_ufw_installed())

    @patch("ezcli_app.firewall.firewall_engine.elevated_run_command")
    @patch("shutil.which", return_value="/usr/sbin/ufw")
    def test_toggle_firewall(self, mock_which, mock_elevated):
        mock_elevated.return_value = (True, "Firewall is active and enabled on system startup", "")
        success, msg = toggle_firewall(True)
        self.assertTrue(success)
        mock_elevated.assert_called_once()
        self.assertIn("enable", mock_elevated.call_args[1]["cmd"])

    @patch("ezcli_app.firewall.firewall_engine.elevated_run_command")
    @patch("shutil.which", return_value="/usr/sbin/ufw")
    def test_add_firewall_rule(self, mock_which, mock_elevated):
        mock_elevated.return_value = (True, "Rule added", "")
        success, msg = add_firewall_rule("allow", "8080", "tcp")
        self.assertTrue(success)
        self.assertIn("8080/tcp", mock_elevated.call_args[1]["cmd"])
        self.assertIn("allow", mock_elevated.call_args[1]["cmd"])

    @patch("ezcli_app.firewall.firewall_engine.elevated_run_command")
    @patch("shutil.which", return_value="/usr/sbin/ufw")
    def test_delete_firewall_rule(self, mock_which, mock_elevated):
        mock_elevated.return_value = (True, "Rule deleted", "")
        success, msg = delete_firewall_rule(3)
        self.assertTrue(success)
        self.assertIn("3", mock_elevated.call_args[1]["cmd"])
        self.assertIn("delete", mock_elevated.call_args[1]["cmd"])


if __name__ == "__main__":
    unittest.main()
