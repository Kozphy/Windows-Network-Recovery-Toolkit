"""Proxy-port to process attribution (heuristic, read-only).

Module responsibility:
    Correlate loopback proxy port listeners with process metadata for explainable risk scoring.

System placement:
    Observation/enrichment layer invoked before risk inference.

Key invariants:
    - Attribution is best-effort and explicitly non-forensic.
    - Missing listener/process details reduce confidence and add limitations.
"""

from __future__ import annotations

import platform
import re
import subprocess
from typing import Any


def _run(argv: list[str], timeout_seconds: float = 20.0) -> tuple[int, str]:
    """Execute one attribution-related command and return merged output."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _listener_pid(port: int) -> int | None:
    """Resolve listening PID for localhost proxy port via netstat parsing."""
    code, out = _run(["netstat", "-ano"])
    if code != 0:
        return None
    patterns = [
        re.compile(rf"^\s*TCP\s+127\.0\.0\.1:{port}\s+\S+\s+LISTENING\s+(?P<pid>\d+)\s*$", re.I),
        re.compile(rf"^\s*TCP\s+\[::1\]:{port}\s+\S+\s+LISTENING\s+(?P<pid>\d+)\s*$", re.I),
        re.compile(rf"^\s*TCP\s+localhost:{port}\s+\S+\s+LISTENING\s+(?P<pid>\d+)\s*$", re.I),
    ]
    for line in out.splitlines():
        for pattern in patterns:
            m = pattern.match(line)
            if m:
                return int(m.group("pid"))
    return None


def _tasklist_name(pid: int) -> str | None:
    """Resolve process name fallback using tasklist CSV output."""
    code, out = _run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
    if code != 0:
        return None
    # CSV first value is image name
    m = re.match(r'^"([^"]+)"', out.strip())
    return m.group(1) if m else None


def _process_details(pid: int) -> dict[str, Any]:
    """Resolve PID/process name/path/parent via CIM with fallback strategy.

    Args:
        pid: Process identifier from listener correlation.

    Returns:
        dict[str, Any]: Partial process metadata; may contain ``None`` values.

    Failure modes:
        CIM failures fall back to ``tasklist`` name-only resolution.
    """
    # Use CIM for executable path + parent pid when available.
    ps = (
        f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" -ErrorAction SilentlyContinue; "
        "if($p){ "
        "$o=[ordered]@{pid=$p.ProcessId;parent_pid=$p.ParentProcessId;name=$p.Name;path=$p.ExecutablePath}; "
        "$o|ConvertTo-Json -Compress }"
    )
    code, out = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], timeout_seconds=25.0)
    if code != 0 or not out.strip():
        return {"pid": pid, "parent_pid": None, "process_name": _tasklist_name(pid), "process_path": None}
    try:
        import json

        blob = json.loads(out.strip())
    except Exception:
        return {"pid": pid, "parent_pid": None, "process_name": _tasklist_name(pid), "process_path": None}
    return {
        "pid": int(blob.get("pid", pid)),
        "parent_pid": blob.get("parent_pid"),
        "process_name": blob.get("name") or _tasklist_name(pid),
        "process_path": blob.get("path"),
    }


def attribute_proxy_port(port: int | None) -> dict[str, Any]:
    """Attribute a localhost proxy listener port to a process.

    Args:
        port: Localhost proxy port extracted from ProxyServer value.

    Returns:
        Dict containing PID/name/path/parent_pid, attribution confidence, and limitations.

    Constraints:
        High confidence means listener PID was observed for the port; it does not prove registry
        writer identity.
    """
    if platform.system().lower() != "windows":
        return {
            "port": port,
            "pid": None,
            "process_name": None,
            "process_path": None,
            "parent_pid": None,
            "attribution_confidence": "low",
            "limitations": ["non_windows_platform"],
        }
    if port is None:
        return {
            "port": None,
            "pid": None,
            "process_name": None,
            "process_path": None,
            "parent_pid": None,
            "attribution_confidence": "low",
            "limitations": ["no_proxy_port_to_attribute"],
        }
    pid = _listener_pid(port)
    if pid is None:
        return {
            "port": port,
            "pid": None,
            "process_name": None,
            "process_path": None,
            "parent_pid": None,
            "attribution_confidence": "low",
            "limitations": ["no_listener_pid_found"],
        }
    details = _process_details(pid)
    confidence = "high" if details.get("process_name") else "medium"
    limitations: list[str] = []
    if not details.get("process_path"):
        limitations.append("process_path_unavailable")
        if confidence == "high":
            confidence = "medium"
    return {
        "port": port,
        "pid": details.get("pid"),
        "process_name": details.get("process_name"),
        "process_path": details.get("process_path"),
        "parent_pid": details.get("parent_pid"),
        "attribution_confidence": confidence,
        "limitations": limitations,
    }

