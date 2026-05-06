"""Persistence indicator collector (preview only).

Module responsibility:
    Collect startup persistence indicators that may explain recurring proxy reconfiguration.

System placement:
    Called by :mod:`proxy_guard.main` as supplemental context for risk inference.

Safety boundary:
    Read-only inspections only. No task deletion, registry mutation, or startup removal.
"""

from __future__ import annotations

import csv
import json
import logging
import platform
import subprocess
from typing import Any

_LOGGER = logging.getLogger(__name__)
_RUN_KEY_PATHS = {
    "HKCU_Run": (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
    "HKCU_RunOnce": (r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU"),
    "HKLM_Run": (r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    "HKLM_RunOnce": (r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM"),
}


def _run(argv: list[str], timeout_seconds: float = 25.0) -> tuple[int, str]:
    """Execute one persistence-related command with timeout.

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
        _LOGGER.debug("Persistence command failed: %s", exc)
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _parse_json_list(text: str) -> list[dict[str, Any]]:
    """Parse PowerShell JSON that may represent one object or a list."""
    if not text.strip():
        return []
    try:
        blob = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(blob, dict):
        return [blob]
    if isinstance(blob, list):
        return [item for item in blob if isinstance(item, dict)]
    return []


def _collect_startup_commands() -> tuple[list[dict[str, Any]], list[str]]:
    """Collect Win32_StartupCommand rows."""
    ps_startup = (
        "Get-CimInstance Win32_StartupCommand | "
        "Select-Object Name,Command,Location,User | ConvertTo-Json -Compress"
    )
    code, startup_out = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_startup], timeout_seconds=35.0)
    if code != 0:
        return [], ["startup_command_collection_failed"]
    return _parse_json_list(startup_out), []


def _collect_scheduled_tasks() -> tuple[list[dict[str, Any]], list[str]]:
    """Collect scheduled task previews from schtasks CSV output."""
    code, sch_out = _run(["schtasks", "/Query", "/FO", "CSV", "/V"], timeout_seconds=35.0)
    if code != 0:
        return [], ["scheduled_task_collection_failed"]
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(sch_out.splitlines()):
        rows.append(
            {
                "task_name": row.get("TaskName") or row.get("Task Name"),
                "task_to_run": row.get("Task To Run"),
                "status": row.get("Status"),
                "author": row.get("Author"),
                "run_as_user": row.get("Run As User"),
            }
        )
    return rows[:500], []


def _collect_run_keys() -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """Collect common Run/RunOnce registry keys via winreg."""
    try:
        import winreg
    except ImportError:
        return {}, ["winreg_unavailable"]

    root_map = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    output: dict[str, list[dict[str, Any]]] = {}
    limitations: list[str] = []
    for label, (subkey, hive_name) in _RUN_KEY_PATHS.items():
        hive = root_map[hive_name]
        entries: list[dict[str, Any]] = []
        try:
            with winreg.OpenKey(hive, subkey) as key:
                index = 0
                while True:
                    try:
                        name, value, _value_type = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    entries.append({"name": name, "command": str(value), "location": f"{hive_name}\\{subkey}"})
                    index += 1
        except OSError:
            limitations.append(f"{label.lower()}_not_accessible_or_missing")
        output[label] = entries
    return output, limitations


def collect_persistence_indicators() -> dict[str, Any]:
    """Collect startup/scheduled-task/run-key indicators without mutation.

    Returns:
        dict[str, Any]: Startup command, scheduled task, run-key previews, and limitations.

    Side effects:
        Runs local read-only commands (PowerShell CIM and schtasks) and reads registry Run keys.

    Failure modes:
        Collector degrades to empty collections when a command fails; risk inference should treat
        missing entries as uncertainty, not absence.
    """
    if platform.system().lower() != "windows":
        return {
            "startup_entries": [],
            "scheduled_tasks": [],
            "run_keys": {},
            "persistence_entry_count": 0,
            "observations": ["Persistence indicators were not inspected because platform is not Windows."],
            "limitations": ["non_windows_platform"],
        }
    startup_entries, startup_limitations = _collect_startup_commands()
    scheduled_tasks, task_limitations = _collect_scheduled_tasks()
    run_keys, run_key_limitations = _collect_run_keys()
    entry_count = len(startup_entries) + len(scheduled_tasks) + sum(len(entries) for entries in run_keys.values())
    return {
        "startup_entries": startup_entries,
        "scheduled_tasks": scheduled_tasks,
        "run_keys": run_keys,
        "persistence_entry_count": entry_count,
        "observations": [
            f"Startup persistence preview collected: {len(startup_entries)} Win32_StartupCommand entries.",
            f"Scheduled task preview collected: {len(scheduled_tasks)} tasks.",
            f"Run-key preview collected: {sum(len(entries) for entries in run_keys.values())} values.",
        ],
        "limitations": startup_limitations + task_limitations + run_key_limitations,
    }

