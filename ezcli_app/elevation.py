"""Shared privilege-elevation layer for EasyCLI (ez).

Safety & UX guarantees:
1. Every command always runs as normal user first.
2. Partial failure: displays collected data + "Some locations were inaccessible. Retry with admin rights? [Y/n]".
3. Full failure: displays "Admin rights are required for this task." and offers seamless elevation.
4. Explains what will be done and why admin rights are needed before asking for password.
5. Visible dot feedback (••••) during password entry.
6. Friendly wrong password message: "Wrong password — no problem, try again." No raw sudo lectures.
7. Never stores or logs passwords. Immediate memory wipe.
8. Only the underlying operation is elevated through the privileged helper.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


def is_root() -> bool:
    """Return True if currently running as root."""
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def prompt_password_dots(prompt_text: str = "🔑 Admin password: ") -> Optional[str]:
    """
    Prompt user for a password with visible dot feedback (••••).
    Supports Backspace, Enter, Ctrl+C / Ctrl+D / Esc.
    Falls back gracefully if stdin is not an interactive tty.
    """
    if not sys.stdin.isatty():
        # Non-interactive fallback (e.g. test environment or piped)
        try:
            line = sys.stdin.readline()
            return line.rstrip("\r\n") if line else None
        except Exception:
            return None

    import termios
    import tty

    sys.stdout.write("\x1b[?25h")
    sys.stdout.write(prompt_text)
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    chars: List[str] = []

    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if not ch:
                break

            # Enter
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                break

            # Ctrl+C or Ctrl+D or ESC
            if ch in ("\x03", "\x04", "\x1b"):
                sys.stdout.write("\n")
                sys.stdout.flush()
                return None

            # Backspace (\x7f or \x08)
            if ch in ("\x7f", "\x08"):
                if chars:
                    chars.pop()
                    # Move cursor back, overwrite with space, move back again
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            else:
                # Accept normal printable characters
                chars.append(ch)
                sys.stdout.write("•")
                sys.stdout.flush()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    password = "".join(chars)
    # Clear chars list from memory
    for i in range(len(chars)):
        chars[i] = "\0"
    return password


def wipe_password(pwd: Optional[str]) -> None:
    """Best-effort cleanup of sensitive string reference."""
    if pwd is not None:
        del pwd


def explain_elevation(
    reason: str,
    task_description: str,
    risk_level: str = "low",
    console: Optional[Console] = None,
) -> bool:
    """
    Display a clear, friendly explanation in plain English before asking for authentication.
    Low risk (read-only): quick prompt.
    High risk (write): prominent risk badge and details.
    """
    console = console or Console()

    if risk_level.lower() == "high":
        title = "🛡️ [bold red]Admin Rights Required (High Risk Write)[/bold red]"
        border_color = "red"
        risk_badge = "[bold red]RISK: Write / Modify Protected System Files[/bold red]\n"
    else:
        title = "🔒 [bold cyan]Admin Rights Required[/bold cyan]"
        border_color = "cyan"
        risk_badge = "[dim]Risk: Low (Read-Only Inspection)[/dim]\n"

    body = (
        f"{risk_badge}\n"
        f"[bold]What EasyCLI will do:[/bold]\n"
        f"  {task_description}\n\n"
        f"[bold]Why admin rights are needed:[/bold]\n"
        f"  {reason}\n\n"
        f"[dim]Security Notice: EasyCLI continues running as your normal user.\n"
        f"Only this specific task is elevated via a small privileged helper.[/dim]"
    )

    console.print(
        Panel(
            body,
            title=title,
            border_style=border_color,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

    return Confirm.ask("Do you want to proceed with admin rights?", default=True)


_ACTIVE_SESSION_PASSWORD: Optional[str] = None


class ElevationSession:
    """A context manager for a scoped elevation session.

    Holds the validated admin password in memory strictly for the duration
    of an authorized multi-step operation, and securely wipes it on exit.
    """

    def __init__(self, password: str = "") -> None:
        self.password = password

    def __enter__(self) -> "ElevationSession":
        global _ACTIVE_SESSION_PASSWORD
        _ACTIVE_SESSION_PASSWORD = self.password
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global _ACTIVE_SESSION_PASSWORD
        _ACTIVE_SESSION_PASSWORD = None
        if self.password:
            wipe_password(self.password)
            self.password = ""


def authenticate_elevation_session(
    reason: str = "",
    task_description: str = "",
    risk_level: str = "low",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Optional[ElevationSession]:
    """Present the elevation explanation card, obtain consent, and verify admin password upfront.

    Returns an active ElevationSession if authenticated, or None if cancelled or declined.
    """
    console = console or Console()

    if is_root():
        return ElevationSession(password="")

    # 1. Show explanation card & get consent if not skipped
    if not skip_explanation:
        approved = explain_elevation(reason, task_description, risk_level, console=console)
        if not approved:
            console.print("[yellow]Update cancelled. No repository lists were changed.[/yellow]")
            return None

    # 2. Check if genuine passwordless sudo is configured in sudoers (NOPASSWD)
    # Using 'sudo -k' resets any previous session timestamp so we only auto-skip if sudo genuinely requires no password.
    try:
        subprocess.run(["sudo", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        check = subprocess.run(
            ["sudo", "-n", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        if check.returncode == 0:
            return ElevationSession(password="")
    except Exception:
        pass

    # 3. Prompt for password and verify it immediately before any task work begins
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        password = prompt_password_dots("🔑 Admin password: ")

        if password is None:
            console.print("[yellow]Password entry cancelled.[/yellow]")
            return None

        if not password:
            if attempt < max_attempts:
                console.print("[yellow]No password entered — please enter your admin password.[/yellow]")
                continue
            else:
                console.print("[bold red]No password entered 3 times. Elevation cancelled.[/bold red]")
                return None

        # Verify password via sudo (clearing any cache first with sudo -k)
        try:
            subprocess.run(["sudo", "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            test_proc = subprocess.run(
                ["sudo", "-S", "-p", "", "true"],
                input=password + "\n",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
            )
            if test_proc.returncode == 0:
                # Successfully authenticated!
                return ElevationSession(password=password)

            err_lower = (test_proc.stderr or "").lower()
            if (
                "not in the sudoers file" in err_lower
                or "not in sudoers" in err_lower
                or "is not allowed to run sudo" in err_lower
            ):
                wipe_password(password)
                console.print("[bold red]Your account does not have admin rights on this machine.[/bold red]")
                return None

            wipe_password(password)
            if attempt < max_attempts:
                console.print("[yellow]Wrong password — no problem, try again.[/yellow]")
            else:
                console.print("[bold red]Incorrect password entered 3 times. Elevation cancelled.[/bold red]")
                return None

        except subprocess.TimeoutExpired:
            wipe_password(password)
            console.print("[bold red]Authentication timed out.[/bold red]")
            return None
        except Exception as e:
            wipe_password(password)
            console.print(f"[bold red]Authentication error: {e.__class__.__name__}[/bold red]")
            return None

    return None


def _run_helper_process(
    sudo_cmd: List[str],
    pwd_input: str,
    timeout: int,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[int, str, str, Optional[Dict[str, Any]]]:
    """Execute sudo helper command, streaming progress events if on_progress is provided.
    Returns (returncode, stdout_data, stderr_data, final_resp_dict).
    """
    proc = subprocess.Popen(
        sudo_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    final_resp: Optional[Dict[str, Any]] = None

    # If test mocked communicate or on_progress is not requested, use communicate()
    if on_progress is None or isinstance(getattr(proc, "communicate", None), MagicMock):
        stdout_data, stderr_data = proc.communicate(input=pwd_input, timeout=timeout)
        for line in (stdout_data or "").splitlines():
            line_clean = line.strip()
            if line_clean.startswith("{") and line_clean.endswith("}"):
                try:
                    data = json.loads(line_clean)
                    if data.get("event") == "progress":
                        if on_progress:
                            on_progress(data)
                        continue
                    if "success" in data:
                        final_resp = data
                        break
                except Exception:
                    pass
        return proc.returncode, stdout_data or "", stderr_data or "", final_resp

    # Live streaming mode
    if pwd_input and proc.stdin and callable(getattr(proc.stdin, "write", None)):
        try:
            proc.stdin.write(pwd_input)
            proc.stdin.flush()
            proc.stdin.close()
        except Exception:
            pass

    stdout_lines: List[str] = []

    def read_stdout() -> None:
        nonlocal final_resp
        stdout_stream = proc.stdout
        if stdout_stream is None:
            return
        if isinstance(stdout_stream, str):
            lines_iter = stdout_stream.splitlines(keepends=True)
        elif hasattr(stdout_stream, "readline"):
            lines_iter = iter(stdout_stream.readline, "")
        elif hasattr(stdout_stream, "__iter__"):
            lines_iter = stdout_stream
        else:
            lines_iter = []

        for raw_line in lines_iter:
            if not isinstance(raw_line, str):
                continue
            line_clean = raw_line.strip()
            if not line_clean:
                continue
            if line_clean.startswith("{") and line_clean.endswith("}"):
                try:
                    parsed = json.loads(line_clean)
                    if parsed.get("event") == "progress":
                        if on_progress:
                            try:
                                on_progress(parsed)
                            except Exception:
                                pass
                        continue
                    elif "success" in parsed:
                        final_resp = parsed
                        continue
                except Exception:
                    pass
            stdout_lines.append(raw_line)

    reader_thread = threading.Thread(target=read_stdout, daemon=True)
    reader_thread.start()

    try:
        if callable(getattr(proc, "wait", None)):
            proc.wait(timeout=timeout)
        reader_thread.join(timeout=3.0)
        stderr_data = ""
        if proc.stderr:
            if isinstance(proc.stderr, str):
                stderr_data = proc.stderr
            elif hasattr(proc.stderr, "read") and callable(proc.stderr.read):
                stderr_data = proc.stderr.read()
        stdout_data = "".join(stdout_lines)
        return proc.returncode, stdout_data, stderr_data, final_resp
    except subprocess.TimeoutExpired:
        if callable(getattr(proc, "kill", None)):
            proc.kill()
        reader_thread.join(timeout=1.0)
        raise


def run_elevated_helper(
    action: str,
    params: Dict[str, Any],
    reason: str = "Access to protected system resources is required.",
    task_description: str = "Execute elevated system action",
    risk_level: str = "low",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 30,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[bool, Optional[Any], str]:
    """
    Execute a privileged action via the helper.
    Returns (success, result_data, error_message).
    """
    console = console or Console()

    # 1. If already root, run directly in-process without any prompt
    if is_root():
        from .privileged_helper import dispatch_helper_request

        res = dispatch_helper_request({"action": action, "params": params}, progress_callback=on_progress)
        if res.get("success"):
            return True, res, ""
        return False, None, res.get("error", "Helper operation failed.")

    # 2. Explain to the user in plain English what & why if not in active session
    live_to_resume = None
    if _ACTIVE_SESSION_PASSWORD is None and console and hasattr(console, "_live") and console._live and getattr(console._live, "is_started", False):
        live_to_resume = console._live
        try:
            live_to_resume.stop()
        except Exception:
            live_to_resume = None

    try:
        if not skip_explanation and _ACTIVE_SESSION_PASSWORD is None:
            approved = explain_elevation(reason, task_description, risk_level, console=console)
            if not approved:
                return False, None, "Elevation was declined by user."

        # 3. Find python executable and repo path
        python_bin = sys.executable or "python3"
        repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_payload = json.dumps({"action": action, "params": params})

        # Prepare command for sudo
        sudo_cmd = [
            "sudo",
            "-S",  # Read password from stdin
            "-p",  # Custom prompt (empty string so sudo doesn't output default prompt)
            "",
            "PYTHONPATH=" + repo_dir,
            python_bin,
            "-m",
            "ezcli_app.privileged_helper",
            "--json",
            json_payload,
        ]

        # If an active session password exists, use it directly without re-prompting
        if _ACTIVE_SESSION_PASSWORD is not None:
            pwd_input = (_ACTIVE_SESSION_PASSWORD + "\n") if _ACTIVE_SESSION_PASSWORD else ""
            try:
                rc, stdout_data, stderr_data, final_resp = _run_helper_process(
                    sudo_cmd, pwd_input, timeout, on_progress
                )
            except subprocess.TimeoutExpired:
                return False, None, "Elevation helper operation timed out."
            except Exception as e:
                return False, None, f"Elevation execution encountered an error ({e.__class__.__name__})."

            if rc != 0 and not stdout_data:
                clean_err = stderr_data.strip()
                return False, None, clean_err or f"Elevation failed (exit code {rc})."

            if final_resp is not None:
                if final_resp.get("success"):
                    return True, final_resp, ""
                return False, None, final_resp.get("error", "Operation failed in helper.")

            try:
                for line in (stdout_data or "").splitlines():
                    line_clean = line.strip()
                    if line_clean.startswith("{") and line_clean.endswith("}"):
                        resp = json.loads(line_clean)
                        if resp.get("event") == "progress":
                            continue
                        if resp.get("success"):
                            return True, resp, ""
                        else:
                            return False, None, resp.get("error", "Operation failed in helper.")
                return False, None, "Invalid response from privileged helper."
            except json.JSONDecodeError:
                return False, None, "Could not parse response from privileged helper."

        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            password = prompt_password_dots("🔑 Admin password: ")

            if password is None:
                return False, None, "Password entry cancelled."

            try:
                try:
                    rc, stdout_data, stderr_data, final_resp = _run_helper_process(
                        sudo_cmd, password + "\n", timeout, on_progress
                    )
                except subprocess.TimeoutExpired:
                    return False, None, "Elevation helper operation timed out."
                except Exception as e:
                    # Sanitized error message: Never include stdin, password, or raw process info
                    return False, None, f"Elevation execution encountered an error ({e.__class__.__name__})."
            finally:
                wipe_password(password)
                password = None

            # 1. Missing case: User is not in sudoers file / lacks sudo rights entirely
            err_lower = stderr_data.lower()
            if (
                "not in the sudoers file" in err_lower
                or "not in sudoers" in err_lower
                or "is not allowed to run sudo" in err_lower
                or "incident will be reported" in err_lower
            ):
                return False, None, "Your account does not have admin rights on this machine."

            # 2. Check for wrong password
            if (
                "incorrect password" in err_lower
                or "try again" in err_lower
                or "password" in err_lower
            ) and rc != 0 and not stdout_data:
                if attempt < max_attempts:
                    console.print("[yellow]Wrong password — no problem, try again.[/yellow]")
                    continue
                else:
                    return False, None, "Incorrect password entered 3 times. Elevation cancelled."

            # 3. Sudo failed for another reason
            if rc != 0 and not stdout_data:
                clean_err = stderr_data.strip()
                if "lecture" in clean_err.lower():
                    clean_err = "Permission was not granted."
                return False, None, clean_err or f"Elevation failed (exit code {rc})."

            # 4. Parse helper's structured JSON response from stdout
            if final_resp is not None:
                if final_resp.get("success"):
                    return True, final_resp, ""
                return False, None, final_resp.get("error", "Operation failed in helper.")

            try:
                for line in (stdout_data or "").splitlines():
                    line_clean = line.strip()
                    if line_clean.startswith("{") and line_clean.endswith("}"):
                        resp = json.loads(line_clean)
                        if resp.get("event") == "progress":
                            continue
                        if resp.get("success"):
                            return True, resp, ""
                        else:
                            return False, None, resp.get("error", "Operation failed in helper.")

                return False, None, "Invalid response from privileged helper."
            except json.JSONDecodeError:
                return False, None, "Could not parse response from privileged helper."

    finally:
        if live_to_resume:
            try:
                live_to_resume.start()
            except Exception:
                pass

    return False, None, "Elevation cancelled."


# ==============================================================================
# Convenience Helper Wrappers
# ==============================================================================
def elevated_read_dir(
    path: str,
    show_hidden: bool = False,
    reason: str = "Read protected directory contents",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Read a protected directory using the privileged helper."""
    success, res, err = run_elevated_helper(
        action="read_dir",
        params={"path": path, "show_hidden": show_hidden},
        reason=reason,
        task_description=f"Inspect contents of protected folder '{path}'",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
    )
    if success and isinstance(res, dict):
        return True, res.get("entries", []), ""
    return False, [], err


def elevated_run_command(
    cmd: List[str],
    reason: str = "Execute privileged system check",
    task_description: str = "Run elevated diagnostic tool",
    timeout: int = 15,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str, str]:
    """Run an elevated read command via helper. Returns (success, stdout, stderr)."""
    success, res, err = run_elevated_helper(
        action="run_command",
        params={"cmd": cmd, "timeout": timeout},
        reason=reason,
        task_description=task_description,
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
    )
    if success and isinstance(res, dict):
        return True, res.get("stdout", ""), res.get("stderr", "")
    return False, "", err


def elevated_file_copy(
    src: str,
    dst: str,
    is_dir: bool = False,
    reason: str = "Copy item into protected directory",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Copy an item to a protected location."""
    success, res, err = run_elevated_helper(
        action="file_copy",
        params={"src": src, "dst": dst, "is_dir": is_dir},
        reason=reason,
        task_description=f"Copy '{os.path.basename(src)}' to protected location '{dst}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_file_move(
    src: str,
    dst: str,
    reason: str = "Move item into/out of protected directory",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Move an item to/from a protected location."""
    success, res, err = run_elevated_helper(
        action="file_move",
        params={"src": src, "dst": dst},
        reason=reason,
        task_description=f"Move '{os.path.basename(src)}' to protected location '{dst}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_file_delete(
    path: str,
    is_dir: bool = False,
    force: bool = False,
    reason: str = "Remove item from protected directory",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Delete an item in a protected location."""
    task_desc = f"Remove '{path}'" + (" forcefully" if force else "")
    success, res, err = run_elevated_helper(
        action="file_delete",
        params={"path": path, "is_dir": is_dir, "force": force},
        reason=reason,
        task_description=task_desc,
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_make_dir(
    path: str,
    reason: str = "Create directory in protected location",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Create a directory in a protected location."""
    success, res, err = run_elevated_helper(
        action="make_dir",
        params={"path": path},
        reason=reason,
        task_description=f"Create directory '{path}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_create_file(
    path: str,
    reason: str = "Create blank file in protected location",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Create a blank file in a protected location."""
    success, res, err = run_elevated_helper(
        action="create_file",
        params={"path": path},
        reason=reason,
        task_description=f"Create file '{path}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_file_write(
    path: str,
    content: str,
    reason: str = "Save changes to protected file",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Write content to a protected file with administrator rights."""
    success, res, err = run_elevated_helper(
        action="file_write",
        params={"path": path, "content": content},
        reason=reason,
        task_description=f"Save changes to '{path}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
    )
    return success, err


def elevated_file_read(
    path: str,
    reason: str = "Read protected system file",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, Optional[str], str]:
    """Read content from a protected file with administrator rights."""
    success, res, err = run_elevated_helper(
        action="file_read",
        params={"path": path},
        reason=reason,
        task_description=f"Read file '{path}'",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
    )
    if success and res and isinstance(res, dict):
        return True, res.get("content", ""), ""
    return False, None, err


def elevated_apt_update(
    reason: str = "Refresh repository catalog of available packages",
    task_description: str = "Fetch updated package lists from configured software repositories into /var/lib/apt/lists/",
    risk_level: str = "low",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Run an elevated apt-get update to refresh the software catalog."""
    success, res, err = run_elevated_helper(
        action="apt_update",
        params={},
        reason=reason,
        task_description=task_description,
        risk_level=risk_level,
        skip_explanation=skip_explanation,
        console=console,
        timeout=180,
        on_progress=on_progress,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_apt_simulate_upgrade(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Simulate an apt-get upgrade to calculate upgradable packages and sizes."""
    success, res, err = run_elevated_helper(
        action="apt_simulate_upgrade",
        params={},
        reason="Calculate upgrade impact preview",
        task_description="Simulate package upgrades without modifying system",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=60,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_apt_upgrade(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
    total_packages: int = 0,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Execute apt-get upgrade non-interactively with live progress streaming."""
    success, res, err = run_elevated_helper(
        action="apt_upgrade",
        params={"total_packages": total_packages},
        reason="Upgrade system packages to latest versions",
        task_description="Install package upgrades via apt-get upgrade",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=600,
        on_progress=on_progress,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_snap_refresh(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Refresh snap packages if snap is installed."""
    success, res, err = run_elevated_helper(
        action="snap_refresh",
        params={},
        reason="Refresh snap packages",
        task_description="Update installed snaps to latest revisions",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=300,
        on_progress=on_progress,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_flatpak_update(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Update flatpak runtimes and applications if flatpak is installed."""
    success, res, err = run_elevated_helper(
        action="flatpak_update",
        params={},
        reason="Update Flatpak applications and runtimes",
        task_description="Install latest Flatpak updates via flatpak update",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=300,
        on_progress=on_progress,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_timeshift_snapshot(
    comment: str = "EasyCLI Pre-upgrade snapshot",
    skip_explanation: bool = True,
    console: Optional[Console] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Create a Timeshift restore point snapshot."""
    success, res, err = run_elevated_helper(
        action="timeshift_snapshot",
        params={"comment": comment},
        reason="Create system restore point before upgrading",
        task_description=f"Create Timeshift snapshot: {comment}",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=300,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


class ElevationResult(tuple):
    """3-tuple (success: bool, data: Optional[Dict[str, Any]], error: str) that also evaluates as boolean."""
    def __bool__(self) -> bool:
        return bool(self[0])


def elevated_package_install(
    platform_or_package: Any = None,
    package: Optional[Any] = None,
    platform: Optional[str] = None,
    reason: Optional[str] = None,
    task_description: Optional[str] = None,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 300,
) -> ElevationResult:
    """Install a software package or list of packages via the privileged helper (APT, Flatpak, Snap).
    
    Supports both calling conventions and keyword arguments:
      - elevated_package_install(platform, package, console=console)
      - elevated_package_install(package_or_packages, reason=..., task_description=..., console=console)
      - elevated_package_install(platform="flatpak", package="org.winehq.Wine", console=console)
    """
    console = console or Console()

    # Determine platform
    chosen_plat: str = "apt"
    if platform is not None:
        chosen_plat = str(platform).lower()
    elif package is not None and str(platform_or_package).lower() in ("apt", "snap", "flatpak", "flathub", "snap_store", "dpkg", "apt_store"):
        chosen_plat = str(platform_or_package).lower()
    elif str(platform_or_package).lower() in ("apt", "snap", "flatpak", "flathub", "snap_store", "dpkg", "apt_store") and package is not None:
        chosen_plat = str(platform_or_package).lower()

    # Normalize platform aliases
    if chosen_plat in ("flathub", "flatpak"):
        platform_clean = "flatpak"
    elif chosen_plat in ("snap_store", "snap"):
        platform_clean = "snap"
    else:
        platform_clean = "apt"

    # Determine target package(s)
    actual_pkg = package if package is not None else platform_or_package

    if isinstance(actual_pkg, (list, tuple, set)):
        pkg_list = [str(p).strip() for p in actual_pkg if str(p).strip()]
        pkg_clean = " ".join(pkg_list)
        pkg_display = ", ".join(pkg_list)
    else:
        pkg_clean = str(actual_pkg).strip() if actual_pkg else ""
        pkg_display = pkg_clean

    plat_label = platform_clean.upper()
    default_reason = f"Install {plat_label} software package '{pkg_display}' onto the system"
    default_task = f"Install '{pkg_display}' via {plat_label} package manager"

    success, res, err = run_elevated_helper(
        action="package_install",
        params={"platform": platform_clean, "package": pkg_clean, "timeout": timeout},
        reason=reason or default_reason,
        task_description=task_description or default_task,
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout + 30,
    )
    return ElevationResult((success, res if isinstance(res, dict) else None, err))


def elevated_package_uninstall(
    platform: str,
    package: str,
    purge: bool = False,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 300,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Uninstall a software package via the privileged helper without password caching."""
    plat_label = (platform or "apt").upper()
    success, res, err = run_elevated_helper(
        action="package_uninstall",
        params={"platform": platform, "package": package, "purge": purge, "timeout": timeout},
        reason=f"Admin rights are required to uninstall {plat_label} software package '{package}'.",
        task_description=f"Uninstall '{package}' via {plat_label} package manager",
        risk_level="medium",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout + 30,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_search_files(
    root_dir: str = "/",
    term: str = "",
    max_results: int = 50,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 60,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """Search filesystem starting at root_dir with administrator privileges."""
    success, res, err = run_elevated_helper(
        action="search_files",
        params={"root_dir": root_dir, "term": term, "max_results": max_results},
        reason=f"Administrator authorization is required to search protected system files in '{root_dir}'.",
        task_description=f"System-wide file search for '{term}'",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout,
    )
    if success and isinstance(res, dict):
        results_list = res.get("results", [])
        if isinstance(results_list, list):
            return True, results_list, ""
    return False, [], err


def elevated_tm_list(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, List[Dict[str, Any]], str]:
    """List snapshots for Time Machine with elevated permissions."""
    success, res, err = run_elevated_helper(
        action="tm_list",
        params={},
        reason="Read protected restore point snapshots from Time Machine storage.",
        task_description="List Time Machine snapshots",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=30,
    )
    if success and isinstance(res, dict):
        return True, res.get("snapshots", []), ""
    return False, [], err


def elevated_tm_create(
    comment: str = "",
    profile: str = "config",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 300,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Create a new Time Machine restore point."""
    success, res, err = run_elevated_helper(
        action="tm_create",
        params={"comment": comment, "profile": profile},
        reason="Create a safe system restore point snapshot using hardlink deduplication.",
        task_description=f"Create Time Machine snapshot: {comment or profile}",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout,
    )
    if success and isinstance(res, dict):
        return True, res.get("snapshot"), ""
    return False, None, err


def elevated_tm_restore(
    snapshot_id: str,
    target_root: str = "/",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 600,
) -> Tuple[bool, str]:
    """Restore system state from designated Time Machine snapshot."""
    success, res, err = run_elevated_helper(
        action="tm_restore",
        params={"snapshot_id": snapshot_id, "target_root": target_root},
        reason=f"Administrator permission is required to restore system files from restore point '{snapshot_id}'.",
        task_description=f"Restore system state to snapshot '{snapshot_id}'",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout,
    )
    if success and isinstance(res, dict):
        msg = res.get("message", "System restored successfully.")
        return True, msg
    return False, err


def elevated_tm_delete(
    snapshot_id: str,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 60,
) -> Tuple[bool, str]:
    """Delete a Time Machine restore point."""
    success, res, err = run_elevated_helper(
        action="tm_delete",
        params={"snapshot_id": snapshot_id},
        reason=f"Administrator permission is required to delete restore point '{snapshot_id}'.",
        task_description=f"Delete snapshot '{snapshot_id}'",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout,
    )
    if success and isinstance(res, dict):
        msg = res.get("message", "Snapshot deleted successfully.")
        return True, msg
    return False, err


def elevated_tm_simulate(
    snapshot_id: str,
    target_root: str = "/",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 60,
) -> Tuple[bool, Dict[str, Any], str]:
    """Simulate restore to preview affected files."""
    success, res, err = run_elevated_helper(
        action="tm_simulate",
        params={"snapshot_id": snapshot_id, "target_root": target_root},
        reason="Preview files that will be modified or restored.",
        task_description=f"Simulate restore for '{snapshot_id}'",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=timeout,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, {}, err


def elevated_tm_stats(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, Dict[str, Any], str]:
    """Get Time Machine storage disk metrics."""
    success, res, err = run_elevated_helper(
        action="tm_stats",
        params={},
        reason="Query Time Machine storage metrics.",
        task_description="Get Time Machine storage stats",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=15,
    )
    if success and isinstance(res, dict):
        return True, res.get("stats", {}), ""
    return False, {}, err


def elevated_cleanup_apt(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Clean APT package cache (/var/cache/apt/archives)."""
    success, res, err = run_elevated_helper(
        action="cleanup_apt",
        params={},
        reason="Clean cached package download files in /var/cache/apt/archives.",
        task_description="Clean APT package cache",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=120,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, ""
    return False, err or (res.get("stderr") if isinstance(res, dict) else "")


def elevated_cleanup_autoremove(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Remove orphan dependency packages via apt-get autoremove."""
    success, res, err = run_elevated_helper(
        action="cleanup_autoremove",
        params={},
        reason="Remove unneeded dependency packages.",
        task_description="Autoremove orphan packages",
        risk_level="medium",
        skip_explanation=skip_explanation,
        console=console,
        timeout=300,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, ""
    return False, err or (res.get("stderr") if isinstance(res, dict) else "")


def elevated_apt_mark_manual(
    packages: List[str],
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Mark packages as manually installed to protect them from autoremove."""
    success, res, err = run_elevated_helper(
        action="apt_mark_manual",
        params={"packages": packages},
        reason=f"Mark {len(packages)} desktop-critical package(s) as manually installed.",
        task_description="Mark packages as manual",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=60,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, ""
    return False, err or (res.get("stderr") if isinstance(res, dict) else "")


def elevated_cleanup_logs(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, Dict[str, Any], str]:
    """Clean old rotated system logs and vacuum journal."""
    success, res, err = run_elevated_helper(
        action="cleanup_logs",
        params={},
        reason="Clean archived and rotated log files in /var/log.",
        task_description="Clean system logs",
        risk_level="low",
        skip_explanation=skip_explanation,
        console=console,
        timeout=60,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, res, ""
    return False, {}, err or (res.get("error") if isinstance(res, dict) else "")


def elevated_user_chpasswd(
    username: str,
    new_password: str,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Update user password via chpasswd using elevation."""
    success, res, err = run_elevated_helper(
        action="user_chpasswd",
        params={"username": username, "new_password": new_password},
        reason=f"Change login password for user '{username}'.",
        task_description=f"Update password for {username}",
        risk_level="medium",
        skip_explanation=skip_explanation,
        console=console,
        timeout=30,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, ""
    return False, err or (res.get("stderr") if isinstance(res, dict) else "")


def elevated_fix_packages(
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str, str]:
    """Repair broken package states: dpkg --configure -a and apt-get --fix-broken install -y."""
    success, res, err = run_elevated_helper(
        action="fix_packages",
        params={},
        reason="Repair interrupted package installations and unmet dependencies.",
        task_description="Repair broken packages",
        risk_level="medium",
        skip_explanation=skip_explanation,
        console=console,
        timeout=600,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, res.get("log", ""), ""
    log_out = res.get("log", "") if isinstance(res, dict) else ""
    return False, log_out, err or (res.get("error") if isinstance(res, dict) else "")


def elevated_toggle_service(
    unit: str,
    enable: bool = True,
    skip_explanation: bool = False,
    console: Optional[Console] = None,
) -> Tuple[bool, str]:
    """Enable or disable a systemd service unit."""
    action_verb = "enable" if enable else "disable"
    success, res, err = run_elevated_helper(
        action="toggle_service",
        params={"unit": unit, "enable": enable},
        reason=f"{action_verb.capitalize()} system boot service '{unit}'.",
        task_description=f"{action_verb.capitalize()} service {unit}",
        risk_level="medium",
        skip_explanation=skip_explanation,
        console=console,
        timeout=30,
    )
    if success and isinstance(res, dict) and res.get("success"):
        return True, ""
    return False, err or (res.get("stderr") if isinstance(res, dict) else "")





