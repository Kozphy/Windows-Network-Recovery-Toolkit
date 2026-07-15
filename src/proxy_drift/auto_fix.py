"""One-shot dead localhost proxy auto-fix and optional guardian install."""

from __future__ import annotations

import platform
import socket
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.proxy_drift.classify import classify_proxy_drift
from src.proxy_drift.guardian import CONFIRM_CLEAR_DEAD, run_dead_proxy_guardian_once
from src.proxy_drift.proxy_fix import apply_proxy_fix
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.registry import read_proxy_registry
from src.proxy_guard.remediation import CONFIRMATION_PHRASE

_DEAD_CLASSIFICATIONS = frozenset(
    {
        "STALE_LOCALHOST_PROXY",
        "STALE_PROXY_AFTER_PROCESS_EXIT",
        "DEAD_PROXY_CONFIG",
    }
)
_SCHEMA = "auto_fix_proxy.v1"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _port_listening(port: int | None) -> bool | None:
    if port is None:
        return None
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.35):
            return True
    except OSError:
        return False


def read_proxy_drift_status(*, run: Callable[..., Any] | None = None) -> dict[str, Any]:
    """Return current WinINET proxy drift classification (read-only)."""
    subprocess_run = run if run is not None else subprocess.run
    reg = read_proxy_registry(run=subprocess_run)
    parsed = parse_proxy_server(reg.proxy_server)
    listener = _port_listening(parsed.localhost_port)
    classification = classify_proxy_drift(
        proxy_enable=reg.proxy_enable,
        proxy_server=reg.proxy_server,
        auto_config_url=reg.auto_config_url,
        listener_found=listener,
    )
    label = str(classification.get("classification") or "")
    legacy = label
    if label in {"STALE_LOCALHOST_PROXY", "STALE_PROXY_AFTER_PROCESS_EXIT"}:
        legacy = "DEAD_PROXY_CONFIG"
    enabled = int(reg.proxy_enable or 0) == 1
    if not enabled and not parsed.raw:
        legacy = "NO_PROXY"
    return {
        "timestamp_utc": _now(),
        "classification": label,
        "legacy_classification": legacy,
        "is_dead_localhost_proxy": label in _DEAD_CLASSIFICATIONS,
        "proxy_enable": reg.proxy_enable,
        "proxy_server": reg.proxy_server,
        "localhost_port": parsed.localhost_port,
        "listener_found": listener,
        "limitations": classification.get("limitations") or [],
    }


def _run_cursor_no_proxy_script(repo_root: Path, run: Callable[..., Any]) -> dict[str, Any]:
    script = repo_root / "scripts" / "configure-cursor-no-proxy.ps1"
    if not script.is_file():
        return {"step": "cursor_no_proxy", "skipped": True, "reason": "script missing"}
    proc = run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(repo_root),
    )
    return {
        "step": "cursor_no_proxy",
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-2000:],
        "stderr": (proc.stderr or "").strip()[-2000:],
    }


def _install_guardian_loop(
    repo_root: Path,
    *,
    interval_seconds: int,
    run: Callable[..., Any],
) -> dict[str, Any]:
    script = repo_root / "scripts" / "install-dead-proxy-guardian.ps1"
    if not script.is_file():
        return {"step": "guardian_install", "skipped": True, "reason": "installer missing"}
    interval_minutes = max(1, (interval_seconds + 59) // 60)
    proc = run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-IntervalSeconds",
            str(interval_seconds),
            "-IntervalMinutes",
            str(interval_minutes),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(repo_root),
    )
    return {
        "step": "guardian_install",
        "interval_seconds": interval_seconds,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-3000:],
        "stderr": (proc.stderr or "").strip()[-2000:],
    }


def run_auto_fix_proxy(
    *,
    dry_run: bool = False,
    skip_guardian_install: bool = False,
    skip_cursor_fix: bool = False,
    guardian_interval_seconds: int = 60,
    prefer_direct: bool = False,
    confirm: str = "",
    repo_root: Path | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Clear dead localhost WinINET proxy and install background guardian when safe.

    Optional ``prefer_direct`` (requires confirm ``PREFER_DIRECT_WININET``) also clears
    an *active* localhost proxy (KNOWN_DEV_PROXY / Cursor Node listener).
    """
    if platform.system() != "Windows":
        return {
            "schema_version": _SCHEMA,
            "unsupported_platform": True,
            "platform": platform.system(),
            "outcome": "unsupported",
        }

    from src.proxy_drift.ensure_health import CONFIRM_PREFER_DIRECT

    subprocess_run = run if run is not None else subprocess.run
    repo = (repo_root or Path.cwd()).resolve()
    steps: list[dict[str, Any]] = []

    if not skip_cursor_fix and not dry_run:
        steps.append(_run_cursor_no_proxy_script(repo, subprocess_run))

    before = read_proxy_drift_status(run=subprocess_run)
    steps.append({"step": "status_before", "result": before})

    guardian = run_dead_proxy_guardian_once(
        dry_run=dry_run,
        confirm=CONFIRM_CLEAR_DEAD if not dry_run else "",
        run=subprocess_run,
    )
    steps.append({"step": "proxy_guardian", "result": guardian})

    after_guardian = read_proxy_drift_status(run=subprocess_run)
    steps.append({"step": "status_after_guardian", "result": after_guardian})

    fix_result: dict[str, Any] | None = None
    if after_guardian.get("is_dead_localhost_proxy") and not dry_run:
        fix_result = apply_proxy_fix(
            dry_run=False,
            confirm=CONFIRMATION_PHRASE,
            clear_pac=False,
            run=subprocess_run,
        )
        steps.append({"step": "proxy_fix_fallback", "result": fix_result})

    prefer_result: dict[str, Any] | None = None
    after_dead = read_proxy_drift_status(run=subprocess_run)
    localhost_enabled = (
        int(after_dead.get("proxy_enable") or 0) == 1 and after_dead.get("localhost_port") is not None
    )
    if prefer_direct and localhost_enabled:
        if dry_run:
            prefer_result = {
                "action_taken": "preview_only",
                "reason": f"Would clear active localhost WinINET proxy (confirm {CONFIRM_PREFER_DIRECT}).",
                "proxy_server": after_dead.get("proxy_server"),
            }
        elif confirm != CONFIRM_PREFER_DIRECT:
            prefer_result = {
                "action_taken": "blocked",
                "reason": f"Confirmation required: {CONFIRM_PREFER_DIRECT}",
                "proxy_server": after_dead.get("proxy_server"),
            }
        else:
            prefer_result = apply_proxy_fix(
                dry_run=False,
                confirm=CONFIRMATION_PHRASE,
                clear_pac=False,
                run=subprocess_run,
            )
            prefer_result["prefer_direct"] = True
        steps.append({"step": "prefer_direct", "result": prefer_result})

    final = read_proxy_drift_status(run=subprocess_run)
    steps.append({"step": "status_final", "result": final})

    if not skip_guardian_install and not dry_run:
        steps.append(
            _install_guardian_loop(
                repo,
                interval_seconds=guardian_interval_seconds,
                run=subprocess_run,
            )
        )

    final_localhost = (
        int(final.get("proxy_enable") or 0) == 1 and final.get("localhost_port") is not None
    )
    if final.get("is_dead_localhost_proxy"):
        outcome = "would_remediate" if dry_run else "still_dead"
    elif prefer_direct and localhost_enabled and prefer_result and prefer_result.get("action_taken") == "blocked":
        outcome = "needs_prefer_direct_confirm"
    elif final_localhost:
        outcome = "localhost_proxy_active"
    else:
        outcome = "healthy"

    return {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "dry_run": dry_run,
        "prefer_direct": prefer_direct,
        "outcome": outcome,
        "classification": final.get("classification"),
        "legacy_classification": final.get("legacy_classification"),
        "steps": steps,
        "limitations": [
            "Default auto-fix clears dead localhost WinINET proxy only — not corporate proxy policy.",
            "prefer_direct also clears active localhost proxies; may break intentional local tunnels.",
            "Listener correlation is not registry writer proof.",
            "Background guardian only remediates dead (no-listener) proxies unless prefer-direct is used.",
        ],
    }
