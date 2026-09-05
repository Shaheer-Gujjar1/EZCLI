"""High-performance, dependency-free Linux system metrics and process collector for EasyCLI."""

import glob
import os
import platform
import signal
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

from ..collectors import format_bytes
from ..distro import detect_distro


class SystemMetricsCollector:
    """Collects real-time CPU, Memory, Swap, Disk, and Process metrics from /proc and ps."""

    def __init__(self) -> None:
        self.last_cpu_ticks: Dict[str, Tuple[float, float]] = {}
        self.last_sample_time: float = 0.0
        # Initialize initial baseline
        self._sample_cpu_ticks()

    def _sample_cpu_ticks(self) -> Dict[str, Tuple[float, float]]:
        """Read /proc/stat and return {cpu_name: (idle_ticks, total_ticks)}."""
        ticks: Dict[str, Tuple[float, float]] = {}
        try:
            with open("/proc/stat", "r") as f:
                for line in f:
                    if not line.startswith("cpu"):
                        continue
                    parts = line.split()
                    name = parts[0]
                    # values: user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice
                    values = [float(x) for x in parts[1:]]
                    if len(values) >= 4:
                        idle = values[3] + (values[4] if len(values) > 4 else 0.0)
                        total = sum(values)
                        ticks[name] = (idle, total)
        except Exception:
            pass
        return ticks

    def get_cpu_percentages(self) -> Tuple[float, List[Dict[str, Any]]]:
        """Compute CPU usage percentages for overall and per-core since last sample."""
        current_ticks = self._sample_cpu_ticks()
        now = time.time()

        if not self.last_cpu_ticks:
            # Baseline didn't exist, sleep briefly to calculate delta
            time.sleep(0.04)
            self.last_cpu_ticks = current_ticks
            current_ticks = self._sample_cpu_ticks()

        overall_percent = 0.0
        per_core: List[Dict[str, Any]] = []

        # Calculate overall CPU
        if "cpu" in current_ticks and "cpu" in self.last_cpu_ticks:
            idle_now, tot_now = current_ticks["cpu"]
            idle_prev, tot_prev = self.last_cpu_ticks["cpu"]
            d_tot = tot_now - tot_prev
            d_idle = idle_now - idle_prev
            if d_tot > 0:
                usage = (1.0 - (d_idle / d_tot)) * 100.0
                overall_percent = max(0.0, min(100.0, round(usage, 1)))

        # Calculate per-core CPU (cpu0, cpu1, ...)
        core_keys = sorted(
            [k for k in current_ticks.keys() if k.startswith("cpu") and k[3:].isdigit()],
            key=lambda x: int(x[3:])
        )
        for k in core_keys:
            core_id = int(k[3:])
            if k in self.last_cpu_ticks:
                idle_now, tot_now = current_ticks[k]
                idle_prev, tot_prev = self.last_cpu_ticks[k]
                d_tot = tot_now - tot_prev
                d_idle = idle_now - idle_prev
                if d_tot > 0:
                    c_usage = (1.0 - (d_idle / d_tot)) * 100.0
                    c_pct = max(0.0, min(100.0, round(c_usage, 1)))
                else:
                    c_pct = 0.0
            else:
                c_pct = 0.0
            per_core.append({
                "core_id": core_id,
                "name": f"CPU {core_id}",
                "percent": c_pct,
            })

        self.last_cpu_ticks = current_ticks
        self.last_sample_time = now
        return overall_percent, per_core

    def get_memory_info(self) -> Dict[str, Any]:
        """Read /proc/meminfo and return RAM & Swap details."""
        mem: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_str = parts[1].strip().split()[0]
                        if val_str.isdigit():
                            mem[key] = int(val_str)
        except Exception:
            pass

        ram_total_bytes = mem.get("MemTotal", 0) * 1024
        ram_free_bytes = mem.get("MemFree", 0) * 1024
        buffers_bytes = mem.get("Buffers", 0) * 1024
        cached_bytes = mem.get("Cached", 0) * 1024

        if "MemAvailable" in mem:
            ram_avail_bytes = mem["MemAvailable"] * 1024
        else:
            ram_avail_bytes = ram_free_bytes + buffers_bytes + cached_bytes

        ram_used_bytes = max(0, ram_total_bytes - ram_avail_bytes)
        ram_percent = round((ram_used_bytes / max(1, ram_total_bytes)) * 100.0, 1)

        swap_total_bytes = mem.get("SwapTotal", 0) * 1024
        swap_free_bytes = mem.get("SwapFree", 0) * 1024
        swap_used_bytes = max(0, swap_total_bytes - swap_free_bytes)
        swap_percent = round((swap_used_bytes / max(1, swap_total_bytes)) * 100.0, 1) if swap_total_bytes else 0.0

        return {
            "ram_total_bytes": ram_total_bytes,
            "ram_used_bytes": ram_used_bytes,
            "ram_free_bytes": ram_free_bytes,
            "ram_avail_bytes": ram_avail_bytes,
            "ram_percent": ram_percent,
            "ram_total_str": format_bytes(ram_total_bytes),
            "ram_used_str": format_bytes(ram_used_bytes),
            "ram_avail_str": format_bytes(ram_avail_bytes),
            "swap_total_bytes": swap_total_bytes,
            "swap_used_bytes": swap_used_bytes,
            "swap_percent": swap_percent,
            "swap_total_str": format_bytes(swap_total_bytes),
            "swap_used_str": format_bytes(swap_used_bytes),
        }

    def get_uptime(self) -> Tuple[float, str]:
        """Read system uptime from /proc/uptime and return (seconds, formatted_string)."""
        try:
            with open("/proc/uptime", "r") as f:
                uptime_sec = float(f.read().split()[0])
        except Exception:
            uptime_sec = 0.0

        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        mins = int((uptime_sec % 3600) // 60)
        secs = int(uptime_sec % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{mins}m")
        if days == 0 and hours == 0:
            parts.append(f"{secs}s")

        return uptime_sec, " ".join(parts)

    def get_system_overview(self) -> Dict[str, Any]:
        """Return comprehensive system summary overview."""
        overall_cpu, per_core = self.get_cpu_percentages()
        mem_info = self.get_memory_info()
        uptime_sec, uptime_str = self.get_uptime()

        # Load averages
        try:
            load1, load5, load15 = os.getloadavg()
            l1, l5, l15 = round(load1, 2), round(load5, 2), round(load15, 2)
        except Exception:
            l1, l5, l15 = 0.0, 0.0, 0.0

        distro_info = detect_distro()
        os_display = getattr(distro_info, "pretty_name", "") or getattr(distro_info, "name", "") or platform.system()
        kernel = platform.release()
        hostname = platform.node()
        cores = os.cpu_count() or 1

        return {
            "hostname": hostname,
            "os_name": os_display,
            "kernel": kernel,
            "cores": cores,
            "uptime_seconds": uptime_sec,
            "uptime_str": uptime_str,
            "cpu_percent": overall_cpu,
            "cpu_per_core": per_core,
            "load_1m": l1,
            "load_5m": l5,
            "load_15m": l15,
            **mem_info,
        }

    def get_processes(
        self,
        sort_by: str = "cpu",
        reverse: bool = True,
        filter_text: str = "",
        limit: int = 250,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Fetch running processes via ps, parse metrics, filter, and sort."""
        tasks_stats = {
            "total": 0,
            "running": 0,
            "sleeping": 0,
            "stopped": 0,
            "zombie": 0,
        }

        cmd = [
            "ps",
            "-eo",
            "pid:10,ppid:10,user:12,%cpu:6,%mem:6,rss:10,stat:6,time:10,comm:20,args",
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
            lines = res.stdout.splitlines()
        except Exception:
            lines = []

        if not lines:
            return [], tasks_stats

        processes: List[Dict[str, Any]] = []
        filter_lower = filter_text.strip().lower()

        # Skip header line
        for line in lines[1:]:
            if len(line) < 70:
                continue
            try:
                pid = int(line[0:10].strip())
                ppid = int(line[11:21].strip())
                user = line[22:34].strip()
                cpu = float(line[35:41].strip())
                mem = float(line[42:48].strip())
                rss_kb = int(line[49:59].strip())
                stat = line[60:66].strip()
                time_str = line[67:77].strip()
                comm = line[78:98].strip()
                args_str = line[99:].strip() if len(line) > 99 else comm

                # Count process states
                tasks_stats["total"] += 1
                if stat.startswith("R"):
                    tasks_stats["running"] += 1
                elif stat.startswith("Z"):
                    tasks_stats["zombie"] += 1
                elif stat.startswith("T"):
                    tasks_stats["stopped"] += 1
                else:
                    tasks_stats["sleeping"] += 1

                # Filter text match
                if filter_lower:
                    searchable = f"{pid} {user} {comm} {args_str}".lower()
                    if filter_lower not in searchable:
                        continue

                # Human readable memory
                rss_str = format_bytes(rss_kb * 1024)

                processes.append({
                    "pid": pid,
                    "ppid": ppid,
                    "user": user,
                    "cpu": cpu,
                    "mem": mem,
                    "rss_kb": rss_kb,
                    "rss_str": rss_str,
                    "stat": stat,
                    "time": time_str,
                    "comm": comm,
                    "args": args_str,
                })
            except (ValueError, IndexError):
                continue

        # Sort processes
        key_fn = {
            "cpu": lambda p: p["cpu"],
            "mem": lambda p: p["mem"],
            "pid": lambda p: p["pid"],
            "rss": lambda p: p["rss_kb"],
            "user": lambda p: p["user"].lower(),
            "name": lambda p: p["comm"].lower(),
            "time": lambda p: p["time"],
        }.get(sort_by, lambda p: p["cpu"])

        processes.sort(key=key_fn, reverse=reverse)
        return processes[:limit], tasks_stats

    @staticmethod
    def get_process_details(pid: int) -> Dict[str, Any]:
        """Inspect detailed information about a process from /proc/<pid>/."""
        details: Dict[str, Any] = {
            "pid": pid,
            "name": "",
            "cmdline": "",
            "cwd": "",
            "exe": "",
            "ppid": 0,
            "state": "",
            "threads": 1,
            "vm_size": "N/A",
            "vm_rss": "N/A",
            "user": "",
            "fds_count": 0,
            "exists": False,
        }

        proc_dir = f"/proc/{pid}"
        if not os.path.exists(proc_dir):
            return details

        details["exists"] = True

        # Read /proc/<pid>/cmdline
        try:
            with open(f"{proc_dir}/cmdline", "rb") as f:
                raw = f.read()
                cmdline = " ".join([p.decode("utf-8", errors="replace") for p in raw.split(b"\x00") if p])
                details["cmdline"] = cmdline
        except Exception:
            pass

        # Read /proc/<pid>/cwd
        try:
            details["cwd"] = os.readlink(f"{proc_dir}/cwd")
        except Exception:
            details["cwd"] = "[Permission Denied / Hidden]"

        # Read /proc/<pid>/exe
        try:
            details["exe"] = os.readlink(f"{proc_dir}/exe")
        except Exception:
            details["exe"] = "[Permission Denied / Hidden]"

        # Read /proc/<pid>/status
        try:
            with open(f"{proc_dir}/status", "r") as f:
                for line in f:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        k = parts[0].strip()
                        v = parts[1].strip()
                        if k == "Name":
                            details["name"] = v
                        elif k == "State":
                            details["state"] = v
                        elif k == "PPid" and v.isdigit():
                            details["ppid"] = int(v)
                        elif k == "Threads" and v.isdigit():
                            details["threads"] = int(v)
                        elif k == "VmSize":
                            details["vm_size"] = v
                        elif k == "VmRSS":
                            details["vm_rss"] = v
        except Exception:
            pass

        # Open file descriptors count
        try:
            fds = os.listdir(f"{proc_dir}/fd")
            details["fds_count"] = len(fds)
        except Exception:
            details["fds_count"] = 0

        return details

    @staticmethod
    def terminate_process(pid: int, sig: int = signal.SIGTERM) -> Tuple[bool, str]:
        """Terminate a process safely using SIGTERM (default) or SIGKILL with elevation support."""
        try:
            os.kill(pid, sig)
            sig_name = "SIGTERM (graceful)" if sig == signal.SIGTERM else "SIGKILL (force)"
            return True, f"Sent {sig_name} to PID {pid} successfully."
        except ProcessLookupError:
            return False, f"Process {pid} no longer exists."
        except PermissionError:
            # Attempt elevation via privileged helper
            from ..elevation import elevated_run_command
            cmd = ["kill", f"-{int(sig)}", str(pid)]
            success, stdout, err = elevated_run_command(
                cmd=cmd,
                reason=f"Terminate process {pid} owned by another user",
                task_description=f"Send signal {sig} to PID {pid}",
            )
            if success:
                return True, f"Successfully terminated PID {pid} using admin rights."
            return False, f"Failed to terminate PID {pid}: {err or 'Permission denied'}"
        except Exception as e:
            return False, f"Error terminating PID {pid}: {e}"
