"""Tests for 'ez run' universal runner, detector, guided mode, and CLI orchestrator."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from rich.console import Console

from ezcli_app.run_cli import (
    _extract_options_for_cli,
    _handle_chmod,
    _launch_gui,
    _run_cli_foreground,
    run_cli_run,
)
from ezcli_app.run_detector import (
    ResolvedTarget,
    detect_desktop_entry_by_name,
    detect_flatpak_candidates,
    detect_script_interpreter,
    detect_snap_app,
    find_desktop_entry_for_binary,
    parse_desktop_file,
    resolve_target,
)
from ezcli_app.run_guide import (
    HelpOption,
    parse_help_text,
    run_guided_form,
    safe_probe_help,
    static_parse_python_script,
    static_parse_shell_script,
)


class TestRunDetector(unittest.TestCase):
    """Unit tests for run_detector.py."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def test_detect_script_interpreter_by_extension(self):
        py_file = os.path.join(self.temp_dir.name, "script.py")
        with open(py_file, "w") as f:
            f.write("print('hello')\n")

        interpreter, label = detect_script_interpreter(py_file)
        self.assertIsNotNone(interpreter)
        assert interpreter is not None
        self.assertIn("python", interpreter)
        self.assertIn("Python", label)

    def test_detect_script_interpreter_by_shebang(self):
        no_ext = os.path.join(self.temp_dir.name, "runner")
        with open(no_ext, "w") as f:
            f.write("#!/usr/bin/env bash\necho hi\n")

        interpreter, label = detect_script_interpreter(no_ext)
        self.assertIsNotNone(interpreter)
        assert interpreter is not None
        self.assertIn("bash", interpreter)
        self.assertIn("Bash", label)

    def test_resolve_local_python_script(self):
        script_path = os.path.join(self.temp_dir.name, "test_job.py")
        with open(script_path, "w") as f:
            f.write("print('test')\n")

        target, candidates, err = resolve_target(script_path, cwd=self.temp_dir.name)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_type, "script")
        self.assertEqual(target.name, "test_job.py")
        self.assertFalse(target.is_gui)
        self.assertTrue(target.needs_chmod)  # Not +x yet

    def test_resolve_local_appimage(self):
        appimage_path = os.path.join(self.temp_dir.name, "MyApp.AppImage")
        with open(appimage_path, "w") as f:
            f.write("APPIMAGE DUMMY")

        target, candidates, err = resolve_target(appimage_path, cwd=self.temp_dir.name)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_type, "appimage")
        self.assertTrue(target.is_gui)
        self.assertTrue(target.needs_chmod)

    def test_resolve_directory_returns_error(self):
        sub_dir = os.path.join(self.temp_dir.name, "my_folder")
        os.makedirs(sub_dir)

        target, candidates, err = resolve_target(sub_dir, cwd=self.temp_dir.name)
        self.assertIsNone(target)
        self.assertIn("is a directory", err)

    @patch("shutil.which")
    def test_resolve_path_binary_cli(self, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/htop" if cmd == "htop" else None

        with patch("ezcli_app.run_detector.find_desktop_entry_for_binary", return_value=None):
            target, candidates, err = resolve_target("htop", cwd=self.temp_dir.name)
            self.assertIsNotNone(target)
            assert target is not None
            self.assertEqual(target.target_type, "binary")
            self.assertEqual(target.name, "htop")
            self.assertFalse(target.is_gui)

    @patch("shutil.which")
    def test_resolve_path_binary_gui_via_desktop_entry(self, mock_which):
        mock_which.side_effect = lambda cmd: "/usr/bin/vlc" if cmd == "vlc" else None

        # Fix 1: Desktop entry with Terminal=false classifies binary as GUI
        with patch("ezcli_app.run_detector.find_desktop_entry_for_binary", return_value=("/usr/share/applications/vlc.desktop", False)):
            target, candidates, err = resolve_target("vlc", cwd=self.temp_dir.name)
            self.assertIsNotNone(target)
            assert target is not None
            self.assertEqual(target.target_type, "binary")
            self.assertTrue(target.is_gui)

    @patch("shutil.which", return_value=None)
    @patch("ezcli_app.run_detector.detect_snap_app")
    def test_resolve_snap_app(self, mock_snap, mock_which):
        mock_snap.return_value = ("spotify", True)

        target, candidates, err = resolve_target("spotify", cwd=self.temp_dir.name)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_type, "snap")
        self.assertEqual(target.exec_cmd, ["snap", "run", "spotify"])
        self.assertTrue(target.is_gui)

    @patch("shutil.which", return_value=None)
    @patch("ezcli_app.run_detector.detect_snap_app", return_value=None)
    @patch("ezcli_app.run_detector.detect_flatpak_candidates")
    def test_resolve_flatpak_single(self, mock_flatpak, mock_snap, mock_which):
        mock_flatpak.return_value = [("GIMP", "org.gimp.GIMP", "Image Editor")]

        target, candidates, err = resolve_target("gimp", cwd=self.temp_dir.name)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_type, "flatpak")
        self.assertEqual(target.exec_cmd, ["flatpak", "run", "org.gimp.GIMP"])
        self.assertTrue(target.is_gui)

    @patch("shutil.which", return_value=None)
    @patch("ezcli_app.run_detector.detect_snap_app", return_value=None)
    @patch("ezcli_app.run_detector.detect_flatpak_candidates")
    def test_resolve_flatpak_multiple_candidates(self, mock_flatpak, mock_snap, mock_which):
        # Fix 4: Multiple candidates returns candidate list for selection menu
        mock_flatpak.return_value = [
            ("Firefox", "org.mozilla.firefox", "Web Browser"),
            ("Firefox Developer", "org.mozilla.FirefoxDev", "Dev Browser"),
        ]

        target, candidates, err = resolve_target("firefox", cwd=self.temp_dir.name)
        self.assertIsNone(target)
        self.assertEqual(len(candidates), 2)

    @patch("shutil.which")
    @patch("ezcli_app.run_detector.detect_snap_app", return_value=None)
    @patch("ezcli_app.run_detector.detect_flatpak_candidates", return_value=[])
    @patch("ezcli_app.run_detector.detect_desktop_entry_by_name")
    def test_resolve_desktop_entry(self, mock_desktop, mock_flatpak, mock_snap, mock_which):
        mock_desktop.return_value = ("/usr/share/applications/calc.desktop", "Calculator", False)
        mock_which.side_effect = lambda cmd: "/usr/bin/gio" if cmd == "gio" else None

        target, candidates, err = resolve_target("calc", cwd=self.temp_dir.name)
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.target_type, "desktop")
        self.assertEqual(target.exec_cmd, ["gio", "launch", "/usr/share/applications/calc.desktop"])
        self.assertTrue(target.is_gui)

    @patch("shutil.which", return_value=None)
    @patch("ezcli_app.run_detector.detect_snap_app", return_value=None)
    @patch("ezcli_app.run_detector.detect_flatpak_candidates", return_value=[])
    @patch("ezcli_app.run_detector.detect_desktop_entry_by_name", return_value=None)
    def test_resolve_not_found(self, mock_desktop, mock_flatpak, mock_snap, mock_which):
        target, candidates, err = resolve_target("nonexistent_utility_12345", cwd=self.temp_dir.name)
        self.assertIsNone(target)
        self.assertEqual(candidates, [])
        self.assertIn("not found", err)


class TestRunGuide(unittest.TestCase):
    """Unit tests for run_guide.py (safe probing, static AST parsing, option parsing)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.console = Console(record=True)

    def test_static_parse_python_script(self):
        # Fix 3: Statically parse argparse without executing script
        py_file = os.path.join(self.temp_dir.name, "cli_tool.py")
        code = """
import argparse
parser = argparse.ArgumentParser(description="Demo tool")
parser.add_argument("--input", "-i", help="Input file path")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
parser.add_argument("--mode", choices=["fast", "accurate"], default="fast", help="Execution mode")
args = parser.parse_args()
"""
        with open(py_file, "w") as f:
            f.write(code)

        options = static_parse_python_script(py_file)
        self.assertEqual(len(options), 3)

        input_opt = next(o for o in options if "--input" in o.flags)
        self.assertEqual(input_opt.option_type, "path")

        verb_opt = next(o for o in options if "--verbose" in o.flags)
        self.assertEqual(verb_opt.option_type, "boolean")

        mode_opt = next(o for o in options if "--mode" in o.flags)
        self.assertEqual(mode_opt.option_type, "choice")
        self.assertIn("fast", mode_opt.choices)
        self.assertIn("accurate", mode_opt.choices)

    def test_static_parse_shell_script(self):
        sh_file = os.path.join(self.temp_dir.name, "script.sh")
        code = """
while getopts "vf:o:" opt; do
  case "$opt" in
    v) verbose=1 ;;
    f) file="$OPTARG" ;;
    o) output="$OPTARG" ;;
  esac
done
"""
        with open(sh_file, "w") as f:
            f.write(code)

        options = static_parse_shell_script(sh_file)
        self.assertGreaterEqual(len(options), 3)
        flags = [o.flags[0] for o in options]
        self.assertIn("-v", flags)
        self.assertIn("-f", flags)
        self.assertIn("-o", flags)

    @patch("subprocess.run")
    def test_safe_probe_help_rules(self, mock_run):
        # Fix 2: Probes --help first; does NOT probe -h if --help succeeds
        mock_res = MagicMock()
        mock_res.stdout = "Usage: mycmd [options]\nOptions:\n  --verbose  Show details"
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        out = safe_probe_help(["mycmd"])
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn("Usage:", out)

        # Ensure probe called with --help, stdin=DEVNULL, timeout
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["mycmd", "--help"])
        self.assertEqual(kwargs.get("stdin"), subprocess.DEVNULL)
        self.assertEqual(kwargs.get("timeout"), 2.5)

    def test_parse_help_text(self):
        sample_help = """
Usage: mytool [OPTIONS] COMMAND

Options:
  -o, --output PATH       Path to destination file
  -v, --verbose           Enable debug output
  -m, --mode {fast,slow}  Operating mode
  --help                  Show this message and exit
"""
        options = parse_help_text(sample_help)
        self.assertEqual(len(options), 3)

        out_opt = next(o for o in options if "--output" in o.flags)
        self.assertEqual(out_opt.option_type, "path")

        verb_opt = next(o for o in options if "--verbose" in o.flags)
        self.assertEqual(verb_opt.option_type, "boolean")

        mode_opt = next(o for o in options if "--mode" in o.flags)
        self.assertEqual(mode_opt.option_type, "choice")
        self.assertEqual(mode_opt.choices, ["fast", "slow"])

    @patch("ezcli_app.run_guide.Confirm.ask")
    def test_run_guided_form_mandatory_preview_confirmation(self, mock_confirm):
        # Confirm for boolean option = True; Confirm for final execution = True
        mock_confirm.side_effect = [True, True]

        options = [
            HelpOption(
                flags=["-v", "--verbose"],
                name="verbose",
                option_type="boolean",
                help_text="Verbose logging",
            )
        ]

        final_cmd = run_guided_form(
            options=options,
            base_cmd=["mytool"],
            target_name="mytool",
            console=self.console,
        )

        self.assertIsNotNone(final_cmd)
        self.assertEqual(final_cmd, ["mytool", "--verbose"])

    @patch("ezcli_app.run_guide.Confirm.ask")
    def test_run_guided_form_declined_execution(self, mock_confirm):
        # User configures options, but declines the mandatory preview confirmation
        mock_confirm.side_effect = [True, False]

        options = [
            HelpOption(
                flags=["--flag"],
                name="flag",
                option_type="boolean",
            )
        ]

        final_cmd = run_guided_form(
            options=options,
            base_cmd=["mytool"],
            target_name="mytool",
            console=self.console,
        )

        self.assertIsNone(final_cmd)


class TestRunCLI(unittest.TestCase):
    """Unit tests for run_cli.py orchestrator."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.console = Console(record=True)

    @patch("ezcli_app.run_cli.Confirm.ask", return_value=True)
    def test_handle_chmod_success(self, mock_confirm):
        test_file = os.path.join(self.temp_dir.name, "run_me.sh")
        with open(test_file, "w") as f:
            f.write("#!/bin/bash\necho ok\n")

        # Ensure not executable
        os.chmod(test_file, 0o644)
        target = ResolvedTarget(
            name="run_me.sh",
            target_type="script",
            exec_cmd=[test_file],
            file_path=test_file,
            is_executable=False,
            needs_chmod=True,
        )

        res = _handle_chmod(target, self.console)
        self.assertTrue(res)
        self.assertTrue(os.access(test_file, os.X_OK))

    @patch("ezcli_app.run_cli.Confirm.ask", return_value=False)
    def test_handle_chmod_declined_script_with_interpreter(self, mock_confirm):
        test_file = os.path.join(self.temp_dir.name, "run_me.py")
        with open(test_file, "w") as f:
            f.write("print('ok')\n")

        target = ResolvedTarget(
            name="run_me.py",
            target_type="script",
            exec_cmd=["python3", test_file],
            file_path=test_file,
            interpreter="python3",
            is_executable=False,
            needs_chmod=True,
        )

        res = _handle_chmod(target, self.console)
        # Should return True because it can run via interpreter
        self.assertTrue(res)

    @patch("subprocess.Popen")
    def test_launch_gui_appimage_fuse_error(self, mock_popen):
        proc_mock = MagicMock()
        proc_mock.returncode = 1
        proc_mock.communicate.return_value = (b"", b"dlopen(): error loading libfuse.so.2: cannot open shared object file")
        mock_popen.return_value = proc_mock

        target = ResolvedTarget(
            name="App.AppImage",
            target_type="appimage",
            exec_cmd=["/path/to/App.AppImage"],
            file_path="/path/to/App.AppImage",
            is_gui=True,
        )

        _launch_gui(target, [], self.console)
        output = self.console.export_text()
        self.assertIn("FUSE Dependency Missing", output)
        self.assertIn("libfuse", output)

    @patch("subprocess.run")
    def test_run_cli_foreground_passthrough_skips_guide(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        target = ResolvedTarget(
            name="echo",
            target_type="binary",
            exec_cmd=["echo"],
            is_gui=False,
        )

        _run_cli_foreground(target, ["hello", "world"], self.console)

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["echo", "hello", "world"])
        output = self.console.export_text()
        self.assertIn("▶ Running: echo hello world", output)

    @patch("ezcli_app.run_cli.Confirm.ask", return_value=True)
    @patch("subprocess.run")
    def test_run_cli_foreground_permission_denied_elevation(self, mock_run, mock_confirm):
        mock_run.return_value = MagicMock(returncode=126)

        target = ResolvedTarget(
            name="dmidecode",
            target_type="binary",
            exec_cmd=["dmidecode"],
            is_gui=False,
        )

        with patch("ezcli_app.elevation.elevated_run_command", return_value=(True, "DMI data", "")) as mock_elev:
            _run_cli_foreground(target, [], self.console)
            mock_elev.assert_called_once()
            output = self.console.export_text()
            self.assertIn("DMI data", output)

    @patch("ezcli_app.run_cli.resolve_target")
    def test_run_cli_run_not_found(self, mock_resolve):
        mock_resolve.return_value = (None, [], "Not found")

        run_cli_run(["unknown_tool_xyz"], console=self.console)
        output = self.console.export_text()
        self.assertIn("Application Not Found", output)
        self.assertIn("ez package-search unknown_tool_xyz", output)

    @patch("ezcli_app.run_cli.Prompt.ask", return_value="1")
    @patch("subprocess.Popen")
    @patch("ezcli_app.run_cli.resolve_target")
    def test_run_cli_run_multiple_flatpak_candidates(self, mock_resolve, mock_popen, mock_prompt):
        # Fix 4: Ambiguous Flatpak candidates presents selection menu
        mock_resolve.return_value = (
            None,
            [
                ("Firefox", "org.mozilla.firefox", "Web Browser"),
                ("Firefox Developer", "org.mozilla.FirefoxDev", "Dev Browser"),
            ],
            "",
        )

        proc_mock = MagicMock()
        proc_mock.communicate.side_effect = subprocess.TimeoutExpired(cmd=["flatpak"], timeout=0.3)
        proc_mock.pid = 4321
        mock_popen.return_value = proc_mock

        run_cli_run(["firefox"], console=self.console)

        output = self.console.export_text()
        self.assertIn("Multiple Flatpak applications found matching", output)
        self.assertIn("org.mozilla.firefox", output)
        self.assertIn("Launched Firefox in the background", output)

    @patch("ezcli_app.run_cli.Confirm.ask", return_value=False)
    def test_handle_chmod_declined_binary_returns_false(self, mock_confirm):
        test_file = os.path.join(self.temp_dir.name, "my_bin")
        with open(test_file, "w") as f:
            f.write("BINARY DATA")
        os.chmod(test_file, 0o644)

        target = ResolvedTarget(
            name="my_bin",
            target_type="binary",
            exec_cmd=[test_file],
            file_path=test_file,
            is_executable=False,
            needs_chmod=True,
        )

        res = _handle_chmod(target, self.console)
        self.assertFalse(res)
        self.assertIn("Execution cancelled", self.console.export_text())

    @patch("ezcli_app.run_cli.Confirm.ask")
    @patch("os.chmod")
    def test_handle_chmod_permission_error_elevated_success(self, mock_chmod, mock_confirm):
        mock_chmod.side_effect = PermissionError("Permission denied")
        # Ask to chmod -> True, Ask to elevate -> True
        mock_confirm.side_effect = [True, True]

        test_file = os.path.join(self.temp_dir.name, "protected_script.sh")
        with open(test_file, "w") as f:
            f.write("#!/bin/bash\n")

        target = ResolvedTarget(
            name="protected_script.sh",
            target_type="script",
            exec_cmd=[test_file],
            file_path=test_file,
            is_executable=False,
            needs_chmod=True,
        )

        with patch("ezcli_app.elevation.elevated_run_command", return_value=(True, "", "")) as mock_elev:
            res = _handle_chmod(target, self.console)
            self.assertTrue(res)
            mock_elev.assert_called_once()
            self.assertIn("administrator privileges", self.console.export_text())

    @patch("ezcli_app.run_cli.Prompt.ask", return_value="")
    def test_run_cli_run_no_args_cancelled(self, mock_prompt):
        run_cli_run([], console=self.console)
        self.assertIn("Run cancelled", self.console.export_text())

    @patch("ezcli_app.run_cli.Prompt.ask", return_value="echo hello")
    @patch("ezcli_app.run_cli.resolve_target")
    @patch("subprocess.run")
    def test_run_cli_run_prompt_input_success(self, mock_run, mock_resolve, mock_prompt):
        mock_resolve.return_value = (
            ResolvedTarget(name="echo", target_type="binary", exec_cmd=["echo"]),
            [],
            "",
        )
        mock_run.return_value = MagicMock(returncode=0)

        run_cli_run([], console=self.console)
        mock_run.assert_called_once()
        self.assertIn("▶ Running: echo hello", self.console.export_text())

    @patch("ezcli_app.explorer.explorer_app.run_file_picker", return_value="/tmp/script.sh")
    @patch("ezcli_app.run_cli.resolve_target")
    @patch("subprocess.run")
    def test_run_cli_run_file_picker(self, mock_run, mock_resolve, mock_picker):
        mock_resolve.return_value = (
            ResolvedTarget(name="script.sh", target_type="script", exec_cmd=["/tmp/script.sh"]),
            [],
            "",
        )
        mock_run.return_value = MagicMock(returncode=0)

        run_cli_run(["choose-directory"], console=self.console)
        mock_picker.assert_called_once()
        mock_resolve.assert_called_once_with("/tmp/script.sh", cwd=os.getcwd())

    @patch("ezcli_app.run_cli.Confirm.ask", return_value=True)
    @patch("ezcli_app.run_cli.run_guided_form", return_value=["mytool", "--flag"])
    @patch("ezcli_app.run_cli.parse_help_text")
    @patch("ezcli_app.run_cli.safe_probe_help", return_value="Usage: mytool\n--flag")
    @patch("subprocess.run")
    def test_run_cli_foreground_usage_error_fallback_retries(
        self, mock_run, mock_probe, mock_parse, mock_guide, mock_confirm
    ):
        # First run fails with code 2 (usage error), second run succeeds
        mock_run.side_effect = [MagicMock(returncode=2), MagicMock(returncode=0)]
        mock_parse.return_value = [HelpOption(flags=["--flag"], name="flag", option_type="boolean")]

        target = ResolvedTarget(
            name="mytool",
            target_type="binary",
            exec_cmd=["mytool"],
            is_gui=False,
        )

        with patch("ezcli_app.run_cli._extract_options_for_cli", return_value=[]):
            _run_cli_foreground(target, [], self.console)

        self.assertEqual(mock_run.call_count, 2)
        output = self.console.export_text()
        self.assertIn("Command Notice", output)
        self.assertIn("▶ Running: mytool --flag", output)


if __name__ == "__main__":
    unittest.main()
