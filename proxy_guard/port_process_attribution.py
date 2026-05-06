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

import csv
import json
import logging
import platform
import subprocess
from typing import Any

_LOGGER = logging.getLogger(__name__)
_KNOWN_PROXY_PROCESS_NAMES = {
    "charles.exe",
    "fiddler.exe",
    "mitmproxy.exe",
    "node.exe",
    "python.exe",
    "proxyman.exe",
    "burp.exe",
    "zap.exe",
    "zscaler.exe",
    "netskope.exe",
}


def _run(argv: list[str], timeout_seconds: float = 20.0) -> tuple[int, str]:
    """Execute one attribution-related command and return merged output.

    Args:
        argv: Command arguments passed with ``shell=False``.
        timeout_seconds: Maximum runtime.

    Returns:
        Tuple of return code and merged stdout/stderr text.
    """
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _LOGGER.debug("Attribution command failed: %s", exc)
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _parse_netstat_listener_pids(netstat_output: str, port: int) -> list[int]:
    """Parse netstat output for TCP listener PIDs bound to a port.

    Args:
        netstat_output: Text from ``netstat -ano``.
        port: Local TCP port to match.

    Returns:
        Ordered unique PIDs for listener rows matching the port.
    """
    pids: list[int] = []
    for line in netstat_output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_address = parts[1]
        state = parts[-2]
        pid_text = parts[-1]
        if state.upper() != "LISTENING":
            continue
        if not local_address.endswith(f":{port}"):
            continue
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def _listener_pid(port: int) -> int | None:
    """Resolve listening PID for a proxy port via netstat parsing.

    Args:
        port: TCP port from the WinINET proxy endpoint.

    Returns:
        PID of a matching listener when found, otherwise ``None``.
    """
    code, out = _run(["netstat", "-ano"])
    if code != 0:
        return None
    pids = _parse_netstat_listener_pids(out, port)
    return pids[0] if pids else None


def _tasklist_name(pid: int) -> str | None:
    """Resolve process name fallback using tasklist CSV output."""
    code, out = _run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
    if code != 0:
        return None
    rows = list(csv.reader(out.splitlines()))
    if not rows or not rows[0]:
        return None
    image_name = rows[0][0].strip()
    if image_name.upper() == "INFO:":
        return None
    return image_name or None


def _candidate_proxy_processes() -> list[dict[str, Any]]:
    """Return running proxy-like processes when exact port attribution fails.

    Returns:
        List of process candidate dictionaries from tasklist. This is correlation evidence only.
    """
    code, out = _run(["tasklist", "/FO", "CSV", "/NH"], timeout_seconds=25.0)
    if code != 0:
        return []
    candidates: list[dict[str, Any]] = []
    for row in csv.reader(out.splitlines()):
        if len(row) < 2:
            continue
        name = row[0].strip()
        if name.lower() not in _KNOWN_PROXY_PROCESS_NAMES:
            continue
        try:
            pid = int(row[1])
        except ValueError:
            pid = None
        candidates.append({"process_name": name, "pid": pid})
    return candidates[:10]


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
        blob = json.loads(out.strip())
    except json.JSONDecodeError:
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
            "candidate_processes": [],
            "attribution_confidence": "low",
            "limitations": ["non_windows_platform"],
            "observations": ["Port/process attribution was not attempted because platform is not Windows."],
        }
    if port is None:
        return {
            "port": None,
            "pid": None,
            "process_name": None,
            "process_path": None,
            "parent_pid": None,
            "candidate_processes": [],
            "attribution_confidence": "low",
            "limitations": ["no_proxy_port_to_attribute"],
            "observations": ["No proxy port was available for listener attribution."],
        }
    pid = _listener_pid(port)
    if pid is None:
        candidates = _candidate_proxy_processes()
        process_name = candidates[0]["process_name"] if candidates else None
        return {
            "port": port,
            "pid": None,
            "process_name": process_name,
            "process_path": None,
            "parent_pid": None,
            "candidate_processes": candidates,
            "attribution_confidence": "medium" if candidates else "low",
            "limitations": ["no_listener_pid_found", "process_name_correlation_only"] if candidates else ["no_listener_pid_found"],
            "observations": [
                f"No exact TCP listener PID was observed for proxy port {port}.",
                "Proxy-like process name correlation is heuristic only.",
            ]
            if candidates
            else [f"No exact TCP listener PID was observed for proxy port {port}."],
        }
    details = _process_details(pid)
    confidence = "high"
    limitations: list[str] = []
    observations = [f"Exact TCP listener PID observed for proxy port {port}: {pid}."]
    if not details.get("process_path"):
        limitations.append("process_path_unavailable")
    if not details.get("process_name"):
        limitations.append("process_name_unavailable")
    return {
        "port": port,
        "pid": details.get("pid"),
        "process_name": details.get("process_name"),
        "process_path": details.get("process_path"),
        "parent_pid": details.get("parent_pid"),
        "candidate_processes": [],
        "attribution_confidence": confidence,
        "limitations": limitations,
        "observations": observations,
    }


__all__ = ["attribute_proxy_port", "_parse_netstat_listener_pids"]

