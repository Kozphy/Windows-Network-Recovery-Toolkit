"""Install/uninstall WNRT-DeadProxyGuardian scheduled task at user logon."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

TASK_NAME = "WNRT-DeadProxyGuardian"
CONFIRM_INSTALL = "INSTALL_GUARDIAN_TASK"
CONFIRM_UNINSTALL = "UNINSTALL_GUARDIAN_TASK"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _python_exe() -> str:
    return sys.executable


def build_guardian_task_command(*, interval: int = 60) -> str:
    """Return the command line the scheduled task should execute."""
    py = _python_exe()
    return (
        f'"{py}" -m src proxy-guardian --loop --interval {interval} '
        f"--confirm CLEAR_DEAD_LOCALHOST_PROXY --dry-run false"
    )


def build_schtasks_create_preview(*, interval: int = 60) -> tuple[str, ...]:
    """Return argv for ``schtasks /Create`` (preview only)."""
    cmd = build_guardian_task_command(interval=interval)
    return (
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/SC",
        "ONLOGON",
        "/RL",
        "LIMITED",
        "/F",
        "/TR",
        cmd,
    )


def preview_install_guardian_task(*, interval: int = 60) -> dict[str, Any]:
    """Return human-readable preview of the scheduled task without creating it."""
    argv = build_schtasks_create_preview(interval=interval)
    return {
        "schema_version": "guardian_task.v1",
        "timestamp_utc": _now(),
        "task_name": TASK_NAME,
        "trigger": "ONLOGON",
        "command": build_guardian_task_command(interval=interval),
        "schtasks_argv": list(argv),
        "schtasks_command": subprocess.list2cmdline(list(argv)),
        "confirmation_required": CONFIRM_INSTALL,
        "limitations": [
            "Task creation mutates Windows scheduler — preview shown first.",
            "Guardian only clears dead localhost proxies with typed confirmation.",
        ],
    }


def install_guardian_task(
    *,
    interval: int = 60,
    confirm: str = "",
    dry_run: bool = True,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Create logon scheduled task when confirmed."""
    subprocess_run = run if run is not None else subprocess.run
    preview = preview_install_guardian_task(interval=interval)
    if dry_run:
        preview["action_taken"] = "preview_only"
        preview["reason"] = "Dry-run — task not created."
        return preview
    if confirm != CONFIRM_INSTALL:
        preview["action_taken"] = "blocked"
        preview["reason"] = f"Confirmation required: {CONFIRM_INSTALL}"
        return preview
    argv = tuple(preview["schtasks_argv"])
    proc = subprocess_run(argv, capture_output=True, text=True, timeout=60, shell=False)
    preview["returncode"] = proc.returncode
    preview["stdout"] = (proc.stdout or "").strip()
    preview["stderr"] = (proc.stderr or "").strip()
    preview["action_taken"] = "installed" if proc.returncode == 0 else "failed"
    preview["reason"] = "Scheduled task created." if proc.returncode == 0 else "schtasks failed."
    return preview


def uninstall_guardian_task(
    *,
    confirm: str = "",
    dry_run: bool = True,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Remove the guardian scheduled task when confirmed."""
    subprocess_run = run if run is not None else subprocess.run
    argv = ("schtasks", "/Delete", "/TN", TASK_NAME, "/F")
    payload: dict[str, Any] = {
        "schema_version": "guardian_task.v1",
        "timestamp_utc": _now(),
        "task_name": TASK_NAME,
        "schtasks_argv": list(argv),
        "schtasks_command": subprocess.list2cmdline(list(argv)),
        "confirmation_required": CONFIRM_UNINSTALL,
    }
    if dry_run:
        payload["action_taken"] = "preview_only"
        payload["reason"] = "Dry-run — task not deleted."
        return payload
    if confirm != CONFIRM_UNINSTALL:
        payload["action_taken"] = "blocked"
        payload["reason"] = f"Confirmation required: {CONFIRM_UNINSTALL}"
        return payload
    proc = subprocess_run(argv, capture_output=True, text=True, timeout=60, shell=False)
    payload["returncode"] = proc.returncode
    payload["stdout"] = (proc.stdout or "").strip()
    payload["stderr"] = (proc.stderr or "").strip()
    payload["action_taken"] = "uninstalled" if proc.returncode == 0 else "failed"
    payload["reason"] = "Scheduled task removed." if proc.returncode == 0 else "schtasks delete failed."
    return payload
