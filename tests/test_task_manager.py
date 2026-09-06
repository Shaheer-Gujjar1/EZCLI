"""Unit tests for EasyCLI Task Manager and Process Engine."""

import os
import signal
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from ezcli_app.config import FEATURES_BY_SUBCOMMAND
from ezcli_app.task_manager.process_engine import ProcessEngine, ProcessItem
from ezcli_app.task_manager.task_manager_app import TaskManagerApp, make_mini_gauge


class TestProcessEngine(unittest.TestCase):
    """Test process collection, categorization, unresponsive detection, and termination."""

    def setUp(self):
        self.engine = ProcessEngine()

    def test_feature_registration(self):
        self.assertIn("task-manager", FEATURES_BY_SUBCOMMAND)
        feat_norm = FEATURES_BY_SUBCOMMAND["task-manager"]
        self.assertEqual(feat_norm.subcommand, "task-manager")
        self.assertEqual(feat_norm.icon, "📋")

        self.assertIn("task-manager-pro", FEATURES_BY_SUBCOMMAND)
        feat_pro = FEATURES_BY_SUBCOMMAND["task-manager-pro"]
        self.assertEqual(feat_pro.subcommand, "task-manager-pro")
        self.assertEqual(feat_pro.icon, "🛡️")

    def test_resolve_app_name_and_icon(self):
        # Browsers
        name, icon = self.engine.resolve_app_name_and_icon("chrome", "/opt/google/chrome/chrome")
        self.assertIn("Chrome", name)
        self.assertEqual(icon, "🌐")

        name, icon = self.engine.resolve_app_name_and_icon("firefox", "/usr/bin/firefox")
        self.assertIn("Firefox", name)
        self.assertEqual(icon, "🦊")

        # Editors & IDEs
        name, icon = self.engine.resolve_app_name_and_icon("code", "/usr/share/code/code")
        self.assertIn("VS Code", name)
        self.assertEqual(icon, "📝")

        # Media
        name, icon = self.engine.resolve_app_name_and_icon("vlc", "/usr/bin/vlc")
        self.assertIn("VLC", name)
        self.assertEqual(icon, "🎬")

        # Terminals
        name, icon = self.engine.resolve_app_name_and_icon("bash", "/bin/bash")
        self.assertIn("Bash", name)
        self.assertEqual(icon, "🐚")

    def test_classify_process(self):
        # 1. Kernel thread
        cat, badge = self.engine.classify_process(
            pid=4, ppid=2, user="root", tty="?", comm="kworker/0:0", args="[kworker/0:0]"
        )
        self.assertEqual(cat, "system")
        self.assertIn("System", badge)

        # 2. System root daemon
        cat, badge = self.engine.classify_process(
            pid=1, ppid=0, user="root", tty="?", comm="systemd", args="/sbin/init"
        )
        self.assertEqual(cat, "system")
        self.assertIn("System", badge)

        # 3. Background desktop daemon under user
        cat, badge = self.engine.classify_process(
            pid=1800, ppid=1700, user="shaheer", tty="?", comm="gvfsd", args="/usr/libexec/gvfsd"
        )
        self.assertEqual(cat, "background")
        self.assertIn("Background", badge)

        cat, badge = self.engine.classify_process(
            pid=1850, ppid=1700, user="shaheer", tty="?", comm="pipewire", args="/usr/bin/pipewire"
        )
        self.assertEqual(cat, "background")
        self.assertIn("Background", badge)

        # 4. User interactive application
        cat, badge = self.engine.classify_process(
            pid=3200, ppid=1700, user="shaheer", tty="?", comm="vlc", args="/usr/bin/vlc movie.mp4"
        )
        self.assertEqual(cat, "app")
        self.assertIn("App", badge)

        cat, badge = self.engine.classify_process(
            pid=4500, ppid=3000, user="shaheer", tty="pts/1", comm="python3", args="python3 test.py"
        )
        self.assertEqual(cat, "app")
        self.assertIn("App", badge)

    def test_detect_unresponsive(self):
        # D state (I/O hang) -> Unresponsive
        is_unresp, icon, text, badge = self.engine.detect_unresponsive("D+", 0.0, "cp")
        self.assertTrue(is_unresp)
        self.assertEqual(icon, "⚠️")
        self.assertEqual(text, "Unresponsive")
        self.assertIn("I/O Wait", badge)

        # Z state (Zombie) -> Unresponsive
        is_unresp, icon, text, badge = self.engine.detect_unresponsive("Z", 0.0, "app")
        self.assertTrue(is_unresp)
        self.assertEqual(icon, "💀")
        self.assertEqual(text, "Zombie")

        # T state (Stopped) -> Unresponsive
        is_unresp, icon, text, badge = self.engine.detect_unresponsive("T", 0.0, "nano")
        self.assertTrue(is_unresp)
        self.assertEqual(icon, "⏸️")
        self.assertEqual(text, "Stopped")

        # Normal Active state
        is_unresp, icon, text, badge = self.engine.detect_unresponsive("R+", 5.2, "vlc")
        self.assertFalse(is_unresp)
        self.assertEqual(icon, "🟢")
        self.assertEqual(text, "Running")

        # Normal Idle state
        is_unresp, icon, text, badge = self.engine.detect_unresponsive("S", 0.0, "bash")
        self.assertFalse(is_unresp)
        self.assertEqual(icon, "🟡")
        self.assertEqual(text, "Idle")

    @patch("subprocess.run")
    def test_get_processes_normal_mode_apps_only(self, mock_run):
        # Mock ps output with 1 app, 1 background daemon, 1 system process, and 1 unresponsive app
        mock_output = (
            "       PID       PPID USER           TT               %CPU  %MEM        RSS     STAT       TIME COMMAND              COMMAND\n"
            "         1          0 root           ?                 0.1   0.1       9500 Ss     00:00:02 systemd              /sbin/init\n"
            "      1772       1744 shaheer        ?                 0.2   0.1       5000 Ssl    00:00:01 pipewire             /usr/bin/pipewire\n"
            "      3200       1744 shaheer        ?                 5.0   2.5     120000 Sl     00:01:20 vlc                  /usr/bin/vlc\n"
            "      4100       1744 shaheer        pts/0             0.0   1.0      40000 D+     00:00:05 gedit                /usr/bin/gedit file.txt\n"
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_output
        mock_run.return_value = mock_proc

        items, summary = self.engine.get_processes(mode="normal")

        # Normal mode should filter out systemd (system) and pipewire (background), leaving only vlc and gedit!
        self.assertEqual(len(items), 2)
        pids = [p.pid for p in items]
        self.assertIn(3200, pids)
        self.assertIn(4100, pids)
        self.assertNotIn(1, pids)
        self.assertNotIn(1772, pids)

        # Unresponsive process (gedit with state D+) should be prioritized and tagged
        gedit_p = next(p for p in items if p.pid == 4100)
        self.assertTrue(gedit_p.is_unresponsive)
        self.assertEqual(gedit_p.status_icon, "⚠️")
        self.assertEqual(gedit_p.status_text, "Unresponsive")
        self.assertEqual(summary["unresponsive_count"], 1)

    @patch("subprocess.run")
    def test_get_processes_pro_mode_includes_all(self, mock_run):
        mock_output = (
            "       PID       PPID USER           TT               %CPU  %MEM        RSS     STAT       TIME COMMAND              COMMAND\n"
            "         1          0 root           ?                 0.1   0.1       9500 Ss     00:00:02 systemd              /sbin/init\n"
            "      1772       1744 shaheer        ?                 0.2   0.1       5000 Ssl    00:00:01 pipewire             /usr/bin/pipewire\n"
            "      3200       1744 shaheer        ?                 5.0   2.5     120000 Sl     00:01:20 vlc                  /usr/bin/vlc\n"
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_output
        mock_run.return_value = mock_proc

        items, summary = self.engine.get_processes(mode="pro")

        # Pro mode should return all 3 processes
        self.assertEqual(len(items), 3)
        cats = [p.category for p in items]
        self.assertIn("system", cats)
        self.assertIn("background", cats)
        self.assertIn("app", cats)

    @patch("subprocess.run")
    def test_get_processes_category_filters(self, mock_run):
        mock_output = (
            "       PID       PPID USER           TT               %CPU  %MEM        RSS     STAT       TIME COMMAND              COMMAND\n"
            "         1          0 root           ?                 0.1   0.1       9500 Ss     00:00:02 systemd              /sbin/init\n"
            "      1772       1744 shaheer        ?                 0.2   0.1       5000 Ssl    00:00:01 pipewire             /usr/bin/pipewire\n"
            "      3200       1744 shaheer        ?                 5.0   2.5     120000 Sl     00:01:20 vlc                  /usr/bin/vlc\n"
            "      4100       1744 shaheer        pts/0             0.0   1.0      40000 D+     00:00:05 gedit                /usr/bin/gedit\n"
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_output
        mock_run.return_value = mock_proc

        # Filter by "app"
        app_items, _ = self.engine.get_processes(mode="pro", category_filter="app")
        self.assertEqual(len(app_items), 2)

        # Filter by "system"
        sys_items, _ = self.engine.get_processes(mode="pro", category_filter="system")
        self.assertEqual(len(sys_items), 1)
        self.assertEqual(sys_items[0].pid, 1)

        # Filter by "background"
        bg_items, _ = self.engine.get_processes(mode="pro", category_filter="background")
        self.assertEqual(len(bg_items), 1)
        self.assertEqual(bg_items[0].pid, 1772)

        # Filter by "unresponsive"
        unresp_items, _ = self.engine.get_processes(mode="pro", category_filter="unresponsive")
        self.assertEqual(len(unresp_items), 1)
        self.assertEqual(unresp_items[0].pid, 4100)

    @patch("subprocess.run")
    def test_get_processes_search_filter(self, mock_run):
        mock_output = (
            "       PID       PPID USER           TT               %CPU  %MEM        RSS     STAT       TIME COMMAND              COMMAND\n"
            "      3200       1744 shaheer        ?                 5.0   2.5     120000 Sl     00:01:20 vlc                  /usr/bin/vlc\n"
            "      4100       1744 shaheer        pts/0             0.0   1.0      40000 S+     00:00:05 gedit                /usr/bin/gedit\n"
        )
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = mock_output
        mock_run.return_value = mock_proc

        items, _ = self.engine.get_processes(mode="normal", filter_text="vlc")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "VLC Media Player")


    @patch("os.kill")
    def test_terminate_process_success(self, mock_kill):
        ok, msg = self.engine.terminate_process(1234, signal.SIGTERM)
        self.assertTrue(ok)
        mock_kill.assert_called_once_with(1234, signal.SIGTERM)
        self.assertIn("Successfully sent SIGTERM", msg)

    @patch("os.kill", side_effect=PermissionError)
    @patch("ezcli_app.elevation.elevated_run_command")
    def test_terminate_process_elevation_fallback(self, mock_elev, mock_kill):
        mock_elev.return_value = (True, "", "")

        ok, msg = self.engine.terminate_process(999, signal.SIGKILL, is_pro=True)
        self.assertTrue(ok)
        self.assertIn("using administrator privileges", msg)
        mock_elev.assert_called_once()
        cmd_sent = mock_elev.call_args[1]["cmd"]
        self.assertEqual(cmd_sent, ["kill", f"-{signal.SIGKILL}", "999"])

    def test_make_mini_gauge(self):
        gauge_low = make_mini_gauge(15.0, width=10)
        self.assertIn("15.0%", gauge_low)
        self.assertIn("bold green", gauge_low)

        gauge_high = make_mini_gauge(85.0, width=10)
        self.assertIn("85.0%", gauge_high)
        self.assertIn("bold red", gauge_high)


class TestTaskManagerApp(unittest.TestCase):
    """Test TaskManagerApp initialization in normal and pro modes."""

    def test_app_init_modes(self):
        app_normal = TaskManagerApp(mode="normal")
        self.assertEqual(app_normal.mode, "normal")

        app_pro = TaskManagerApp(mode="pro")
        self.assertEqual(app_pro.mode, "pro")


if __name__ == "__main__":
    unittest.main()
