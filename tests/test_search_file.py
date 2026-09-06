"""Unit tests for EasyCLI ez search-file command and engine."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.privileged_helper import helper_search_files
from ezcli_app.search_file import (
    copy_path_to_clipboard,
    fuzzy_match_score,
    interactive_select_and_act,
    open_path_in_system,
    render_search_results_table,
    run_search_file_cli,
    search_home_directory,
    search_system_root,
)


class TestSearchFileEngine(unittest.TestCase):
    """Test suite for fuzzy file searching and scoring."""

    def test_fuzzy_match_score_exact(self):
        score = fuzzy_match_score("wifi_app.py", "wifi_app.py")
        self.assertEqual(score, 100.0)

    def test_fuzzy_match_score_no_extension(self):
        score = fuzzy_match_score("wifi_app", "wifi_app.py")
        self.assertEqual(score, 95.0)

    def test_fuzzy_match_score_prefix(self):
        score = fuzzy_match_score("wifi", "wifi_app.py")
        self.assertEqual(score, 90.0)

    def test_fuzzy_match_score_acronym(self):
        score = fuzzy_match_score("wa", "wifi_app.py")
        self.assertGreaterEqual(score, 80.0)

    def test_fuzzy_match_score_substring(self):
        score = fuzzy_match_score("app", "wifi_app.py")
        self.assertGreaterEqual(score, 70.0)

    def test_fuzzy_match_score_subsequence(self):
        score = fuzzy_match_score("wfap", "wifi_app.py")
        self.assertGreaterEqual(score, 50.0)

    def test_fuzzy_match_score_no_match(self):
        score = fuzzy_match_score("xyz123", "wifi_app.py")
        self.assertEqual(score, 0.0)

    def test_fuzzy_match_score_empty(self):
        self.assertEqual(fuzzy_match_score("", "wifi_app.py"), 0.0)
        self.assertEqual(fuzzy_match_score("wifi", ""), 0.0)


class TestDirectoryScanning(unittest.TestCase):
    """Test directory search and filesystem traversal."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Create mock file structure
        self.file1 = os.path.join(self.test_dir, "my_config.toml")
        with open(self.file1, "w") as f:
            f.write("test config")

        self.sub_dir = os.path.join(self.test_dir, "subfolder")
        os.makedirs(self.sub_dir, exist_ok=True)
        self.file2 = os.path.join(self.sub_dir, "app_report.txt")
        with open(self.file2, "w") as f:
            f.write("sample report")

        # Cache dir that should be pruned
        self.cache_dir = os.path.join(self.test_dir, ".cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "cached_report.txt")
        with open(self.cache_file, "w") as f:
            f.write("cached")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_search_home_directory_custom_root(self):
        with patch("os.path.expanduser", return_value=self.test_dir), \
             patch("os.path.exists", side_effect=lambda p: True if p == self.test_dir else False):
            results = search_home_directory("report", max_results=10)
            paths = [r["path"] for r in results]
            self.assertIn(self.file2, paths)
            self.assertNotIn(self.cache_file, paths)

    def test_helper_search_files(self):
        res = helper_search_files(root_dir=self.test_dir, term="config", max_results=10)
        self.assertTrue(res.get("success"))
        results = res.get("results", [])
        self.assertTrue(any("my_config.toml" in r["name"] for r in results))

    def test_helper_search_files_empty_term(self):
        res = helper_search_files(root_dir=self.test_dir, term="", max_results=10)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("results"), [])

    def test_helper_search_files_nonexistent_root(self):
        res = helper_search_files(root_dir="/nonexistent_path_xyz_123", term="test")
        self.assertFalse(res.get("success"))


class TestActionsAndClipboard(unittest.TestCase):
    """Test clipboard copy, open file, and table rendering."""

    def test_copy_path_to_clipboard(self):
        with patch("subprocess.run") as mock_sub, patch("sys.stdout.write"):
            copied = copy_path_to_clipboard("/home/user/document.txt")
            self.assertTrue(copied)

    def test_open_path_in_system_nonexistent(self):
        ok, msg = open_path_in_system("/nonexistent_path_xyz_999")
        self.assertFalse(ok)
        self.assertIn("no longer exists", msg)

    def test_open_path_in_system_success(self):
        with tempfile.NamedTemporaryFile() as tmp:
            with patch("shutil.which", return_value="/usr/bin/xdg-open"), \
                 patch("subprocess.Popen") as mock_popen:
                ok, msg = open_path_in_system(tmp.name)
                self.assertTrue(ok)
                self.assertIn("Opened", msg)
                mock_popen.assert_called_once()

    def test_render_search_results_table(self):
        console = Console(record=True, width=120)
        results = [
            {
                "name": "report.pdf",
                "path": "/home/shaheer/Documents/report.pdf",
                "is_dir": False,
                "size_str": "1.4 MB",
                "mtime_str": "2026-09-07 00:00",
                "icon": "📄",
                "score": 90.0,
            }
        ]
        render_search_results_table(results, "report", "/home", console=console)
        output = console.export_text()
        self.assertIn("report.pdf", output)
        self.assertIn("1.4 MB", output)


class TestInteractiveFlow(unittest.TestCase):
    """Test interactive menu and CLI flow."""

    def test_interactive_select_and_act_quit(self):
        console = Console(record=True)
        results = [
            {
                "name": "test.py",
                "path": "/home/user/test.py",
                "is_dir": False,
                "size_str": "500 B",
                "mtime_str": "2026-09-07",
                "icon": "🐍",
                "score": 100.0,
            }
        ]
        with patch("rich.prompt.Prompt.ask", return_value="q"):
            interactive_select_and_act(results, "test", console=console, searched_system=False)
        self.assertIn("Search closed", console.export_text())

    def test_interactive_select_and_act_open(self):
        console = Console(record=True)
        results = [
            {
                "name": "test.py",
                "path": "/home/user/test.py",
                "is_dir": False,
                "size_str": "500 B",
                "mtime_str": "2026-09-07",
                "icon": "🐍",
                "score": 100.0,
            }
        ]
        # User enters "1" to select file, then "1" to open, then "q" to exit
        with patch("rich.prompt.Prompt.ask", side_effect=["1", "1", "q"]), \
             patch("ezcli_app.search_file.open_path_in_system", return_value=(True, "Opened")):
            interactive_select_and_act(results, "test", console=console, searched_system=False)

    def test_interactive_select_and_act_copy(self):
        console = Console(record=True)
        results = [
            {
                "name": "test.py",
                "path": "/home/user/test.py",
                "is_dir": False,
                "size_str": "500 B",
                "mtime_str": "2026-09-07",
                "icon": "🐍",
                "score": 100.0,
            }
        ]
        # User enters "1" to select file, then "2" to copy path, then "q" to exit
        with patch("rich.prompt.Prompt.ask", side_effect=["1", "2", "q"]), \
             patch("ezcli_app.search_file.copy_path_to_clipboard", return_value=True):
            interactive_select_and_act(results, "test", console=console, searched_system=False)
        self.assertIn("Path copied to clipboard", console.export_text())

    def test_interactive_select_and_act_system_search_trigger(self):
        console = Console(record=True)
        home_results = [
            {
                "name": "home_test.py",
                "path": "/home/user/home_test.py",
                "is_dir": False,
                "size_str": "100 B",
                "mtime_str": "2026-09-07",
                "icon": "🐍",
                "score": 80.0,
            }
        ]
        sys_results = [
            {
                "name": "sys_test.conf",
                "path": "/etc/sys_test.conf",
                "is_dir": False,
                "size_str": "200 B",
                "mtime_str": "2026-09-07",
                "icon": "⚙️",
                "score": 90.0,
            }
        ]
        # User presses "s" to search system, then "q" to exit
        with patch("rich.prompt.Prompt.ask", side_effect=["s", "q"]), \
             patch("ezcli_app.search_file.search_system_root", return_value=sys_results):
            interactive_select_and_act(home_results, "test", console=console, searched_system=False)
        self.assertIn("sys_test.conf", console.export_text())

    def test_run_search_file_cli_no_term(self):
        console = Console(record=True)
        run_search_file_cli(term=None, console=console)
        out = console.export_text()
        self.assertIn("Usage:", out)
        self.assertIn("ez search-file <term>", out)

    def test_run_search_file_cli_fallback_prompt_yes(self):
        console = Console(record=True)
        sys_results = [
            {
                "name": "hosts",
                "path": "/etc/hosts",
                "is_dir": False,
                "size_str": "150 B",
                "mtime_str": "2026-09-07",
                "icon": "⚙️",
                "score": 100.0,
            }
        ]
        with patch("ezcli_app.search_file.search_home_directory", return_value=[]), \
             patch("rich.prompt.Prompt.ask", side_effect=["y", "q"]), \
             patch("ezcli_app.search_file.search_system_root", return_value=sys_results):
            run_search_file_cli(term="hosts", console=console)
        self.assertIn("hosts", console.export_text())

    def test_run_search_file_cli_fallback_prompt_no(self):
        console = Console(record=True)
        with patch("ezcli_app.search_file.search_home_directory", return_value=[]), \
             patch("rich.prompt.Prompt.ask", return_value="n"):
            run_search_file_cli(term="hosts", console=console)
        self.assertIn("Search cancelled", console.export_text())


if __name__ == "__main__":
    unittest.main()
