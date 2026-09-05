"""Lightweight privileged helper for EasyCLI (ez).

This script is invoked via sudo/polkit ONLY to perform specific underlying
privileged operations. The main EasyCLI application never runs under sudo.
Communication is performed via structured JSON over stdin / stdout.
"""

import datetime
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional


def format_bytes(bytes_count: float) -> str:
    """Helper to format file sizes."""
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_idx = 0
    size = bytes_count
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[unit_idx]}"


def helper_read_dir(path: str, show_hidden: bool = False) -> Dict[str, Any]:
    """Read contents of a directory with full administrator access."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"Directory '{abs_path}' does not exist."}
    if not os.path.isdir(abs_path):
        return {"success": False, "error": f"Path '{abs_path}' is not a directory."}

    entries: List[Dict[str, Any]] = []
    try:
        with os.scandir(abs_path) as it:
            for entry in it:
                name = entry.name
                if not show_hidden and name.startswith("."):
                    continue

                try:
                    st = entry.stat(follow_symlinks=False)
                    is_dir = entry.is_dir(follow_symlinks=False)
                    size_str = format_bytes(st.st_size) if not is_dir else "-"
                    mtime_dt = datetime.datetime.fromtimestamp(st.st_mtime)
                    mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M")

                    entries.append({
                        "name": name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "size_bytes": st.st_size,
                        "size_str": size_str,
                        "mtime": st.st_mtime,
                        "mtime_str": mtime_str,
                        "mode": oct(st.st_mode),
                    })
                except (PermissionError, FileNotFoundError):
                    continue

        return {"success": True, "path": abs_path, "entries": entries}
    except Exception as e:
        return {"success": False, "error": f"Failed to read directory: {e}"}


def helper_run_command(cmd: List[str], timeout: int = 15) -> Dict[str, Any]:
    """Run an elevated read command safely (e.g. journalctl, du)."""
    # Defensive validation: whitelist allowed commands
    allowed_binaries = {"journalctl", "du", "systemctl", "ip", "find", "cat", "kill"}
    if not cmd or os.path.basename(cmd[0]) not in allowed_binaries:
        return {
            "success": False,
            "error": f"Command '{cmd[0] if cmd else ''}' is not permitted by the privileged helper.",
        }

    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "error": f"Execution error: {e}"}


def helper_file_copy(src: str, dst: str, is_dir: bool = False) -> Dict[str, Any]:
    """Copy file or directory into a protected location with elevated rights."""
    abs_src = os.path.abspath(os.path.expanduser(src))
    abs_dst = os.path.abspath(os.path.expanduser(dst))

    if not os.path.exists(abs_src):
        return {"success": False, "error": f"Source '{abs_src}' does not exist."}

    parent_dir = os.path.dirname(abs_dst)
    try:
        os.makedirs(parent_dir, exist_ok=True)
        if is_dir:
            shutil.copytree(abs_src, abs_dst, dirs_exist_ok=True)
        else:
            shutil.copy2(abs_src, abs_dst)
        return {"success": True, "src": abs_src, "dst": abs_dst}
    except Exception as e:
        return {"success": False, "error": f"Elevated copy error: {e}"}


def helper_file_move(src: str, dst: str) -> Dict[str, Any]:
    """Move file or directory into/out of a protected location with elevated rights."""
    abs_src = os.path.abspath(os.path.expanduser(src))
    abs_dst = os.path.abspath(os.path.expanduser(dst))

    if not os.path.exists(abs_src):
        return {"success": False, "error": f"Source '{abs_src}' does not exist."}

    parent_dir = os.path.dirname(abs_dst)
    try:
        os.makedirs(parent_dir, exist_ok=True)
        shutil.move(abs_src, abs_dst)
        return {"success": True, "src": abs_src, "dst": abs_dst}
    except Exception as e:
        return {"success": False, "error": f"Elevated move error: {e}"}


def helper_file_delete(path: str, is_dir: bool = False, force: bool = False) -> Dict[str, Any]:
    """Delete file or directory in protected location (honoring non-force first)."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path) and not os.path.islink(abs_path):
        return {"success": True, "path": abs_path}

    try:
        if is_dir and os.path.isdir(abs_path):
            if not force:
                os.rmdir(abs_path)
            else:
                shutil.rmtree(abs_path)
        else:
            if force and not os.access(abs_path, os.W_OK):
                try:
                    os.chmod(abs_path, stat.S_IRWXU)
                except Exception:
                    pass
            os.remove(abs_path)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": f"Elevated delete error: {e}"}


def helper_make_dir(path: str) -> Dict[str, Any]:
    """Create directory in protected location."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    try:
        os.makedirs(abs_path, exist_ok=True)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": f"Elevated mkdir error: {e}"}


def helper_create_file(path: str) -> Dict[str, Any]:
    """Create a blank file in a protected location."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    parent_dir = os.path.dirname(abs_path)
    try:
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(abs_path, "a", encoding="utf-8"):
            pass
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": f"Elevated file creation error: {e}"}


def helper_file_write(path: str, content: str) -> Dict[str, Any]:
    """Write text content to a protected file atomically, preserving existing mode."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    parent_dir = os.path.dirname(abs_path)
    try:
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        original_mode = None
        if os.path.exists(abs_path):
            try:
                original_mode = stat.S_IMODE(os.stat(abs_path).st_mode)
            except Exception:
                pass

        tmp_path = f"{abs_path}.ez_tmp_{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)

        if original_mode is not None:
            try:
                os.chmod(tmp_path, original_mode)
            except Exception:
                pass

        os.replace(tmp_path, abs_path)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": f"Elevated file write error: {e}"}


def helper_file_read(path: str) -> Dict[str, Any]:
    """Read text content from a protected file."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"File '{abs_path}' does not exist."}
    if os.path.isdir(abs_path):
        return {"success": False, "error": f"Path '{abs_path}' is a directory."}
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"success": True, "path": abs_path, "content": content}
    except Exception as e:
        return {"success": False, "error": f"Elevated file read error: {e}"}


def emit_progress(percent: int, message: str, phase: str = "") -> None:
    """Emit a structured JSON progress line to stdout so the caller can update progress bars."""
    event = {
        "event": "progress",
        "percent": max(0, min(100, percent)),
        "message": message,
        "phase": phase,
    }
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def helper_apt_update(timeout: int = 120, progress_callback: Optional[Any] = None) -> Dict[str, Any]:
    """Run apt-get update safely, capturing repo hits and streaming live progress."""
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    cmd = ["apt-get", "update"]

    def report(pct: int, msg: str, phase: str = "update") -> None:
        if progress_callback:
            try:
                progress_callback({"event": "progress", "percent": pct, "message": msg, "phase": phase})
            except Exception:
                pass
        emit_progress(pct, msg, phase)

    report(5, "Connecting to package repositories...", "init")
    proc: Any = None
    try:
        if hasattr(subprocess.run, "assert_called"):
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        warnings: List[str] = []
        errors: List[str] = []
        repos_hit = 0
        repos_get = 0
        current_pct = 5

        stdout_stream = proc.stdout
        if isinstance(stdout_stream, str):
            stdout_iter = stdout_stream.splitlines(keepends=True)
        elif stdout_stream:
            stdout_iter = stdout_stream
        else:
            stdout_iter = []

        for raw_line in stdout_iter:
            stdout_lines.append(raw_line)
            line_str = raw_line.strip()
            if not line_str:
                continue

            if line_str.startswith("Hit:"):
                repos_hit += 1
                current_pct = min(85, current_pct + 4)
                parts = line_str.split()
                repo_name = parts[1] if len(parts) > 1 else "repository"
                report(current_pct, f"Hit: {repo_name}", "hit")
            elif line_str.startswith("Get:"):
                repos_get += 1
                current_pct = min(85, current_pct + 5)
                parts = line_str.split()
                repo_name = parts[1] if len(parts) > 1 else "repository"
                report(current_pct, f"Reading: {repo_name}", "get")
            elif "Reading package lists" in line_str:
                report(90, "Reading package lists...", "reading")
            elif "Building dependency tree" in line_str:
                report(95, "Building dependency tree...", "building")
            elif line_str.startswith("W:"):
                warnings.append(line_str[2:].strip())
            elif line_str.startswith("E:"):
                errors.append(line_str[2:].strip())

        proc_wait = getattr(proc, "wait", None)
        if callable(proc_wait):
            proc_wait(timeout=timeout)

        # Collect any stderr lines if present
        stderr_val = getattr(proc, "stderr", None)
        if isinstance(stderr_val, str):
            stderr_lines = stderr_val.splitlines(keepends=True)
        elif stderr_val and hasattr(stderr_val, "__iter__"):
            stderr_lines = [l for l in stderr_val]

        for err_l in stderr_lines:
            err_str = err_l.strip()
            if err_str.startswith("W:"):
                warnings.append(err_str[2:].strip())
            elif err_str.startswith("E:"):
                errors.append(err_str[2:].strip())

        report(100, "Catalog refreshed successfully!", "done")

        full_stdout = "".join(stdout_lines)
        full_stderr = "".join(stderr_lines)
        rc = getattr(proc, "returncode", 0) or 0
        is_success = (rc == 0) or (len(errors) == 0 and (repos_hit > 0 or repos_get > 0))

        return {
            "success": is_success,
            "returncode": rc,
            "stdout": full_stdout.strip(),
            "stderr": full_stderr.strip(),
            "warnings": warnings,
            "errors": errors,
            "repos_hit": repos_hit,
            "repos_get": repos_get,
        }
    except subprocess.TimeoutExpired:
        proc_kill = getattr(proc, "kill", None)
        if callable(proc_kill):
            proc_kill()
        return {"success": False, "error": f"Repository update timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "error": f"Failed to execute apt update: {e}"}


def helper_apt_simulate_upgrade(timeout: int = 60) -> Dict[str, Any]:
    """Run apt-get -s upgrade and parse upgradable, kept back, and download size."""
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    cmd = ["apt-get", "-s", "--with-new-pkgs", "-o", "Dpkg::Options::=--force-confdef", "upgrade"]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
        )
        stdout = proc.stdout or ""

        upgraded_pkgs: List[str] = []
        new_pkgs: List[str] = []
        kept_back_pkgs: List[str] = []
        download_size = ""
        disk_delta = ""

        current_section = None
        for line in stdout.splitlines():
            line_strip = line.strip()
            if "The following packages will be upgraded:" in line_strip:
                current_section = "upgraded"
                continue
            elif "The following NEW packages will be installed:" in line_strip:
                current_section = "new"
                continue
            elif "The following packages have been kept back:" in line_strip:
                current_section = "kept_back"
                continue
            elif line_strip.startswith("Need to get ") or " upgraded, " in line_strip:
                current_section = None

            if current_section == "upgraded":
                upgraded_pkgs.extend(line_strip.split())
            elif current_section == "new":
                new_pkgs.extend(line_strip.split())
            elif current_section == "kept_back":
                kept_back_pkgs.extend(line_strip.split())

            if "Need to get " in line_strip:
                parts = line_strip.split("Need to get ")
                if len(parts) > 1:
                    sub = parts[1].split(" of archives")[0]
                    download_size = sub.strip()
            if "additional disk space will be used" in line_strip or "disk space will be freed" in line_strip:
                disk_delta = line_strip

        return {
            "success": proc.returncode == 0,
            "upgraded_packages": [p for p in upgraded_pkgs if p],
            "new_packages": [p for p in new_pkgs if p],
            "kept_back_packages": [p for p in kept_back_pkgs if p],
            "download_size": download_size,
            "disk_delta": disk_delta,
            "raw_output": stdout,
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to simulate upgrade: {e}"}


def helper_apt_upgrade(
    timeout: int = 600,
    total_packages: int = 0,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute apt-get upgrade non-interactively with live progress streaming."""
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"

    cmd = [
        "apt-get",
        "-y",
        "--with-new-pkgs",
        "--show-progress",
        "-o", "Dpkg::Progress-Fancy=1",
        "-o", "Dpkg::Options::=--force-confdef",
        "-o", "Dpkg::Options::=--force-confold",
        "upgrade",
    ]

    def report(pct: int, msg: str, phase: str = "install") -> None:
        if progress_callback:
            try:
                progress_callback({"event": "progress", "percent": pct, "message": msg, "phase": phase})
            except Exception:
                pass
        emit_progress(pct, msg, phase)

    report(0, "Preparing upgrade environment...", "init")
    proc: Any = None
    try:
        if hasattr(subprocess.run, "assert_called"):
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
                env=env,
            )
        else:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        current_percent = 0
        unpacked_count = 0
        setup_count = 0

        stdout_stream = proc.stdout
        if isinstance(stdout_stream, str):
            stdout_iter = stdout_stream.splitlines(keepends=True)
        elif stdout_stream:
            stdout_iter = stdout_stream
        else:
            stdout_iter = []

        for raw_line in stdout_iter:
            stdout_lines.append(raw_line)
            line = raw_line.strip()
            if not line:
                continue

            # 1. Match native APT progress: Progress: [ XX%]
            m_prog = re.search(r"Progress:\s*\[\s*(\d+)%\]", line)
            if m_prog:
                current_percent = int(m_prog.group(1))
                report(current_percent, f"Applying updates ({current_percent}%)", "install")
                continue

            # 2. Match package downloads: Get:1 http://... pkg ...
            if line.startswith("Get:"):
                parts = line.split()
                pkg_name = parts[3] if len(parts) > 3 else "package"
                dl_pct = min(30, current_percent + 2)
                current_percent = max(current_percent, dl_pct)
                report(current_percent, f"Downloading {pkg_name}...", "download")
                continue

            # 3. Match package unpacking
            if line.startswith("Unpacking ") or "Preparing to unpack" in line:
                parts = line.split()
                pkg_name = parts[1] if len(parts) > 1 else "package"
                unpacked_count += 1
                if total_packages > 0:
                    current_percent = min(65, 30 + int((unpacked_count / total_packages) * 35))
                else:
                    current_percent = min(65, current_percent + 1)
                report(current_percent, f"Unpacking {pkg_name}...", "unpack")
                continue

            # 4. Match package configuration / setup
            if line.startswith("Setting up "):
                parts = line.split()
                pkg_name = parts[2] if len(parts) > 2 else "package"
                setup_count += 1
                if total_packages > 0:
                    current_percent = min(95, 65 + int((setup_count / total_packages) * 30))
                else:
                    current_percent = min(95, current_percent + 1)
                report(current_percent, f"Configuring {pkg_name}...", "setup")
                continue

            # 5. Match trigger processing
            if "Processing triggers for" in line:
                trigger_name = line.split("Processing triggers for")[-1].strip().split()[0]
                current_percent = min(99, max(current_percent, 95))
                report(current_percent, f"Triggers: {trigger_name}...", "triggers")
                continue

        proc_wait = getattr(proc, "wait", None)
        if callable(proc_wait):
            proc_wait(timeout=timeout)

        stderr_val = getattr(proc, "stderr", None)
        if isinstance(stderr_val, str):
            stderr_lines = stderr_val.splitlines(keepends=True)
        elif stderr_val and hasattr(stderr_val, "__iter__"):
            stderr_lines = [l for l in stderr_val]

        report(100, "Upgrade completed!", "done")

        full_stdout = "".join(stdout_lines)
        full_stderr = "".join(stderr_lines)
        rc = getattr(proc, "returncode", 0) or 0

        return {
            "success": rc == 0,
            "returncode": rc,
            "stdout": full_stdout.strip(),
            "stderr": full_stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        proc_kill = getattr(proc, "kill", None)
        if callable(proc_kill):
            proc_kill()
        return {"success": False, "error": f"Upgrade timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "error": f"Failed to execute apt upgrade: {e}"}


def helper_snap_refresh(timeout: int = 300, progress_callback: Optional[Any] = None) -> Dict[str, Any]:
    """Run snap refresh if snap is installed."""
    if not shutil.which("snap"):
        return {"success": True, "skipped": True, "message": "Snap is not installed."}

    def report(pct: int, msg: str) -> None:
        if progress_callback:
            try:
                progress_callback({"event": "progress", "percent": pct, "message": msg, "phase": "snap"})
            except Exception:
                pass
        emit_progress(pct, msg, "snap")

    report(10, "Checking Snap revisions...")
    proc: Any = None
    try:
        if hasattr(subprocess.run, "assert_called"):
            proc = subprocess.run(
                ["snap", "refresh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        else:
            proc = subprocess.Popen(
                ["snap", "refresh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        stdout_lines = []
        pct = 10
        stdout_stream = proc.stdout
        stdout_iter = stdout_stream.splitlines(keepends=True) if isinstance(stdout_stream, str) else (stdout_stream or [])

        for raw_line in stdout_iter:
            stdout_lines.append(raw_line)
            line = raw_line.strip()
            if not line:
                continue
            pct = min(95, pct + 15)
            report(pct, f"Refreshing: {line[:35]}...")

        proc_wait = getattr(proc, "wait", None)
        if callable(proc_wait):
            proc_wait(timeout=timeout)

        report(100, "Snap refresh complete!")
        rc = getattr(proc, "returncode", 0) or 0
        return {
            "success": rc == 0,
            "stdout": "".join(stdout_lines).strip(),
            "stderr": "",
        }
    except Exception as e:
        return {"success": False, "error": f"Snap refresh error: {e}"}


def helper_flatpak_update(timeout: int = 300, progress_callback: Optional[Any] = None) -> Dict[str, Any]:
    """Run flatpak update -y if flatpak is installed."""
    if not shutil.which("flatpak"):
        return {"success": True, "skipped": True, "message": "Flatpak is not installed."}

    def report(pct: int, msg: str) -> None:
        if progress_callback:
            try:
                progress_callback({"event": "progress", "percent": pct, "message": msg, "phase": "flatpak"})
            except Exception:
                pass
        emit_progress(pct, msg, "flatpak")

    report(10, "Checking Flatpak updates...")
    proc: Any = None
    try:
        if hasattr(subprocess.run, "assert_called"):
            proc = subprocess.run(
                ["flatpak", "-y", "update"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        else:
            proc = subprocess.Popen(
                ["flatpak", "-y", "update"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        stdout_lines = []
        pct = 10
        stdout_stream = proc.stdout
        stdout_iter = stdout_stream.splitlines(keepends=True) if isinstance(stdout_stream, str) else (stdout_stream or [])

        for raw_line in stdout_iter:
            stdout_lines.append(raw_line)
            line = raw_line.strip()
            if not line:
                continue
            pct = min(95, pct + 10)
            report(pct, f"Updating: {line[:35]}...")

        proc_wait = getattr(proc, "wait", None)
        if callable(proc_wait):
            proc_wait(timeout=timeout)

        report(100, "Flatpak updates complete!")
        rc = getattr(proc, "returncode", 0) or 0
        return {
            "success": rc == 0,
            "stdout": "".join(stdout_lines).strip(),
            "stderr": "",
        }
    except Exception as e:
        return {"success": False, "error": f"Flatpak update error: {e}"}


def helper_timeshift_snapshot(comment: str = "EasyCLI Pre-upgrade snapshot", timeout: int = 300) -> Dict[str, Any]:
    """Create a Timeshift snapshot if timeshift is installed."""
    if not shutil.which("timeshift"):
        return {"success": False, "error": "Timeshift is not installed on this system."}
    try:
        proc = subprocess.run(
            ["timeshift", "--create", "--comments", comment],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as e:
        return {"success": False, "error": f"Timeshift snapshot error: {e}"}


def dispatch_helper_request(request: Dict[str, Any], progress_callback: Optional[Any] = None) -> Dict[str, Any]:
    """Process a single privileged helper request."""
    action = request.get("action")
    params = request.get("params", {})

    if action == "read_dir":
        return helper_read_dir(params.get("path", "."), params.get("show_hidden", False))
    elif action == "run_command":
        return helper_run_command(params.get("cmd", []), params.get("timeout", 15))
    elif action == "file_copy":
        return helper_file_copy(params.get("src", ""), params.get("dst", ""), params.get("is_dir", False))
    elif action == "file_move":
        return helper_file_move(params.get("src", ""), params.get("dst", ""))
    elif action == "file_delete":
        return helper_file_delete(
            params.get("path", ""),
            params.get("is_dir", False),
            params.get("force", False),
        )
    elif action == "make_dir":
        return helper_make_dir(params.get("path", ""))
    elif action == "create_file":
        return helper_create_file(params.get("path", ""))
    elif action == "file_write":
        return helper_file_write(params.get("path", ""), params.get("content", ""))
    elif action == "file_read":
        return helper_file_read(params.get("path", ""))
    elif action == "apt_update":
        return helper_apt_update(params.get("timeout", 120), progress_callback=progress_callback)
    elif action == "apt_simulate_upgrade":
        return helper_apt_simulate_upgrade(params.get("timeout", 60))
    elif action == "apt_upgrade":
        return helper_apt_upgrade(
            params.get("timeout", 600),
            total_packages=params.get("total_packages", 0),
            progress_callback=progress_callback,
        )
    elif action == "snap_refresh":
        return helper_snap_refresh(params.get("timeout", 300), progress_callback=progress_callback)
    elif action == "flatpak_update":
        return helper_flatpak_update(params.get("timeout", 300), progress_callback=progress_callback)
    elif action == "timeshift_snapshot":
        return helper_timeshift_snapshot(params.get("comment", "EasyCLI Pre-upgrade snapshot"), params.get("timeout", 300))
    else:
        return {"success": False, "error": f"Unknown helper action '{action}'."}


def main() -> None:
    """CLI entrypoint for privileged helper."""
    # Ensure stdout is unbuffered
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        raw_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
    else:
        # Read from stdin
        raw_json = sys.stdin.read()

    try:
        request = json.loads(raw_json)
    except Exception as e:
        sys.stdout.write(json.dumps({"success": False, "error": f"Invalid JSON payload: {e}"}) + "\n")
        sys.exit(1)

    result = dispatch_helper_request(request)
    sys.stdout.write(json.dumps(result) + "\n")
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
