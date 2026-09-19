"""
Core native snapshot engine for Time Machine.

Implements standalone, lightweight system restore points using standard Linux tools
(rsync with --link-dest hardlink deduplication or BTRFS subvolumes) without requiring
any external applications or heavy packages.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_SNAPSHOT_BASE = "/var/backups/ez-time-machine"
SNAPSHOTS_DIR_NAME = "snapshots"

# Default exclusions for full root snapshot to avoid virtual filesystems, caches, and user data
SYSTEM_EXCLUDES = [
    "/proc/*",
    "/sys/*",
    "/dev/*",
    "/run/*",
    "/tmp/*",
    "/var/tmp/*",
    "/lost+found",
    "/media/*",
    "/mnt/*",
    "/var/cache/*",
    "/var/backups/ez-time-machine/*",
    "/home/*",
    "/root/.cache/*",
    "/swapfile",
]

# Exclusions for config profile
CONFIG_EXCLUDES = [
    "*.log",
    "*.log.*",
    "/etc/shadow-",
    "/etc/gshadow-",
    "/var/cache/*",
    "/var/tmp/*",
]


@dataclass
class SnapshotMetadata:
    id: str
    created_at: str
    timestamp: float
    comment: str
    profile: str  # 'config' or 'system'
    size_bytes: int
    distro: str
    kernel: str
    packages_count: int
    status: str = "complete"


def get_base_dir() -> Path:
    """Return base directory for Time Machine storage."""
    custom = os.environ.get("EZ_TIME_MACHINE_DIR")
    if custom:
        return Path(custom)
    return Path(DEFAULT_SNAPSHOT_BASE)


def get_snapshots_dir() -> Path:
    """Return directory where snapshots reside."""
    return get_base_dir() / SNAPSHOTS_DIR_NAME


def format_snapshot_id(dt: Optional[datetime.datetime] = None) -> str:
    """Generate clean sortable snapshot ID."""
    dt = dt or datetime.datetime.now()
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


def format_human_size(size_bytes: int) -> str:
    """Format byte size into clean human-readable string."""
    if size_bytes < 0:
        return "-"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def detect_system_info() -> Tuple[str, str, int]:
    """Return (distro_name, kernel_version, package_count)."""
    distro = "Linux"
    kernel = "Unknown"
    pkg_count = 0

    try:
        kernel = subprocess.check_output(["uname", "-r"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        pass

    try:
        from ..distro import detect_distro
        d = detect_distro()
        distro = f"{d.name} {d.version_id}".strip()
    except Exception:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break

    try:
        proc = subprocess.run(
            ["dpkg-query", "-f", ".\n", "-W"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if proc.returncode == 0:
            pkg_count = proc.stdout.count(".")
    except Exception:
        pass

    return distro, kernel, pkg_count


def list_local_snapshots(snapshots_dir: Optional[Path] = None) -> List[SnapshotMetadata]:
    """
    Read and return all valid snapshots sorted from newest to oldest.
    """
    base = snapshots_dir or get_snapshots_dir()
    if not base.exists():
        return []

    snapshots: List[SnapshotMetadata] = []
    try:
        for entry in os.scandir(base):
            if not entry.is_dir():
                continue
            meta_file = Path(entry.path) / "snapshot.json"
            if not meta_file.exists():
                continue
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = SnapshotMetadata(
                    id=data.get("id", entry.name),
                    created_at=data.get("created_at", ""),
                    timestamp=data.get("timestamp", 0.0),
                    comment=data.get("comment", ""),
                    profile=data.get("profile", "config"),
                    size_bytes=data.get("size_bytes", 0),
                    distro=data.get("distro", "Linux"),
                    kernel=data.get("kernel", ""),
                    packages_count=data.get("packages_count", 0),
                    status=data.get("status", "complete"),
                )
                snapshots.append(meta)
            except Exception:
                continue
    except (PermissionError, OSError):
        return []

    # Sort descending by timestamp (newest first)
    snapshots.sort(key=lambda s: s.timestamp, reverse=True)
    return snapshots


def get_latest_snapshot(snapshots_dir: Optional[Path] = None) -> Optional[SnapshotMetadata]:
    """Return the most recent snapshot if any exist."""
    snapshots = list_local_snapshots(snapshots_dir)
    return snapshots[0] if snapshots else None


def calculate_dir_apparent_size(dir_path: Path) -> int:
    """Calculate total apparent byte size of a directory."""
    total = 0
    try:
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.lstat(fp).st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def get_storage_stats(base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get disk space metrics for the filesystem housing the Time Machine directory.
    """
    target = base_dir or get_base_dir()
    check_path = target if target.exists() else Path("/")
    try:
        st = os.statvfs(check_path)
        total_bytes = st.f_blocks * st.f_frsize
        avail_bytes = st.f_bavail * st.f_frsize
        used_bytes = total_bytes - avail_bytes
        percent = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0
        return {
            "path": str(target),
            "total_bytes": total_bytes,
            "avail_bytes": avail_bytes,
            "used_bytes": used_bytes,
            "used_percent": round(percent, 1),
            "total_human": format_human_size(total_bytes),
            "avail_human": format_human_size(avail_bytes),
            "used_human": format_human_size(used_bytes),
        }
    except Exception as e:
        return {
            "path": str(target),
            "total_bytes": 0,
            "avail_bytes": 0,
            "used_bytes": 0,
            "used_percent": 0.0,
            "total_human": "-",
            "avail_human": "-",
            "used_human": "-",
            "error": str(e),
        }


def create_snapshot(
    comment: str = "",
    profile: str = "config",
    snapshots_dir: Optional[Path] = None,
    progress_callback: Optional[Any] = None,
) -> Tuple[bool, Optional[SnapshotMetadata], str]:
    """
    Create a new restore point using rsync with hardlink deduplication.
    """
    base_snapshots = snapshots_dir or get_snapshots_dir()
    base_snapshots.mkdir(parents=True, exist_ok=True)

    prev_snapshot = get_latest_snapshot(base_snapshots)

    now = datetime.datetime.now()
    snap_id = format_snapshot_id(now)
    snap_dir = base_snapshots / snap_id
    data_dir = snap_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    distro, kernel, pkg_count = detect_system_info()
    display_comment = comment.strip() or ("System Configuration Restore Point" if profile == "config" else "Full System Restore Point")

    # Hardlink deduplication against most recent snapshot if compatible profile
    link_args: List[str] = []
    if prev_snapshot and prev_snapshot.profile == profile:
        prev_data = base_snapshots / prev_snapshot.id / "data"
        if prev_data.exists():
            link_args = [f"--link-dest={prev_data.resolve()}"]

    try:
        if profile == "config":
            # 1. Capture system configuration trees (/etc and /usr/local)
            for src, rel_dest in [("/etc", "etc"), ("/usr/local", "usr/local")]:
                if not os.path.exists(src):
                    continue
                dest_path = data_dir / rel_dest
                dest_path.mkdir(parents=True, exist_ok=True)

                cmd = ["rsync", "-aAX", "--delete"]
                if link_args:
                    prev_src_data = base_snapshots / prev_snapshot.id / "data" / rel_dest
                    if prev_src_data.exists():
                        cmd.append(f"--link-dest={prev_src_data.resolve()}")

                for exc in CONFIG_EXCLUDES:
                    cmd.extend(["--exclude", exc])

                cmd.extend([f"{src}/", str(dest_path)])
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode != 0 and proc.returncode != 24:  # 24 = vanished files ok
                    return False, None, f"Failed syncing {src}: {proc.stderr.strip()}"

            # 2. Package database state
            try:
                dpkg_status = Path("/var/lib/dpkg/status")
                if dpkg_status.exists():
                    dpkg_dest_dir = data_dir / "var/lib/dpkg"
                    dpkg_dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(dpkg_status), str(dpkg_dest_dir / "status"))
            except (PermissionError, OSError):
                pass

            # 3. Boot config if present
            try:
                grub_cfg = Path("/boot/grub/grub.cfg")
                if grub_cfg.exists():
                    boot_dest = data_dir / "boot/grub"
                    boot_dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(grub_cfg), str(boot_dest / "grub.cfg"))
            except (PermissionError, OSError):
                pass



        else:
            # Full System Root Profile
            cmd = ["rsync", "-aAX", "--delete"]
            if link_args:
                cmd.extend(link_args)

            for exc in SYSTEM_EXCLUDES:
                cmd.extend(["--exclude", exc])

            cmd.extend(["/", str(data_dir)])
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 and proc.returncode != 24:
                return False, None, f"Failed creating root snapshot: {proc.stderr.strip()}"

        # Calculate snapshot size
        snap_size = calculate_dir_apparent_size(data_dir)

        # Write snapshot.json metadata
        meta = SnapshotMetadata(
            id=snap_id,
            created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
            timestamp=now.timestamp(),
            comment=display_comment,
            profile=profile,
            size_bytes=snap_size,
            distro=distro,
            kernel=kernel,
            packages_count=pkg_count,
            status="complete",
        )

        with open(snap_dir / "snapshot.json", "w", encoding="utf-8") as f:
            json.dump(asdict(meta), f, indent=2)

        return True, meta, ""

    except Exception as e:
        # Cleanup incomplete snapshot directory on failure
        if snap_dir.exists():
            shutil.rmtree(snap_dir, ignore_errors=True)
        return False, None, str(e)


def simulate_restore(
    snapshot_id: str,
    snapshots_dir: Optional[Path] = None,
    target_root: str = "/",
) -> Dict[str, Any]:
    """
    Simulate restoration via rsync dry-run to preview affected files.
    """
    base_snapshots = snapshots_dir or get_snapshots_dir()
    snap_dir = base_snapshots / snapshot_id
    data_dir = snap_dir / "data"
    meta_file = snap_dir / "snapshot.json"

    if not data_dir.exists() or not meta_file.exists():
        return {"success": False, "error": f"Snapshot '{snapshot_id}' not found"}

    try:
        with open(meta_file, "r") as f:
            meta = json.load(f)
        profile = meta.get("profile", "config")

        changes: List[str] = []
        files_modified = 0
        files_created = 0
        files_deleted = 0

        target_base = Path(target_root)

        if profile == "config":
            sync_pairs = [
                (data_dir / "etc", target_base / "etc"),
                (data_dir / "usr/local", target_base / "usr/local"),
            ]
            for s, d in sync_pairs:
                if not s.exists():
                    continue
                cmd = ["rsync", "-aAX", "--delete", "--dry-run", "-i", f"{s}/", f"{d}/"]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for line in proc.stdout.splitlines():
                    if not line.strip():
                        continue
                    code = line[:9]
                    fname = line[10:].strip()
                    if code.startswith("*deleting"):
                        files_deleted += 1
                        changes.append(f"(-) Delete {fname}")
                    elif ">f+++++++" in code or ">d+++++++" in code:
                        files_created += 1
                        changes.append(f"(+) Create {fname}")
                    else:
                        files_modified += 1
                        changes.append(f"(~) Modify {fname}")
        else:
            cmd = ["rsync", "-aAX", "--delete", "--dry-run", "-i"]
            for exc in SYSTEM_EXCLUDES:
                cmd.extend(["--exclude", exc])
            cmd.extend([f"{data_dir}/", f"{target_base}/"])
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                code = line[:9]
                fname = line[10:].strip()
                if code.startswith("*deleting"):
                    files_deleted += 1
                    changes.append(f"(-) Delete {fname}")
                elif ">f+++++++" in code or ">d+++++++" in code:
                    files_created += 1
                    changes.append(f"(+) Create {fname}")
                else:
                    files_modified += 1
                    changes.append(f"(~) Modify {fname}")

        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "profile": profile,
            "comment": meta.get("comment", ""),
            "created_at": meta.get("created_at", ""),
            "files_modified": files_modified,
            "files_created": files_created,
            "files_deleted": files_deleted,
            "sample_changes": changes[:25],
            "total_changes": len(changes),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def restore_snapshot(
    snapshot_id: str,
    snapshots_dir: Optional[Path] = None,
    target_root: str = "/",
) -> Tuple[bool, str]:
    """
    Restore system state from designated snapshot.
    """
    base_snapshots = snapshots_dir or get_snapshots_dir()
    snap_dir = base_snapshots / snapshot_id
    data_dir = snap_dir / "data"
    meta_file = snap_dir / "snapshot.json"

    if not data_dir.exists() or not meta_file.exists():
        return False, f"Snapshot '{snapshot_id}' not found."

    try:
        with open(meta_file, "r") as f:
            meta = json.load(f)
        profile = meta.get("profile", "config")

        target_base = Path(target_root)

        if profile == "config":
            # Restore /etc and /usr/local
            for rel in ["etc", "usr/local"]:
                src = data_dir / rel
                dest = target_base / rel
                if not src.exists():
                    continue
                dest.mkdir(parents=True, exist_ok=True)
                cmd = ["rsync", "-aAX", "--delete", f"{src}/", f"{dest}/"]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if proc.returncode != 0 and proc.returncode != 24:
                    return False, f"Restore failed on {rel}: {proc.stderr.strip()}"

            # Restore dpkg status if present
            saved_dpkg = data_dir / "var/lib/dpkg/status"
            if saved_dpkg.exists():
                dpkg_dest_dir = target_base / "var/lib/dpkg"
                dpkg_dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(saved_dpkg), str(dpkg_dest_dir / "status"))

            return True, f"System configuration restored successfully from restore point {snapshot_id}."

        else:
            # Full system restoration
            cmd = ["rsync", "-aAX", "--delete"]
            for exc in SYSTEM_EXCLUDES:
                cmd.extend(["--exclude", exc])
            cmd.extend([f"{data_dir}/", f"{target_base}/"])
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 and proc.returncode != 24:
                return False, f"System restore failed: {proc.stderr.strip()}"

            return True, f"System fully restored successfully from restore point {snapshot_id}."

    except Exception as e:
        return False, str(e)


def delete_snapshot(snapshot_id: str, snapshots_dir: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Delete a snapshot directory. Thanks to hardlinks, other snapshots remain 100% intact.
    """
    base_snapshots = snapshots_dir or get_snapshots_dir()
    snap_dir = base_snapshots / snapshot_id

    if not snap_dir.exists():
        return False, f"Snapshot '{snapshot_id}' does not exist."

    try:
        shutil.rmtree(snap_dir)
        return True, f"Restore point {snapshot_id} deleted successfully."
    except Exception as e:
        return False, str(e)

