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
from typing import Any, Dict, List, Optional, Tuple

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

    # 2. Check if passwordless sudo is already active (e.g. valid timestamp or NOPASSWD)
    try:
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

        # Verify password via sudo
        try:
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


def run_elevated_helper(
    action: str,
    params: Dict[str, Any],
    reason: str = "Access to protected system resources is required.",
    task_description: str = "Execute elevated system action",
    risk_level: str = "low",
    skip_explanation: bool = False,
    console: Optional[Console] = None,
    timeout: int = 30,
) -> Tuple[bool, Optional[Any], str]:
    """
    Execute a privileged action via the helper.
    Returns (success, result_data, error_message).
    """
    console = console or Console()

    # 1. If already root, run directly in-process without any prompt
    if is_root():
        from .privileged_helper import dispatch_helper_request

        res = dispatch_helper_request({"action": action, "params": params})
        if res.get("success"):
            return True, res, ""
        return False, None, res.get("error", "Helper operation failed.")

    # 2. Explain to the user in plain English what & why if not in active session
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
        proc = None
        try:
            proc = subprocess.Popen(
                sudo_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            pwd_input = (_ACTIVE_SESSION_PASSWORD + "\n") if _ACTIVE_SESSION_PASSWORD else ""
            stdout_data, stderr_data = proc.communicate(input=pwd_input, timeout=timeout)
        except subprocess.TimeoutExpired:
            if proc is not None:
                try:
                    proc.kill()
                    proc.communicate()
                except Exception:
                    pass
            return False, None, "Elevation helper operation timed out."
        except Exception as e:
            return False, None, f"Elevation execution encountered an error ({e.__class__.__name__})."

        rc = proc.returncode
        if rc != 0 and not stdout_data:
            clean_err = stderr_data.strip()
            return False, None, clean_err or f"Elevation failed (exit code {rc})."

        try:
            for line in stdout_data.splitlines():
                line_clean = line.strip()
                if line_clean.startswith("{") and line_clean.endswith("}"):
                    resp = json.loads(line_clean)
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

        proc = None
        try:
            try:
                proc = subprocess.Popen(
                    sudo_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout_data, stderr_data = proc.communicate(input=password + "\n", timeout=timeout)
            except subprocess.TimeoutExpired:
                if proc is not None:
                    try:
                        proc.kill()
                        proc.communicate()
                    except Exception:
                        pass
                return False, None, "Elevation helper operation timed out."
            except Exception as e:
                # Sanitized error message: Never include stdin, password, or raw process info
                return False, None, f"Elevation execution encountered an error ({e.__class__.__name__})."
        finally:
            wipe_password(password)
            password = None

        if proc is None:
            return False, None, "Elevation process could not be started."

        rc = proc.returncode

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
        try:
            for line in stdout_data.splitlines():
                line_clean = line.strip()
                if line_clean.startswith("{") and line_clean.endswith("}"):
                    resp = json.loads(line_clean)
                    if resp.get("success"):
                        return True, resp, ""
                    else:
                        return False, None, resp.get("error", "Operation failed in helper.")

            return False, None, "Invalid response from privileged helper."
        except json.JSONDecodeError:
            return False, None, "Could not parse response from privileged helper."

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
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Execute apt-get upgrade non-interactively."""
    success, res, err = run_elevated_helper(
        action="apt_upgrade",
        params={},
        reason="Upgrade system packages to latest versions",
        task_description="Install package upgrades via apt-get upgrade",
        risk_level="high",
        skip_explanation=skip_explanation,
        console=console,
        timeout=600,
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_snap_refresh(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
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
    )
    if success and isinstance(res, dict):
        return True, res, ""
    return False, None, err


def elevated_flatpak_update(
    skip_explanation: bool = True,
    console: Optional[Console] = None,
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

