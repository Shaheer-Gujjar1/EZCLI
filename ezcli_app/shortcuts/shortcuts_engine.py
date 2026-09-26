"""Backend engine for managing shell command shortcuts (persisted in shell config).

CRITICAL REQUIREMENT: User-facing text must NEVER use the word 'aliases'.
All user-facing concepts are termed 'Shortcuts' or 'Command Shortcuts'.
"""

from dataclasses import dataclass
import os
import re
import shutil
from typing import List, Optional, Tuple


START_MARKER = "# >>> EasyCLI Shortcuts >>>"
END_MARKER = "# <<< EasyCLI Shortcuts <<<"


@dataclass
class ShortcutItem:
    """Represents a custom terminal command shortcut."""
    name: str
    command: str
    is_managed: bool = False
    source: str = "Shell Config"


def get_shell_rc_path() -> str:
    """Determine the user's active shell configuration file."""
    shell_env = os.environ.get("SHELL", "").lower()
    home = os.path.expanduser("~")

    if "zsh" in shell_env:
        return os.path.join(home, ".zshrc")
    elif "fish" in shell_env:
        return os.path.join(home, ".config", "fish", "config.fish")
    else:
        return os.path.join(home, ".bashrc")


def ensure_backup_created(rc_path: str) -> bool:
    """Create an automatic backup copy before modifying the shell configuration for the first time."""
    backup_path = f"{rc_path}.ezcli.bak"
    if not os.path.exists(backup_path) and os.path.exists(rc_path):
        try:
            shutil.copy2(rc_path, backup_path)
            return True
        except Exception:
            return False
    return os.path.exists(backup_path)


def parse_shortcuts(rc_path: str) -> List[ShortcutItem]:
    """Parse all shortcuts defined in the shell configuration."""
    if not os.path.exists(rc_path):
        return []

    shortcuts: List[ShortcutItem] = []
    in_managed_block = False

    alias_pattern = re.compile(r"^\s*alias\s+([a-zA-Z0-9_\-\.]+)=(['\"])(.*?)\2\s*(?:#.*)?$")
    loose_pattern = re.compile(r"^\s*alias\s+([a-zA-Z0-9_\-\.]+)=(.*?)\s*(?:#.*)?$")

    try:
        with open(rc_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if stripped == START_MARKER:
                    in_managed_block = True
                    continue
                elif stripped == END_MARKER:
                    in_managed_block = False
                    continue

                m = alias_pattern.match(stripped)
                if m:
                    name = m.group(1)
                    cmd = m.group(3)
                    shortcuts.append(
                        ShortcutItem(
                            name=name,
                            command=cmd,
                            is_managed=in_managed_block,
                            source="EasyCLI Managed" if in_managed_block else "Custom Shell Setting",
                        )
                    )
                else:
                    m2 = loose_pattern.match(stripped)
                    if m2:
                        name = m2.group(1)
                        cmd = m2.group(2).strip("'\"")
                        shortcuts.append(
                            ShortcutItem(
                                name=name,
                                command=cmd,
                                is_managed=in_managed_block,
                                source="EasyCLI Managed" if in_managed_block else "Custom Shell Setting",
                            )
                        )
    except Exception:
        pass

    return shortcuts


def validate_shortcut_name(name: str) -> Tuple[bool, str]:
    """Validate that the shortcut name is safe and valid."""
    clean = name.strip()
    if not clean:
        return False, "Shortcut name cannot be empty."
    if " " in clean or "\t" in clean:
        return False, "Shortcut name cannot contain spaces."
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", clean):
        return False, "Shortcut name contains invalid characters. Use letters, numbers, hyphens, or underscores."

    # Prevent shadowing critical shell builtins accidentally
    dangerous = {"cd", "exit", "sudo", "su", "sh", "bash", "source", "exec", "return"}
    if clean in dangerous:
        return False, f"Shortcut name '{clean}' is a critical shell built-in and cannot be overridden."

    return True, ""


def add_or_update_shortcut(rc_path: str, name: str, command: str) -> Tuple[bool, str]:
    """Add a new shortcut or update an existing one in the shell configuration."""
    is_valid, msg = validate_shortcut_name(name)
    if not is_valid:
        return False, msg

    ensure_backup_created(rc_path)

    clean_name = name.strip()
    clean_cmd = command.strip().replace("'", "'\\''")
    new_line = f"alias {clean_name}='{clean_cmd}'"

    lines: List[str] = []
    if os.path.exists(rc_path):
        with open(rc_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

    # Locate managed block if it exists
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == START_MARKER:
            start_idx = i
        elif line.strip() == END_MARKER:
            end_idx = i

    if start_idx != -1 and end_idx != -1:
        # Update within existing block
        block_lines = lines[start_idx + 1:end_idx]
        found = False
        new_block = []
        for bl in block_lines:
            if re.match(rf"^\s*alias\s+{re.escape(clean_name)}=", bl.strip()):
                new_block.append(f"{new_line}\n")
                found = True
            else:
                new_block.append(bl)

        if not found:
            new_block.append(f"{new_line}\n")

        lines = lines[:start_idx + 1] + new_block + lines[end_idx:]
    else:
        # Append new managed block at end of rc file
        lines.append("\n" + START_MARKER + "\n")
        lines.append(f"{new_line}\n")
        lines.append(END_MARKER + "\n")

    try:
        with open(rc_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True, f"Shortcut '{clean_name}' saved to {os.path.basename(rc_path)}."
    except Exception as e:
        return False, f"Failed to save shortcut: {e}"


def delete_shortcut(rc_path: str, name: str) -> Tuple[bool, str]:
    """Delete a shortcut from the shell configuration file."""
    if not os.path.exists(rc_path):
        return False, "Shell configuration file does not exist."

    ensure_backup_created(rc_path)
    clean_name = name.strip()

    with open(rc_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    new_lines: List[str] = []
    deleted = False

    for line in lines:
        if re.match(rf"^\s*alias\s+{re.escape(clean_name)}=", line.strip()):
            deleted = True
            continue
        new_lines.append(line)

    if not deleted:
        return False, f"Shortcut '{clean_name}' was not found in {os.path.basename(rc_path)}."

    try:
        with open(rc_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True, f"Shortcut '{clean_name}' removed."
    except Exception as e:
        return False, f"Failed to remove shortcut: {e}"
