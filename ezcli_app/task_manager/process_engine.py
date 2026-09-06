"""Process Engine & Categorization System for EasyCLI Task Manager."""

import os
import pwd
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from ..collectors import format_bytes


@dataclass
class ProcessItem:
    """Represents a running process with rich classification, metrics, and visual badges."""
    pid: int
    ppid: int
    user: str
    comm: str
    args: str
    name: str
    app_icon: str
    category: str  # "app", "background", "system"
    category_badge: str
    status_icon: str
    status_text: str
    is_unresponsive: bool
    unresponsive_badge: str
    cpu_percent: float
    mem_percent: float
    rss_kb: int
    rss_str: str
    stat: str
    time_str: str
    tty: str


class ProcessEngine:
    """Engine responsible for polling, parsing, categorizing, and terminating processes."""

    # Keywords that indicate background services / desktop daemons
    DAEMON_KEYWORDS: Set[str] = {
        "systemd", "dbus", "gvfs", "pipewire", "wireplumber", "pulseaudio",
        "dconf", "at-spi", "agent", "daemon", "polkit", "service-manager",
        "portal", "tracker", "gcr", "obex", "anything", "appmenu", "session",
        "ibus", "fcitx", "kdeconnect", "xdg-desktop", "geoclue", "upower",
        "blueman", "mpris", "indicator", "notify-osd", "dunst", "xfce4-notifyd",
    }

    # Common application icons mapping
    APP_ICON_MAP = [
        # Browsers
        (["chrome", "google-chrome"], "🌐 Chrome"),
        (["firefox"], "🦊 Firefox"),
        (["brave"], "🦁 Brave"),
        (["opera"], "🔴 Opera"),
        (["edge", "msedge"], "🧭 Edge"),
        (["chromium"], "🌐 Chromium"),
        (["zen-browser"], "🌊 Zen Browser"),

        # Editors & IDEs
        (["code", "vscode"], "📝 VS Code"),
        (["antigravity", "antigravity-ide"], "🧠 Antigravity IDE"),
        (["pycharm"], "🐍 PyCharm"),
        (["sublime", "subl"], "🗒️ Sublime Text"),
        (["gedit", "kate", "xed"], "🖋️ Text Editor"),
        (["vim", "nvim"], "💻 Vim Editor"),
        (["nano"], "📝 Nano"),
        (["emacs"], "🦄 Emacs"),

        # Terminals & Shells
        (["bash"], "🐚 Bash Shell"),
        (["zsh"], "🐚 Zsh Shell"),
        (["fish"], "🐟 Fish Shell"),
        (["gnome-terminal", "konsole", "alacritty", "kitty", "xterm", "deepin-terminal", "terminator", "tilix"], "📟 Terminal"),

        # Development & Runtimes
        (["python", "python3"], "🐍 Python App"),
        (["node", "nodejs"], "📦 Node.js"),
        (["cargo", "rustc"], "🦀 Rust"),
        (["go"], "🐹 Go App"),
        (["java"], "☕ Java App"),
        (["docker"], "🐳 Docker"),
        (["git"], "🐙 Git"),

        # Media & Entertainment
        (["vlc"], "🎬 VLC Media Player"),
        (["spotify"], "🎵 Spotify"),
        (["mpv"], "▶️ MPV Player"),
        (["rhythmbox", "audacious"], "🎧 Music Player"),
        (["obs", "obs64"], "📹 OBS Studio"),
        (["audacity"], "🎙️ Audacity"),

        # Graphics & Office
        (["gimp"], "🎨 GIMP"),
        (["inkscape"], "🖌️ Inkscape"),
        (["blender"], "🧊 Blender"),
        (["libreoffice", "soffice.bin"], "📑 LibreOffice"),
        (["evince", "okular", "atril"], "📄 PDF Viewer"),

        # Communication
        (["discord"], "💬 Discord"),
        (["telegram", "telegram-deskto"], "📱 Telegram"),
        (["slack"], "🗣️ Slack"),
        (["thunderbird"], "📧 Thunderbird"),
        (["zoom"], "📹 Zoom"),

        # Games & Launchers
        (["steam"], "🎮 Steam"),
        (["lutris", "heroic"], "🕹️ Game Launcher"),
        (["wine", "wine64"], "🍷 Wine"),

        # Files & Utilities
        (["nautilus", "dolphin", "nemo", "thunar", "dde-file-manage", "pcmanfm"], "📁 File Manager"),
        (["calc", "kcalc", "gnome-calculator"], "🔢 Calculator"),
        (["system-monitor", "gnome-system-mo", "ksysguard"], "📊 System Monitor"),
    ]

    def __init__(self) -> None:
        try:
            self.current_user = pwd.getpwuid(os.getuid()).pw_name
            self.current_uid = os.getuid()
        except Exception:
            self.current_user = os.environ.get("USER", "unknown")
            self.current_uid = 1000

    def resolve_app_name_and_icon(self, comm: str, args: str) -> Tuple[str, str]:
        """Map process binary command and arguments to friendly name and emoji."""
        comm_lower = comm.lower()
        args_lower = args.lower()

        for keywords, label in self.APP_ICON_MAP:
            for kw in keywords:
                if kw in comm_lower or f"/{kw}" in args_lower or f" {kw}" in args_lower:
                    parts = label.split(" ", 1)
                    icon = parts[0]
                    name = parts[1] if len(parts) > 1 else comm
                    return name, icon

        # Default fallback by heuristic
        if comm_lower.startswith("kworker") or comm_lower.startswith("ksoftirq") or comm_lower.startswith("rcu"):
            return comm, "🧠"
        elif comm_lower.endswith("d") or "daemon" in comm_lower:
            return comm, "⚙️"
        elif comm_lower.startswith("systemd"):
            return comm, "🔒"
        elif "helper" in comm_lower:
            return comm, "🔧"
        else:
            return comm, "📱"

    def classify_process(
        self,
        pid: int,
        ppid: int,
        user: str,
        tty: str,
        comm: str,
        args: str,
    ) -> Tuple[str, str]:
        """
        Classify process into:
          - "app": User interactive application (Terminal, GUI app, Python/Node tool)
          - "background": User/system desktop background daemon or helper
          - "system": Kernel thread, root service, or core system init
        Returns (category, category_badge).
        """
        is_kernel = (ppid == 2 or args.startswith("[") and args.endswith("]"))
        comm_lower = comm.lower()
        args_lower = args.lower()

        # 1. System Processes: Kernel threads and system services
        is_system_user = (
            user in (
                "root", "messagebus", "daemon", "syslog", "bin", "avahi",
                "colord", "rtkit", "cups", "polkitd", "nobody", "_apt",
                "dnsmasq", "ntp", "geoclue", "speech-dispatcher"
            )
            or user.startswith("systemd")
        )

        if is_kernel or (is_system_user and (ppid == 1 or tty in ("?", "-"))):
            return "system", "🔒 System"

        # 2. Background Daemons: Daemons and background helpers
        if (
            any(k in comm_lower for k in self.DAEMON_KEYWORDS)
            or "/libexec/" in args_lower
            or "/lib/systemd/" in args_lower
            or comm_lower in ("kwin_x11", "dde-shell", "dde-lock", "dde-fakewm", "(sd-pam)")
            or (comm_lower.endswith("d") and tty in ("?", "-") and not any(k in comm_lower for kw_list, _ in self.APP_ICON_MAP for k in kw_list))
        ):
            return "background", "⚙️ Background"

        # 3. User Applications
        # If user owns it and it's not categorized as system or background, it is an App!
        return "app", "📱 App"

    def detect_unresponsive(self, stat: str, cpu: float, comm: str) -> Tuple[bool, str, str, str]:
        """
        Inspect process state and detect unresponsive / frozen status.
        Returns (is_unresponsive, status_icon, status_text, unresponsive_badge).
        """
        stat_upper = stat.upper()

        # D: Uninterruptible sleep (I/O hang / driver lockup)
        if "D" in stat_upper:
            return True, "⚠️", "Unresponsive", "⚠️ Unresponsive (I/O Wait)"

        # Z: Defunct / Zombie
        if "Z" in stat_upper:
            return True, "💀", "Zombie", "💀 Zombie (Defunct)"

        # T: Stopped / Frozen by signal
        if "T" in stat_upper:
            return True, "⏸️", "Stopped", "⏸️ Frozen (Stopped)"

        # Active vs Idle
        if "R" in stat_upper or cpu > 1.0:
            return False, "🟢", "Running", ""
        else:
            return False, "🟡", "Idle", ""

    def get_processes(
        self,
        mode: str = "normal",  # "normal" (apps only) or "pro" (all tasks)
        filter_text: str = "",
        category_filter: str = "all",  # "all", "app", "background", "system", "unresponsive"
        sort_by: str = "cpu",  # "cpu", "mem", "name", "pid", "status"
        reverse: bool = True,
    ) -> Tuple[List[ProcessItem], Dict[str, Any]]:
        """
        Fetch running processes via ps, classify, filter, and sort.
        Returns (process_list, summary_metrics).
        """
        summary = {
            "total": 0,
            "apps_count": 0,
            "background_count": 0,
            "system_count": 0,
            "unresponsive_count": 0,
            "overall_cpu": 0.0,
            "used_ram_str": "",
            "total_ram_str": "",
            "ram_percent": 0.0,
        }

        # Memory summary from /proc/meminfo
        try:
            with open("/proc/meminfo", "r") as f:
                mem_kvs = {}
                for line in f:
                    pts = line.split(":")
                    if len(pts) == 2:
                        k = pts[0].strip()
                        v = pts[1].strip().split()[0]
                        if v.isdigit():
                            mem_kvs[k] = int(v)
            total_kb = mem_kvs.get("MemTotal", 1)
            avail_kb = mem_kvs.get("MemAvailable", mem_kvs.get("MemFree", 0))
            used_kb = max(0, total_kb - avail_kb)
            summary["ram_percent"] = round((used_kb / total_kb) * 100.0, 1)
            summary["used_ram_str"] = format_bytes(used_kb * 1024)
            summary["total_ram_str"] = format_bytes(total_kb * 1024)
        except Exception:
            pass

        # Fetch processes with ps
        cmd = [
            "ps",
            "-eo",
            "pid,ppid,user,tty,%cpu,%mem,rss,stat,time,comm,args",
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
            lines = res.stdout.splitlines()
        except Exception:
            lines = []

        if not lines:
            return [], summary

        items: List[ProcessItem] = []
        filter_lower = filter_text.strip().lower()
        tot_cpu = 0.0

        for line in lines[1:]:
            parts = line.split(None, 10)
            if len(parts) < 10:
                continue
            try:
                pid = int(parts[0])
                ppid = int(parts[1])
                user = parts[2]
                tty = parts[3]
                cpu = float(parts[4])
                mem = float(parts[5])
                rss_kb = int(parts[6])
                stat = parts[7]
                time_str = parts[8]
                comm = parts[9]
                args_str = parts[10].strip() if len(parts) > 10 else comm

                tot_cpu += cpu
                summary["total"] += 1

                # Classify category
                category, cat_badge = self.classify_process(pid, ppid, user, tty, comm, args_str)
                if category == "app":
                    summary["apps_count"] += 1
                elif category == "background":
                    summary["background_count"] += 1
                else:
                    summary["system_count"] += 1

                # Unresponsive detection
                is_unresp, st_icon, st_text, unresp_badge = self.detect_unresponsive(stat, cpu, comm)
                if is_unresp:
                    summary["unresponsive_count"] += 1

                # Filter by mode: In normal mode, ONLY show apps!
                if mode == "normal" and category != "app":
                    continue

                # Category filter tab
                if category_filter == "app" and category != "app":
                    continue
                elif category_filter == "background" and category != "background":
                    continue
                elif category_filter == "system" and category != "system":
                    continue
                elif category_filter == "unresponsive" and not is_unresp:
                    continue

                # Search filter
                if filter_lower:
                    searchable = f"{pid} {user} {comm} {args_str} {st_text}".lower()
                    if filter_lower not in searchable:
                        continue

                friendly_name, icon = self.resolve_app_name_and_icon(comm, args_str)
                rss_str = format_bytes(rss_kb * 1024)

                items.append(
                    ProcessItem(
                        pid=pid,
                        ppid=ppid,
                        user=user,
                        comm=comm,
                        args=args_str,
                        name=friendly_name,
                        app_icon=icon,
                        category=category,
                        category_badge=cat_badge,
                        status_icon=st_icon,
                        status_text=st_text,
                        is_unresponsive=is_unresp,
                        unresponsive_badge=unresp_badge,
                        cpu_percent=cpu,
                        mem_percent=mem,
                        rss_kb=rss_kb,
                        rss_str=rss_str,
                        stat=stat,
                        time_str=time_str,
                        tty=tty,
                    )
                )
            except (ValueError, IndexError):
                continue

        summary["overall_cpu"] = min(100.0, round(tot_cpu / max(1, os.cpu_count() or 1), 1))

        # Sorting
        # By default, prioritize unresponsive processes at the top, then sort by selected metric!
        def sort_key(p: ProcessItem) -> Any:
            val = {
                "cpu": p.cpu_percent,
                "mem": p.mem_percent,
                "rss": p.rss_kb,
                "name": p.name.lower(),
                "pid": p.pid,
                "status": (1 if p.is_unresponsive else 0, p.cpu_percent),
                "user": p.user.lower(),
            }.get(sort_by, p.cpu_percent)
            # Unresponsive boost
            unresp_boost = 1000000.0 if p.is_unresponsive else 0.0
            if isinstance(val, (int, float)):
                return (unresp_boost + val) if reverse else (-unresp_boost + val)
            return val

        items.sort(key=sort_key, reverse=reverse)
        return items, summary

    def terminate_process(
        self,
        pid: int,
        sig: int = signal.SIGTERM,
        is_pro: bool = False,
        app: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """
        Safely terminate or force-kill a process.
        If permission is denied and in Pro mode or system process, automatically elevates via privileged helper!
        """
        sig_name = "SIGTERM (Graceful End Task)" if sig == signal.SIGTERM else "SIGKILL (Force Kill)"

        try:
            os.kill(pid, sig)
            return True, f"✔ Successfully sent {sig_name} to process (PID {pid})."
        except ProcessLookupError:
            return False, f"Process {pid} no longer exists."
        except PermissionError:
            # Elevation handling
            from ..elevation import elevated_run_command

            cmd = ["kill", f"-{int(sig)}", str(pid)]
            reason = f"Admin authorization required to terminate system/background process PID {pid}."
            task_desc = f"Terminate process PID {pid} via {sig_name}"

            if app is not None and hasattr(app, "suspend"):
                with app.suspend():
                    success, _, err = elevated_run_command(
                        cmd=cmd,
                        reason=reason,
                        task_description=task_desc,
                    )
            else:
                success, _, err = elevated_run_command(
                    cmd=cmd,
                    reason=reason,
                    task_description=task_desc,
                )

            if success:
                return True, f"✔ Successfully terminated PID {pid} using administrator privileges."
            return False, f"Failed to terminate PID {pid}: {err or 'Permission denied.'}"
        except Exception as e:
            return False, f"Error terminating PID {pid}: {e}"
