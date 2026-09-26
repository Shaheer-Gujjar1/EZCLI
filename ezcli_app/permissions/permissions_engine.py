"""Backend engine for inspecting and modifying file/directory permissions and ownership."""

from dataclasses import dataclass
import grp
import os
import pwd
import stat
from typing import Optional, Tuple

from ..elevation import elevated_run_command


@dataclass
class FilePermissions:
    """Represents the complete permission state of a file or directory."""
    path: str
    name: str
    is_dir: bool
    owner_r: bool
    owner_w: bool
    owner_x: bool
    group_r: bool
    group_w: bool
    group_x: bool
    other_r: bool
    other_w: bool
    other_x: bool
    owner_name: str
    group_name: str
    octal: str
    symbolic: str
    is_dangerous: bool = False
    danger_reason: str = ""


def calculate_octal(
    u_r: bool, u_w: bool, u_x: bool,
    g_r: bool, g_w: bool, g_x: bool,
    o_r: bool, o_w: bool, o_x: bool,
) -> str:
    """Calculate 4-digit octal permission string (e.g. 0755)."""
    u = (4 if u_r else 0) + (2 if u_w else 0) + (1 if u_x else 0)
    g = (4 if g_r else 0) + (2 if g_w else 0) + (1 if g_x else 0)
    o = (4 if o_r else 0) + (2 if o_w else 0) + (1 if o_x else 0)
    return f"0{u}{g}{o}"


def calculate_symbolic(
    is_dir: bool,
    u_r: bool, u_w: bool, u_x: bool,
    g_r: bool, g_w: bool, g_x: bool,
    o_r: bool, o_w: bool, o_x: bool,
) -> str:
    """Generate standard ls -l symbolic representation (e.g. -rwxr-xr-x)."""
    prefix = "d" if is_dir else "-"
    u_str = f"{'r' if u_r else '-'}{'w' if u_w else '-'}{'x' if u_x else '-'}"
    g_str = f"{'r' if g_r else '-'}{'w' if g_w else '-'}{'x' if g_x else '-'}"
    o_str = f"{'r' if o_r else '-'}{'w' if o_w else '-'}{'x' if o_x else '-'}"
    return f"{prefix}{u_str}{g_str}{o_str}"


def check_dangerous_permissions(
    u_r: bool, u_w: bool, u_x: bool,
    g_r: bool, g_w: bool, g_x: bool,
    o_r: bool, o_w: bool, o_x: bool,
    is_dir: bool = False,
) -> Tuple[bool, str]:
    """Check for dangerous combinations such as 0777 or world-writable files."""
    octal = calculate_octal(u_r, u_w, u_x, g_r, g_w, g_x, o_r, o_w, o_x)
    raw_octal = octal.lstrip("0") or "0"

    if o_w:
        if raw_octal == "777":
            return True, "🚨 DANGEROUS (0777): Anyone or any process on this system can read, modify, or execute this!"
        elif raw_octal == "666":
            return True, "⚠️ WORLD-WRITABLE (0666): Anyone on this computer can alter or delete this file."
        else:
            return True, f"⚠️ SECURITY RISK: Public write enabled ({octal}). Any unprivileged process can modify this file."

    if is_dir and not u_x:
        return True, "⚠️ CAUTION: Directory requires Execute permission for you to enter and open files inside."

    return False, ""


def explain_role_permissions(r: bool, w: bool, x: bool, is_dir: bool) -> str:
    """Generate a friendly plain-English description for a single role's permissions."""
    if is_dir:
        if r and w and x:
            return "Full access: list files, add or delete contents, and enter folder"
        elif r and not w and x:
            return "Can view contents and open folder (cannot add or delete files)"
        elif not r and w and x:
            return "Can enter folder and add files (cannot list existing contents)"
        elif r and w and not x:
            return "Can list and modify files, but cannot enter or navigate into folder"
        elif r and not w and not x:
            return "Can list file names only (cannot open or enter folder)"
        elif not r and not w and x:
            return "Can enter folder if exact filename is known (cannot browse)"
        elif not r and w and not x:
            return "Drop-box only: can write files without seeing contents"
        else:
            return "No access (completely locked out)"
    else:
        if r and w and x:
            return "Full access: can view, edit, and run as a program/script"
        elif r and w and not x:
            return "Can view and edit/modify (cannot run as program)"
        elif r and not w and x:
            return "Can view and run as program (read-only, cannot edit)"
        elif r and not w and not x:
            return "Read-only: can view, but cannot edit or run"
        elif not r and w and x:
            return "Can modify and execute, but cannot read content"
        elif not r and w and not x:
            return "Write-only: can modify or append, cannot read content"
        elif not r and not w and x:
            return "Execute-only: can run as program, cannot read or edit"
        else:
            return "No access (completely locked out)"


def explain_permissions(
    is_dir: bool,
    u_r: bool, u_w: bool, u_x: bool,
    g_r: bool, g_w: bool, g_x: bool,
    o_r: bool, o_w: bool, o_x: bool,
    group_name: str = "group",
) -> Tuple[str, str, str]:
    """Return plain-English explanations for Owner, Group, and Everyone Else."""
    owner_desc = explain_role_permissions(u_r, u_w, u_x, is_dir)
    group_desc = explain_role_permissions(g_r, g_w, g_x, is_dir)
    others_desc = explain_role_permissions(o_r, o_w, o_x, is_dir)
    return owner_desc, group_desc, others_desc


def get_preset_name(octal: str, is_dir: bool) -> str:
    """Identify matching common preset name for a given octal code."""
    raw = octal.lstrip("0") or "0"
    if is_dir:
        presets = {
            "700": "🔒 Private (Only Me)",
            "755": "📂 Standard Folder",
            "775": "👥 Team Shared Folder",
            "555": "🛡️ Read-Only Locked Folder",
            "777": "⚠️ Full Access (Open)",
        }
    else:
        presets = {
            "600": "🔒 Private (Only Me)",
            "644": "📄 Standard Document",
            "755": "⚡ Runnable Script / App",
            "664": "👥 Team Shared File",
            "444": "🛡️ Read-Only Locked",
            "777": "⚠️ Full Access (Open)",
        }
    return presets.get(raw, "⚙️ Custom Settings")


def get_file_permissions(path: str) -> FilePermissions:
    """Read and parse permissions and ownership for a given file or directory."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    st = os.stat(abs_path)
    is_dir = stat.S_ISDIR(st.st_mode)

    owner_r = bool(st.st_mode & stat.S_IRUSR)
    owner_w = bool(st.st_mode & stat.S_IWUSR)
    owner_x = bool(st.st_mode & stat.S_IXUSR)

    group_r = bool(st.st_mode & stat.S_IRGRP)
    group_w = bool(st.st_mode & stat.S_IWGRP)
    group_x = bool(st.st_mode & stat.S_IXGRP)

    other_r = bool(st.st_mode & stat.S_IROTH)
    other_w = bool(st.st_mode & stat.S_IWOTH)
    other_x = bool(st.st_mode & stat.S_IXOTH)

    try:
        owner_name = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner_name = str(st.st_uid)

    try:
        group_name = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group_name = str(st.st_gid)

    octal = calculate_octal(owner_r, owner_w, owner_x, group_r, group_w, group_x, other_r, other_w, other_x)
    symbolic = calculate_symbolic(is_dir, owner_r, owner_w, owner_x, group_r, group_w, group_x, other_r, other_w, other_x)
    is_dang, dang_reason = check_dangerous_permissions(
        owner_r, owner_w, owner_x, group_r, group_w, group_x, other_r, other_w, other_x, is_dir=is_dir
    )

    return FilePermissions(
        path=abs_path,
        name=os.path.basename(abs_path) or abs_path,
        is_dir=is_dir,
        owner_r=owner_r,
        owner_w=owner_w,
        owner_x=owner_x,
        group_r=group_r,
        group_w=group_w,
        group_x=group_x,
        other_r=other_r,
        other_w=other_w,
        other_x=other_x,
        owner_name=owner_name,
        group_name=group_name,
        octal=octal,
        symbolic=symbolic,
        is_dangerous=is_dang,
        danger_reason=dang_reason,
    )


def apply_permissions(
    path: str,
    octal: str,
    new_owner: Optional[str] = None,
    new_group: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Apply chmod and chown to target file/folder.
    Attempts unprivileged execution first, falling back cleanly to the elevation layer if needed.
    """
    abs_path = os.path.abspath(os.path.expanduser(path))
    int_mode = int(octal, 8)

    # 1. Attempt chmod
    chmod_needed = True
    try:
        os.chmod(abs_path, int_mode)
        chmod_needed = False
    except (PermissionError, OSError):
        pass

    if chmod_needed:
        success, out, err = elevated_run_command(
            cmd=["chmod", octal.lstrip("0") or "0", abs_path],
            reason=f"Apply permissions {octal} to '{os.path.basename(abs_path)}'",
            task_description="Change File Permissions (chmod)",
        )
        if not success:
            return False, f"Failed to change permissions: {err}"

    # 2. Attempt chown if owner/group change requested
    if new_owner or new_group:
        owner_group_str = f"{new_owner or ''}:{new_group or ''}".strip(":")
        chown_needed = True
        try:
            uid = pwd.getpwnam(new_owner).pw_uid if new_owner else -1
            gid = grp.getgrnam(new_group).gr_gid if new_group else -1
            os.chown(abs_path, uid, gid)
            chown_needed = False
        except (PermissionError, OSError, KeyError):
            pass

        if chown_needed:
            success, out, err = elevated_run_command(
                cmd=["chown", owner_group_str, abs_path],
                reason=f"Change ownership of '{os.path.basename(abs_path)}' to {owner_group_str}",
                task_description="Change File Ownership (chown)",
            )
            if not success:
                return False, f"Permissions applied, but failed to change ownership: {err}"

    return True, f"Successfully updated permissions for '{os.path.basename(abs_path)}' to {octal}."
