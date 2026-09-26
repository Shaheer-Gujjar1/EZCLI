"""Backend engine for UFW firewall management in EasyCLI.

Provides:
- Detection of ufw installation and operational status (active/inactive)
- Parsing of numbered rules and default incoming/outgoing policies
- Safety check for SSH lockout (ensures port 22/SSH is allowed before enabling)
- Elevated helpers for enabling, disabling, adding, and deleting firewall rules
"""

from dataclasses import dataclass
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ..elevation import elevated_run_command


@dataclass
class FirewallRule:
    """Represents a single parsed UFW rule."""
    index: int
    to_port: str
    action: str  # ALLOW, DENY, REJECT, LIMIT
    direction: str  # IN, OUT, FWD
    from_ip: str
    v6: bool = False


@dataclass
class FirewallStatus:
    """Represents the complete status of the UFW firewall."""
    installed: bool
    active: bool
    default_incoming: str = "deny"
    default_outgoing: str = "allow"
    rules: List[FirewallRule] = None  # type: ignore
    has_ssh_rule: bool = False
    raw_output: str = ""

    def __post_init__(self):
        if self.rules is None:
            self.rules = []


def is_ufw_installed() -> bool:
    """Check if the ufw binary is installed on the system."""
    return shutil.which("ufw") is not None or os.path.exists("/usr/sbin/ufw") or os.path.exists("/sbin/ufw")


def parse_ufw_status_output(output: str) -> Tuple[bool, str, str, List[FirewallRule], bool]:
    """
    Parse the stdout of `ufw status numbered` or `ufw status verbose`.
    Returns (active, default_incoming, default_outgoing, rules, has_ssh_rule).
    """
    active = "Status: active" in output
    default_incoming = "deny"
    default_outgoing = "allow"
    rules: List[FirewallRule] = []
    has_ssh_rule = False

    # Extract default policies if present
    # e.g.: "Default: deny (incoming), allow (outgoing), disabled (routed)"
    default_match = re.search(r"Default:\s*(\w+)\s*\(incoming\),\s*(\w+)\s*\(outgoing\)", output, re.IGNORECASE)
    if default_match:
        default_incoming = default_match.group(1).lower()
        default_outgoing = default_match.group(2).lower()

    # Rule pattern: e.g. [ 1] 22/tcp                     ALLOW IN    Anywhere
    # or [ 2] 80                         ALLOW IN    192.168.1.0/24
    rule_regex = re.compile(
        r"\[\s*(\d+)\]\s+([^\s]+(?:\s+\(v6\))?)\s+(ALLOW|DENY|REJECT|LIMIT)\s*(IN|OUT|FWD)?\s+(.+)$",
        re.IGNORECASE,
    )

    for line in output.splitlines():
        line = line.strip()
        m = rule_regex.match(line)
        if m:
            idx = int(m.group(1))
            target_port = m.group(2).strip()
            action = m.group(3).upper()
            direction = (m.group(4) or "IN").upper()
            from_target = m.group(5).strip()

            v6 = "(v6)" in target_port or "(v6)" in from_target
            clean_port = target_port.replace("(v6)", "").strip()
            clean_from = from_target.replace("(v6)", "").strip()

            # Check if this rule protects SSH from incoming lockout
            if action == "ALLOW" and direction in ("IN", ""):
                lower_p = clean_port.lower()
                if (
                    "22" in lower_p
                    or "ssh" in lower_p
                    or "openssh" in lower_p
                ):
                    has_ssh_rule = True

            rules.append(
                FirewallRule(
                    index=idx,
                    to_port=clean_port,
                    action=action,
                    direction=direction,
                    from_ip=clean_from or "Anywhere",
                    v6=v6,
                )
            )

    return active, default_incoming, default_outgoing, rules, has_ssh_rule


def get_firewall_status() -> FirewallStatus:
    """Fetch and parse current UFW status and rules."""
    if not is_ufw_installed():
        return FirewallStatus(installed=False, active=False)

    ufw_bin = shutil.which("ufw") or "/usr/sbin/ufw"

    # Try non-elevated read first (some distros allow reading ufw status or reading /etc/ufw/)
    try:
        proc = subprocess.run(
            [ufw_bin, "status", "numbered"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and ("Status:" in proc.stdout or "Status: inactive" in proc.stdout):
            active, in_def, out_def, rules, has_ssh = parse_ufw_status_output(proc.stdout)
            return FirewallStatus(
                installed=True,
                active=active,
                default_incoming=in_def,
                default_outgoing=out_def,
                rules=rules,
                has_ssh_rule=has_ssh,
                raw_output=proc.stdout,
            )
    except Exception:
        pass

    # If non-elevated failed or produced permission error, try via elevated read
    success, stdout, _ = elevated_run_command(
        cmd=[ufw_bin, "status", "numbered"],
        reason="Read UFW firewall status and active rules",
        task_description="Firewall Status Check",
        timeout=10,
        skip_explanation=True,
    )
    if success and "Status:" in stdout:
        active, in_def, out_def, rules, has_ssh = parse_ufw_status_output(stdout)
        return FirewallStatus(
            installed=True,
            active=active,
            default_incoming=in_def,
            default_outgoing=out_def,
            rules=rules,
            has_ssh_rule=has_ssh,
            raw_output=stdout,
        )

    # Fallback: check status file /etc/ufw/ufw.conf
    is_active = False
    try:
        if os.path.exists("/etc/ufw/ufw.conf"):
            with open("/etc/ufw/ufw.conf", "r", encoding="utf-8") as f:
                content = f.read()
                if "ENABLED=yes" in content:
                    is_active = True
    except Exception:
        pass

    return FirewallStatus(
        installed=True,
        active=is_active,
        rules=[],
        has_ssh_rule=False,
    )


def toggle_firewall(enable: bool) -> Tuple[bool, str]:
    """Toggle UFW firewall state (enable/disable) with admin rights."""
    ufw_bin = shutil.which("ufw") or "/usr/sbin/ufw"
    cmd = [ufw_bin, "--force", "enable" if enable else "disable"]
    verb = "Enabling" if enable else "Disabling"

    success, stdout, stderr = elevated_run_command(
        cmd=cmd,
        reason=f"{verb} the UFW system firewall",
        task_description=f"Firewall {'Enable' if enable else 'Disable'}",
        timeout=15,
    )
    if success:
        return True, stdout or f"Firewall successfully {'enabled' if enable else 'disabled'}."
    return False, stderr or "Failed to change firewall state."


def add_firewall_rule(action: str, port_or_service: str, protocol: str = "") -> Tuple[bool, str]:
    """Add a new UFW allow/deny rule."""
    ufw_bin = shutil.which("ufw") or "/usr/sbin/ufw"
    clean_action = action.strip().lower()
    clean_target = port_or_service.strip()
    if protocol and protocol.lower() in ("tcp", "udp") and "/" not in clean_target:
        clean_target = f"{clean_target}/{protocol.lower()}"

    cmd = [ufw_bin, clean_action, clean_target]
    success, stdout, stderr = elevated_run_command(
        cmd=cmd,
        reason=f"Add firewall rule to {clean_action.upper()} traffic on {clean_target}",
        task_description="Add Firewall Rule",
        timeout=15,
    )
    if success:
        return True, stdout or f"Rule successfully added: {clean_action} {clean_target}"
    return False, stderr or f"Failed to add firewall rule: {stderr}"


def delete_firewall_rule(rule_num: int) -> Tuple[bool, str]:
    """Delete a UFW rule by its numbered index."""
    ufw_bin = shutil.which("ufw") or "/usr/sbin/ufw"
    cmd = [ufw_bin, "--force", "delete", str(rule_num)]
    success, stdout, stderr = elevated_run_command(
        cmd=cmd,
        reason=f"Delete firewall rule #{rule_num}",
        task_description=f"Delete Firewall Rule #{rule_num}",
        timeout=15,
    )
    if success:
        return True, stdout or f"Rule #{rule_num} deleted."
    return False, stderr or f"Failed to delete firewall rule #{rule_num}."
