"""Persistence indicator collector (preview only).

Module responsibility:
    Collect startup persistence indicators that may explain recurring proxy reconfiguration.

System placement:
    Called by :mod:`proxy_guard.main` as supplemental context for risk inference.

Safety boundary:
    Read-only inspections only. No task deletion, registry mutation, or startup removal.
"""

from __future__ import annotations

import platform
import subprocess
from typing import Any


def _run(argv: list[str], timeout_seconds: float = 25.0) -> tuple[int, str]:
    """Execute one persistence-related command with timeout."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def collect_persistence_indicators() -> dict[str, Any]:
    """Collect startup/scheduled-task/run-key indicators without mutation.

    Returns:
        dict[str, Any]: Startup command summaries, scheduled task text, run-key excerpts, and
        limitations list.

    Side effects:
        Runs local read-only commands (PowerShell CIM, schtasks, reg query).

    Failure modes:
        Collector degrades to empty strings when a command fails; risk inference should treat
        missing entries as uncertainty, not absence.
    """
    if platform.system().lower() != "windows":
        return {"startup_entries": [], "scheduled_tasks": [], "run_keys": [], "limitations": ["non_windows_platform"]}
    ps_startup = (
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name,Command,Location,User | ConvertTo-Json -Compress"
    )
    _, startup_out = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_startup], timeout_seconds=35.0)
    sch_code, sch_out = _run(["schtasks", "/Query", "/FO", "CSV", "/V"], timeout_seconds=35.0)
    hkcu_code, hkcu_run = _run(["reg", "query", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"])
    hklm_code, hklm_run = _run(["reg", "query", r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"])
    return {
        "startup_entries": startup_out[:6000],
        "scheduled_tasks": sch_out[:6000] if sch_code == 0 else "",
        "run_keys": {"hkcu": hkcu_run[:3000] if hkcu_code == 0 else "", "hklm": hklm_run[:3000] if hklm_code == 0 else ""},
        "limitations": [],
    }

