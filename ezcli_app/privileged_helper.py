"""Lightweight privileged helper for EasyCLI (ezcli).

This script is invoked via sudo/polkit ONLY to perform specific underlying
privileged operations. The main EasyCLI application never runs under sudo.
Communication is performed via structured JSON over stdin / stdout.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List


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
    allowed_binaries = {"journalctl", "du", "systemctl", "ip", "find", "cat"}
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


def helper_file_delete(path: str, is_dir: bool = False) -> Dict[str, Any]:
    """Delete file or directory in protected location (for undo/cleanup)."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return {"success": True, "path": abs_path}

    try:
        if is_dir and os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
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


def dispatch_helper_request(request: Dict[str, Any]) -> Dict[str, Any]:
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
        return helper_file_delete(params.get("path", ""), params.get("is_dir", False))
    elif action == "make_dir":
        return helper_make_dir(params.get("path", ""))
    elif action == "create_file":
        return helper_create_file(params.get("path", ""))
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
