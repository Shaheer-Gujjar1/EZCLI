"""Target detection and resolution engine for 'ez run'.

Resolves execution targets in strict priority order:
1. Existing file path (Executable binary, AppImage, Script with interpreter).
2. Application name:
   a. Binary on PATH (cross-referencing desktop entries for GUI classification)
   b. Snap application via 'snap run'
   c. Flatpak application via fuzzy matching (interactive menu if multiple candidates)
   d. Desktop entry via 'gio launch' or 'gtk-launch'
"""

from dataclasses import dataclass
import os
import re
import shutil
import subprocess
from typing import List, Optional, Sequence, Tuple


@dataclass
class ResolvedTarget:
    """Represents a resolved software or script execution target."""

    name: str
    target_type: str  # "script", "binary", "appimage", "snap", "flatpak", "desktop"
    exec_cmd: List[str]
    file_path: Optional[str] = None
    interpreter: Optional[str] = None
    is_gui: bool = False
    is_executable: bool = True
    needs_chmod: bool = False
    description: str = ""


# Standard directories where .desktop files live
XDG_DESKTOP_DIRS = [
    os.path.expanduser("~/.local/share/applications"),
    "/usr/local/share/applications",
    "/usr/share/applications",
    "/var/lib/snapd/desktop/applications",
    os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
    "/var/lib/flatpak/exports/share/applications",
]


def get_all_desktop_dirs() -> List[str]:
    """Return all valid desktop search directories on this system."""
    dirs: List[str] = []
    env_xdg = os.environ.get("XDG_DATA_DIRS", "")
    if env_xdg:
        for d in env_xdg.split(":"):
            app_dir = os.path.join(d.strip(), "applications")
            if os.path.isdir(app_dir) and app_dir not in dirs:
                dirs.append(app_dir)

    for d in XDG_DESKTOP_DIRS:
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return dirs


def parse_desktop_file(filepath: str) -> Optional[dict]:
    """Parse key properties from a .desktop file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return None

    in_entry = False
    data: dict = {
        "name": "",
        "exec": "",
        "terminal": False,
        "nodisplay": False,
        "type": "Application",
    }

    for line in lines:
        line_str = line.strip()
        if line_str == "[Desktop Entry]":
            in_entry = True
            continue
        elif line_str.startswith("[") and in_entry:
            # Entered another section like [Desktop Action ...]
            break

        if in_entry and "=" in line_str:
            k, v = line_str.split("=", 1)
            k = k.strip().lower()
            v = v.strip()
            if k == "name" and not data["name"]:
                data["name"] = v
            elif k == "exec" and not data["exec"]:
                data["exec"] = v
            elif k == "terminal":
                data["terminal"] = v.lower() == "true"
            elif k == "nodisplay":
                data["nodisplay"] = v.lower() == "true"
            elif k == "type":
                data["type"] = v

    if data["type"].lower() != "application" or data["nodisplay"]:
        return None
    return data


def find_desktop_entry_for_binary(bin_path: str) -> Optional[Tuple[str, bool]]:
    """Check whether a binary on PATH corresponds to an installed desktop application.

    Returns:
        (desktop_filepath, is_terminal) or None
    """
    bin_name = os.path.basename(bin_path).lower()
    for d in get_all_desktop_dirs():
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for entry in entries:
            if not entry.endswith(".desktop"):
                continue
            fpath = os.path.join(d, entry)
            parsed = parse_desktop_file(fpath)
            if not parsed or not parsed["exec"]:
                continue

            # Extract first token of Exec=
            exec_bin = parsed["exec"].split()[0]
            # Strip quotes or path
            clean_exec = os.path.basename(exec_bin.strip("\"'")).lower()
            if clean_exec == bin_name:
                return fpath, parsed["terminal"]

            # Also match entry basename (e.g. gimp.desktop matches gimp)
            base_entry = entry[:-8].lower()
            if base_entry == bin_name:
                return fpath, parsed["terminal"]
    return None


def detect_desktop_entry_by_name(name: str) -> Optional[Tuple[str, str, bool]]:
    """Find a .desktop file by application name or desktop file base name.

    Returns:
        (desktop_filepath, app_display_name, is_terminal) or None
    """
    clean_name = name.strip().lower()
    for d in get_all_desktop_dirs():
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for entry in entries:
            if not entry.endswith(".desktop"):
                continue
            fpath = os.path.join(d, entry)
            parsed = parse_desktop_file(fpath)
            if not parsed:
                continue

            base_entry = entry[:-8].lower()
            app_name = parsed["name"].strip()
            if base_entry == clean_name or app_name.lower() == clean_name:
                return fpath, app_name or base_entry, parsed["terminal"]

    # Partial substring match if no exact match
    for d in get_all_desktop_dirs():
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for entry in entries:
            if not entry.endswith(".desktop"):
                continue
            fpath = os.path.join(d, entry)
            parsed = parse_desktop_file(fpath)
            if not parsed:
                continue
            app_name = parsed["name"].strip()
            if clean_name in app_name.lower() or clean_name in entry.lower():
                return fpath, app_name or entry[:-8], parsed["terminal"]
    return None


def detect_script_interpreter(filepath: str) -> Tuple[Optional[str], str]:
    """Detect appropriate interpreter for a script based on extension or shebang.

    Returns:
        (interpreter_command, script_type_label)
    """
    lower = filepath.lower()
    ext_map = {
        ".py": ("python3", "Python script"),
        ".sh": ("bash", "Shell script"),
        ".bash": ("bash", "Bash script"),
        ".js": ("node", "Node.js script"),
        ".mjs": ("node", "Node.js module"),
        ".rb": ("ruby", "Ruby script"),
        ".pl": ("perl", "Perl script"),
        ".php": ("php", "PHP script"),
        ".zsh": ("zsh", "Zsh script"),
    }
    for ext, (interp, label) in ext_map.items():
        if lower.endswith(ext):
            return interp, label

    # Shebang check
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline().strip()
        if first_line.startswith("#!"):
            shebang = first_line[2:].strip()
            if "python" in shebang:
                return "python3", "Python script"
            elif "bash" in shebang:
                return "bash", "Bash script"
            elif "sh" in shebang:
                return "sh", "Shell script"
            elif "node" in shebang:
                return "node", "Node.js script"
            elif "ruby" in shebang:
                return "ruby", "Ruby script"
            elif "perl" in shebang:
                return "perl", "Perl script"
            elif "php" in shebang:
                return "php", "PHP script"
            elif "zsh" in shebang:
                return "zsh", "Zsh script"
    except Exception:
        pass

    return None, "Executable script"


def detect_snap_app(name: str) -> Optional[Tuple[str, bool]]:
    """Check if name is an installed Snap package.

    Returns:
        (snap_name, is_gui) or None
    """
    if not shutil.which("snap"):
        return None

    try:
        res = subprocess.run(
            ["snap", "list", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        if res.returncode != 0 or not res.stdout:
            return None

        lines = res.stdout.strip().splitlines()
        if len(lines) >= 2:
            snap_pkg = lines[1].split()[0].strip()
            # Check if desktop entry exists for snap to see if it is GUI
            is_gui = False
            desktop_match = find_desktop_entry_for_binary(snap_pkg)
            if desktop_match:
                is_gui = not desktop_match[1]
            elif os.path.exists(f"/var/lib/snapd/desktop/applications/{snap_pkg}_{snap_pkg}.desktop"):
                is_gui = True
            return snap_pkg, is_gui
    except Exception:
        pass
    return None


def detect_flatpak_candidates(name: str) -> List[Tuple[str, str, str]]:
    """Query installed Flatpaks and return matching candidate applications.

    Returns list of: (display_name, application_id, description)
    """
    if not shutil.which("flatpak"):
        return []

    clean_name = name.strip().lower()
    try:
        res = subprocess.run(
            ["flatpak", "list", "--app", "--columns=name,application,description"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=4,
        )
        if res.returncode != 0 or not res.stdout:
            return []

        candidates: List[Tuple[str, str, str]] = []
        for line in res.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                disp_name = parts[0].strip()
                app_id = parts[1].strip()
                desc = parts[2].strip() if len(parts) > 2 else ""

                # Exact or fuzzy match
                if (
                    clean_name == disp_name.lower()
                    or clean_name == app_id.lower()
                    or clean_name in disp_name.lower()
                    or clean_name in app_id.lower()
                ):
                    candidates.append((disp_name, app_id, desc))
        return candidates
    except Exception:
        return []


def resolve_target(
    target_str: str,
    cwd: Optional[str] = None,
) -> Tuple[Optional[ResolvedTarget], List[Tuple[str, str, str]], str]:
    """Resolve a user-provided target string into an actionable ResolvedTarget.

    Returns:
        (resolved_target, flatpak_candidates, error_msg)
    """
    cleaned = (target_str or "").strip()
    if not cleaned:
        return None, [], "No target specified."

    effective_cwd = os.path.abspath(cwd or os.getcwd())

    # =========================================================================
    # 1. Existing File Path Resolution
    # =========================================================================
    file_candidate = os.path.abspath(os.path.expanduser(cleaned))
    if not os.path.isabs(cleaned) and not cleaned.startswith("~"):
        file_candidate = os.path.join(effective_cwd, cleaned)

    if os.path.isdir(file_candidate):
        return None, [], f"'{cleaned}' is a directory, not an executable file or application."

    if os.path.isfile(file_candidate):
        base_name = os.path.basename(file_candidate)
        is_exec = os.access(file_candidate, os.X_OK)

        # 1a. AppImage
        if base_name.lower().endswith(".appimage"):
            return (
                ResolvedTarget(
                    name=base_name,
                    target_type="appimage",
                    exec_cmd=[file_candidate],
                    file_path=file_candidate,
                    is_gui=True,  # AppImages are typically GUI
                    is_executable=is_exec,
                    needs_chmod=not is_exec,
                    description="AppImage application",
                ),
                [],
                "",
            )

        # 1b. Known script types or shebang
        interpreter, script_label = detect_script_interpreter(file_candidate)
        if interpreter:
            cmd = [file_candidate] if is_exec else [interpreter, file_candidate]
            return (
                ResolvedTarget(
                    name=base_name,
                    target_type="script",
                    exec_cmd=cmd,
                    file_path=file_candidate,
                    interpreter=shutil.which(interpreter) or interpreter,
                    is_gui=False,
                    is_executable=is_exec,
                    needs_chmod=not is_exec,
                    description=script_label,
                ),
                [],
                "",
            )

        # 1c. Native binary / Other executable
        if is_exec:
            return (
                ResolvedTarget(
                    name=base_name,
                    target_type="binary",
                    exec_cmd=[file_candidate],
                    file_path=file_candidate,
                    is_gui=False,
                    is_executable=True,
                    needs_chmod=False,
                    description="Executable binary",
                ),
                [],
                "",
            )

        # 1d. Non-executable file without known interpreter
        return (
            ResolvedTarget(
                name=base_name,
                target_type="binary",
                exec_cmd=[file_candidate],
                file_path=file_candidate,
                is_gui=False,
                is_executable=False,
                needs_chmod=True,
                description="Unrecognized file",
            ),
            [],
            "",
        )

    # =========================================================================
    # 2. Installed Application Resolution by Name
    # =========================================================================

    # 2a. Binary on PATH
    bin_path = shutil.which(cleaned)
    if bin_path:
        # Fix 1: Cross-reference desktop entry for GUI classification
        desktop_info = find_desktop_entry_for_binary(bin_path)
        is_gui = False
        if desktop_info:
            _, is_terminal = desktop_info
            is_gui = not is_terminal  # Terminal=false means GUI!

        return (
            ResolvedTarget(
                name=os.path.basename(bin_path),
                target_type="binary",
                exec_cmd=[bin_path],
                file_path=bin_path,
                is_gui=is_gui,
                is_executable=True,
                needs_chmod=False,
                description="GUI application on PATH" if is_gui else "CLI binary on PATH",
            ),
            [],
            "",
        )

    # 2b. Snap Application
    snap_match = detect_snap_app(cleaned)
    if snap_match:
        snap_name, is_gui = snap_match
        return (
            ResolvedTarget(
                name=snap_name,
                target_type="snap",
                exec_cmd=["snap", "run", snap_name],
                is_gui=is_gui,
                is_executable=True,
                description=f"Snap package ({snap_name})",
            ),
            [],
            "",
        )

    # 2c. Flatpak Application (Fix 4: Ambiguity handling)
    flatpak_candidates = detect_flatpak_candidates(cleaned)
    if len(flatpak_candidates) == 1:
        disp_name, app_id, desc = flatpak_candidates[0]
        return (
            ResolvedTarget(
                name=disp_name,
                target_type="flatpak",
                exec_cmd=["flatpak", "run", app_id],
                is_gui=True,
                is_executable=True,
                description=desc or f"Flatpak application ({app_id})",
            ),
            [],
            "",
        )
    elif len(flatpak_candidates) > 1:
        # Multiple candidates found! Return candidate list for selection menu
        return None, flatpak_candidates, ""

    # 2d. Desktop Entry
    desktop_match = detect_desktop_entry_by_name(cleaned)
    if desktop_match:
        desktop_path, app_name, is_terminal = desktop_match
        # Preferred runner: gio launch if available, else gtk-launch
        launch_cmd = ["gio", "launch", desktop_path] if shutil.which("gio") else ["gtk-launch", os.path.basename(desktop_path)[:-8]]
        return (
            ResolvedTarget(
                name=app_name,
                target_type="desktop",
                exec_cmd=launch_cmd,
                file_path=desktop_path,
                is_gui=not is_terminal,
                is_executable=True,
                description="Desktop application",
            ),
            [],
            "",
        )

    # =========================================================================
    # 3. Not Found
    # =========================================================================
    return None, [], f"Target '{cleaned}' not found as a local file, PATH binary, Snap, Flatpak, or desktop application."
