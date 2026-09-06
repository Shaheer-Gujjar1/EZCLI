"""Unit tests for 'ez version [name]' universal version checker."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app import __version__
from ezcli_app.version_checker import (
    collect_all_versions,
    detect_apt_catalog_version,
    detect_dpkg_version,
    detect_executable_version,
    detect_flatpak_version,
    detect_node_library_version,
    detect_python_library_version,
    detect_snap_version,
    extract_version_from_text,
    render_version_results,
    run_version_command,
)


class TestVersionChecker(unittest.TestCase):
    def setUp(self):
        self.console = Console(record=True, width=120)

    def test_extract_version_from_text_formats(self):
        cases = [
            ("git version 2.43.0", "2.43.0"),
            ("curl 8.14.1 (x86_64-pc-linux-gnu) libcurl/8.14.1", "8.14.1"),
            ("Python 3.12.3", "3.12.3"),
            ("GNU bash, version 5.2.21(1)-release", "5.2.21"),
            ("tmux 3.4", "3.4"),
            ("tar (GNU tar) 1.35", "1.35"),
            ("nginx/1.24.0", "1.24.0"),
            ("docker version 24.0.7, build 24.0.7-0ubuntu4.1", "24.0.7"),
            ("npm 10.2.4", "10.2.4"),
            ("node v20.11.1", "20.11.1"),
            ("OpenSSH_9.6p1 Ubuntu-3ubuntu13", "9.6p1"),
            ("v1.2.3-beta.1", "1.2.3-beta.1"),
            ("", None),
            ("no digits here", None),
        ]
        for raw, expected in cases:
            self.assertEqual(extract_version_from_text(raw), expected, f"Failed for {raw}")

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("os.path.isfile")
    @patch("os.path.getmtime")
    def test_detect_executable_version(self, mock_mtime, mock_isfile, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/git"
        mock_isfile.return_value = True
        mock_mtime.return_value = 1715000000.0

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "git version 2.43.0\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = detect_executable_version("git")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "Binary")
        self.assertEqual(result["version"], "2.43.0")
        self.assertEqual(result["location"], "/usr/bin/git")
        self.assertIn("2024", result["install_date"])
        self.assertEqual(result["source_order"], 1)

    @patch("subprocess.run")
    def test_detect_dpkg_version(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "curl\t8.14.1-2+deb13u4\tinstall ok installed\n"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = detect_dpkg_version("curl")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "Debian Package")
        self.assertEqual(result["version"], "8.14.1-2+deb13u4")
        self.assertEqual(result["source_order"], 2)

    @patch("subprocess.run")
    def test_detect_apt_catalog_version(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "tree:\n"
            "  Installed: (none)\n"
            "  Candidate: 2.1.1-1\n"
            "  Version table:\n"
            "     2.1.1-1 500\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = detect_apt_catalog_version("tree")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "APT Catalog")
        self.assertEqual(result["version"], "2.1.1-1")
        self.assertEqual(result["source_order"], 3)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_detect_snap_version(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/snap"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "Name    Version  Rev    Tracking       Publisher  Notes\n"
            "spotify 1.2.31   76     latest/stable  spotify    -\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = detect_snap_version("spotify")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "Snap")
        self.assertEqual(result["version"], "1.2.31")
        self.assertEqual(result["source_order"], 4)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_detect_flatpak_version(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/flatpak"
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = (
            "VLC - Media player\n"
            "Version: 3.0.20\n"
            "Ref: org.videolan.VLC/x86_64/stable\n"
        )
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        result = detect_flatpak_version("vlc")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "Flatpak")
        self.assertEqual(result["version"], "3.0.20")
        self.assertEqual(result["source_order"], 5)

    @patch("importlib.metadata.distribution")
    def test_detect_python_library_version(self, mock_dist):
        mock_obj = MagicMock()
        mock_obj.version = "13.7.1"
        mock_obj.metadata = {"Name": "rich"}
        mock_obj._path = "/path/to/rich-13.7.1.dist-info"
        mock_dist.return_value = mock_obj

        result = detect_python_library_version("rich")
        self.assertIsNotNone(result)
        self.assertEqual(result["source_type"], "Python Library")
        self.assertEqual(result["version"], "13.7.1")
        self.assertEqual(result["source_order"], 6)

    def test_detect_node_library_version_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            node_dir = os.path.join(tmpdir, "node_modules", "express")
            os.makedirs(node_dir)
            pkg_file = os.path.join(node_dir, "package.json")
            with open(pkg_file, "w") as f:
                f.write('{"name": "express", "version": "4.19.2"}')

            cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = detect_node_library_version("express")
                self.assertIsNotNone(result)
                self.assertEqual(result["source_type"], "Node.js Library")
                self.assertEqual(result["version"], "4.19.2")
                self.assertEqual(result["source_order"], 7)
            finally:
                os.chdir(cwd)

    @patch("ezcli_app.version_checker.detect_executable_version")
    @patch("ezcli_app.version_checker.detect_dpkg_version")
    @patch("ezcli_app.version_checker.detect_apt_catalog_version")
    @patch("ezcli_app.version_checker.detect_snap_version")
    @patch("ezcli_app.version_checker.detect_flatpak_version")
    @patch("ezcli_app.version_checker.detect_python_library_version")
    @patch("ezcli_app.version_checker.detect_node_library_version")
    def test_collect_all_versions_ordering(
        self, mock_node, mock_py, mock_fl, mock_sn, mock_apt, mock_dpkg, mock_bin
    ):
        mock_bin.return_value = {"source_type": "Binary", "version": "1.0", "source_order": 1}
        mock_dpkg.return_value = {"source_type": "Debian Package", "version": "1.0-1", "source_order": 2}
        mock_apt.return_value = {"source_type": "APT Catalog", "version": "1.0-2", "source_order": 3}
        mock_sn.return_value = {"source_type": "Snap", "version": "1.0.0", "source_order": 4}
        mock_fl.return_value = {"source_type": "Flatpak", "version": "1.0.0", "source_order": 5}
        mock_py.return_value = {"source_type": "Python Library", "version": "1.0.0", "source_order": 6}
        mock_node.return_value = {"source_type": "Node.js Library", "version": "1.0.0", "source_order": 7}

        matches = collect_all_versions("mytool")
        self.assertEqual(len(matches), 7)
        orders = [m["source_order"] for m in matches]
        self.assertEqual(orders, [1, 2, 3, 4, 5, 6, 7])

    def test_render_version_results_single_and_multi_match(self):
        matches = [
            {
                "source_type": "Binary",
                "source_icon": "🖥️",
                "version": "8.14.1",
                "location": "/usr/bin/curl",
                "install_date": "2026-08-05 14:29",
                "source_order": 1,
            },
            {
                "source_type": "Debian Package",
                "source_icon": "📦",
                "version": "8.14.1-2",
                "location": "dpkg (curl)",
                "install_date": "2026-08-05 14:29",
                "source_order": 2,
            },
        ]
        render_version_results(self.console, "curl", matches)
        output = self.console.export_text()
        self.assertIn("Version Information: curl", output)
        self.assertIn("curl", output)
        self.assertIn("Binary", output)
        self.assertIn("8.14.1", output)
        self.assertIn("Debian", output)
        self.assertIn("Package", output)
        self.assertIn("8.14.1-2", output)
        self.assertIn("2 sources detected", output)

    def test_render_version_results_not_found(self):
        render_version_results(self.console, "nonexistent_app", [])
        output = self.console.export_text()
        self.assertIn("No matches found for 'nonexistent_app'", output)
        self.assertIn("package-search", output)
        self.assertIn("nonexistent_app", output)
        self.assertIn("ez installed-packages", output)

    def test_run_version_command_no_arg_shows_ez_version(self):
        run_version_command(name="", console=self.console)
        output = self.console.export_text()
        self.assertIn(f"EasyCLI (ez) v{__version__}", output)
        self.assertIn("ez version", output)
        self.assertIn("<name>", output)


if __name__ == "__main__":
    unittest.main()
