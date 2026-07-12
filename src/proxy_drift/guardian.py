"""Dead localhost proxy guardian with configurable interval and confirmation gates."""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.logging.audit import append_jsonl
from src.proxy_drift.classify import classify_proxy_drift
from src.proxy_drift.proxy_fix import apply_proxy_fix
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.registry import read_proxy_registry

CONFIRM_CLEAR_DEAD = "CLEAR_DEAD_LOCALHOST_PROXY"
_SCHEMA = "proxy_guardian.v1"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _port_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            return True
    except OSError:
        return False


def _audit(log_path: Path, row: dict[str, Any]) -> None:
    """Dual-write: legacy JSONL under logs/ + hash-chained custody under WNT_AUDIT_DIR."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(log_path, row)
    try:
        from src.platform_core.audit.custody import append_custody_event

        event = str(row.get("event") or "guardian_check")
        append_custody_event(
            event,
            actor="proxy_guardian",
            subsystem="proxy_guardian",
            dry_run=row.get("dry_run"),
            confirmation_supplied=bool(row.get("action_taken") == "remediated"),
            before={
                "proxy_enable": row.get("proxy_enable"),
                "proxy_server": row.get("proxy_server"),
            },
            after=None,
            outcome=str(row.get("action_taken") or ""),
            limitations=list(row.get("limitations") or []),
            extra={
                "classification": row.get("classification"),
                "dead_localhost_proxy": row.get("dead_localhost_proxy"),
                "reason": row.get("reason"),
            },
            soft_fail=True,
        )
    except Exception:
        # Custody must not break guardian remediation path.
        pass


def run_dead_proxy_guardian_once(
    *,
    dry_run: bool = True,
    confirm: str = "",
    audit_path: Path | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Check for dead localhost WinINET proxy and optionally clear with confirmation."""
    subprocess_run = run if run is not None else subprocess.run
    log_path = audit_path or Path("logs") / "proxy_guardian.jsonl"
    reg = read_proxy_registry(run=subprocess_run)
    parsed = parse_proxy_server(reg.proxy_server)
    enabled = int(reg.proxy_enable or 0) == 1
    port = parsed.localhost_port
    listener = _port_listening(int(port)) if port else False
    classification = classify_proxy_drift(
        proxy_enable=reg.proxy_enable,
        proxy_server=reg.proxy_server,
        auto_config_url=reg.auto_config_url,
        listener_found=listener if port else None,
    )
    label = classification["classification"]
    dead = enabled and parsed.is_localhost_proxy and port and not listener

    result: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "dry_run": dry_run,
        "classification": label,
        "dead_localhost_proxy": dead,
        "proxy_enable": reg.proxy_enable,
        "proxy_server": reg.proxy_server,
        "localhost_port": port,
        "listener_found": listener,
        "action_taken": "none",
        "recommended_action": "No change required.",
        "limitations": classification.get("limitations") or [],
    }

    if not dead:
        result["reason"] = "No dead localhost proxy detected."
        _audit(log_path, {"event": "guardian_check", **result})
        return result

    result["recommended_action"] = (
        "Set ProxyEnable=0 and clear localhost ProxyServer (preview by default)."
    )
    if dry_run:
        result["action_taken"] = "preview_only"
        result["reason"] = "Dead localhost proxy detected; dry-run — no registry mutation."
        _audit(log_path, {"event": "guardian_preview", **result})
        return result

    if confirm != CONFIRM_CLEAR_DEAD:
        result["action_taken"] = "blocked"
        result["reason"] = f"Confirmation required: {CONFIRM_CLEAR_DEAD}"
        _audit(log_path, {"event": "guardian_blocked", **result})
        return result

    fix = apply_proxy_fix(
        dry_run=False,
        confirm="DISABLE_WININET_PROXY",
        clear_pac=False,
        run=subprocess_run,
    )
    result["remediation"] = fix
    result["action_taken"] = "remediated" if fix.get("action_allowed") else "blocked"
    result["reason"] = fix.get("reason") or "Guardian remediation completed."
    _audit(log_path, {"event": "guardian_apply", **result})
    return result


def run_dead_proxy_guardian_loop(
    *,
    interval_seconds: float = 60.0,
    once: bool = False,
    dry_run: bool = True,
    confirm: str = "",
    audit_path: Path | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run guardian checks on an interval until interrupted or ``once``."""
    subprocess_run = run if run is not None else subprocess.run
    log_path = audit_path or Path("logs") / "proxy_guardian.jsonl"
    interval = max(1.0, interval_seconds)
    cycles = 0
    last: dict[str, Any] = {}
    while True:
        last = run_dead_proxy_guardian_once(
            dry_run=dry_run,
            confirm=confirm,
            audit_path=log_path,
            run=subprocess_run,
        )
        cycles += 1
        if once:
            break
        time.sleep(interval)
    return {"cycles": cycles, "last_result": last}
