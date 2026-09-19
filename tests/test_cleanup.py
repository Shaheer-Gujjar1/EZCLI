"""Unit tests for ez cleanup engine and safety checks."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ezcli_app.cleanup.cleaner_engine import (
    clean_thumbnails,
    clean_trash,
    detect_desktop_critical_packages,
    format_bytes,
    scan_apt_cache,
    scan_old_logs,
    scan_orphan_packages,
    scan_thumbnails,
    scan_trash,
)


class TestCleanupEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1024 * 1024 * 5), "5.0 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 2.5), "2.5 GB")

    def test_detect_desktop_critical_packages(self):
        pkgs = ["xorg", "gnome-shell", "libcurl4", "python3-pip", "gdm3", "lightdm", "dde-file-manager", "plasma-desktop"]
        critical = detect_desktop_critical_packages(pkgs)
        self.assertIn("xorg", critical)
        self.assertIn("gnome-shell", critical)
        self.assertIn("gdm3", critical)
        self.assertIn("lightdm", critical)
        self.assertIn("dde-file-manager", critical)
        self.assertIn("plasma-desktop", critical)
        self.assertNotIn("libcurl4", critical)
        self.assertNotIn("python3-pip", critical)

    def test_detect_non_critical_packages(self):
        pkgs = ["curl", "wget", "libssl3", "tree", "htop", "gcc"]
        critical = detect_desktop_critical_packages(pkgs)
        self.assertEqual(critical, [])

    def test_scan_and_clean_trash(self):
        trash_dir = os.path.join(self.temp_dir, "Trash")
        files_dir = os.path.join(trash_dir, "files")
        info_dir = os.path.join(trash_dir, "info")
        os.makedirs(files_dir)
        os.makedirs(info_dir)

        # Create dummy trash files
        f1 = os.path.join(files_dir, "doc.txt")
        with open(f1, "w") as f:
            f.write("hello" * 100)

        f1_info = os.path.join(info_dir, "doc.txt.trashinfo")
        with open(f1_info, "w") as f:
            f.write("[Trash Info]\nPath=/home/user/doc.txt")

        count, total_bytes = scan_trash(trash_dir)
        self.assertEqual(count, 1)
        self.assertEqual(total_bytes, 500)

        freed = clean_trash(trash_dir)
        self.assertEqual(freed, 500)
        self.assertFalse(os.path.exists(f1))
        self.assertFalse(os.path.exists(f1_info))

    def test_scan_and_clean_thumbnails(self):
        thumb_dir = os.path.join(self.temp_dir, "thumbnails")
        normal_dir = os.path.join(thumb_dir, "normal")
        os.makedirs(normal_dir)

        t1 = os.path.join(normal_dir, "thumb1.png")
        with open(t1, "w") as f:
            f.write("PNG" * 200)

        count, total_bytes = scan_thumbnails(thumb_dir)
        self.assertEqual(count, 1)
        self.assertEqual(total_bytes, 600)

        freed = clean_thumbnails(thumb_dir)
        self.assertEqual(freed, 600)
        self.assertFalse(os.path.exists(t1))

    def test_scan_apt_cache(self):
        cache_dir = os.path.join(self.temp_dir, "archives")
        os.makedirs(cache_dir)

        p1 = os.path.join(cache_dir, "pkg1_1.0_amd64.deb")
        with open(p1, "w") as f:
            f.write("deb" * 300)

        p2 = os.path.join(cache_dir, "partial")
        os.makedirs(p2)

        count, total_bytes = scan_apt_cache(cache_dir)
        self.assertEqual(count, 1)
        self.assertEqual(total_bytes, 900)

    def test_scan_old_logs(self):
        log_dir = os.path.join(self.temp_dir, "log")
        os.makedirs(log_dir)

        l1 = os.path.join(log_dir, "syslog.1")
        with open(l1, "w") as f:
            f.write("log" * 50)

        l2 = os.path.join(log_dir, "auth.log.2.gz")
        with open(l2, "w") as f:
            f.write("gz" * 50)

        active = os.path.join(log_dir, "syslog")
        with open(active, "w") as f:
            f.write("active" * 50)

        count, total_bytes = scan_old_logs(log_dir)
        self.assertEqual(count, 2)
        self.assertEqual(total_bytes, 250)

    @patch("subprocess.run")
    def test_scan_orphan_packages_parsing(self, mock_run):
        mock_output = """Reading package lists...
Building dependency tree...
The following packages will be REMOVED:
  libgcc-10-dev libllvm11 xorg-server
0 upgraded, 0 newly installed, 3 to remove and 0 not upgraded.
After this operation, 45.2 MB disk space will be freed.
"""
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        pkgs, freed_bytes = scan_orphan_packages()
        self.assertEqual(pkgs, ["libgcc-10-dev", "libllvm11", "xorg-server"])
        self.assertEqual(freed_bytes, int(45.2 * 1024 * 1024))


if __name__ == "__main__":
    unittest.main()
