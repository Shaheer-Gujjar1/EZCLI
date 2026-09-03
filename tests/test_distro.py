"""Tests for Debian-based distribution detection."""

import tempfile
import unittest
from pathlib import Path
from ezcli_app.distro import parse_os_release, detect_distro


class TestDistro(unittest.TestCase):
    def test_parse_os_release_mock_ubuntu(self):
        mock_content = """
NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"
VERSION_CODENAME=jammy
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(mock_content)
            temp_path = f.name

        try:
            parsed = parse_os_release(temp_path)
            self.assertEqual(parsed.get("ID"), "ubuntu")
            self.assertEqual(parsed.get("VERSION_CODENAME"), "jammy")

            distro = detect_distro(temp_path)
            self.assertEqual(distro.id, "ubuntu")
            self.assertEqual(distro.name, "Ubuntu")
            self.assertTrue(distro.is_debian_based)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_os_release_mock_deepin(self):
        mock_content = """
PRETTY_NAME="Deepin 25"
NAME="Deepin"
VERSION_CODENAME=crimson
ID=deepin
VERSION_ID="25"
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(mock_content)
            temp_path = f.name

        try:
            distro = detect_distro(temp_path)
            self.assertEqual(distro.id, "deepin")
            self.assertTrue(distro.is_debian_based)
            self.assertEqual(distro.codename, "crimson")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_parse_os_release_mock_zorin(self):
        mock_content = """
NAME="Zorin OS"
VERSION="17"
ID=zorin
ID_LIKE="ubuntu debian"
PRETTY_NAME="Zorin OS 17"
"""
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write(mock_content)
            temp_path = f.name

        try:
            distro = detect_distro(temp_path)
            self.assertEqual(distro.id, "zorin")
            self.assertTrue(distro.is_debian_based)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_current_host_distro(self):
        distro = detect_distro()
        self.assertIsNotNone(distro.name)
        self.assertIsNotNone(distro.id)
        # Deepin 25 running on host
        self.assertTrue(distro.is_debian_based)


if __name__ == "__main__":
    unittest.main()
