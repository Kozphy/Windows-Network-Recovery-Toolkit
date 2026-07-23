"""Dead / active-but-broken localhost proxy guardian with confirmation gates."""

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
# Same token as ensure/auto-fix prefer-direct — clears listener-up path failures only.
CONFIRM_CLEAR_BROKEN = "PREFER_DIRECT_WININET"
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
                "broken_localhost_proxy": row.get("broken_localhost_proxy"),
                "reason": row.get("reason"),
            },
            soft_fail=True,
        )
    except Exception:
        # Custody must not break guardian remediation path.
        pass


def _assess_broken(
    *,
    enabled: bool,
    is_localhost: bool,
    port: int | None,
    listener: bool,
    path_health: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    """Return (is_broken, path_probe_dict) for listener-up path failures."""
    if not (enabled and is_localhost and port and listener):
        return False, {}
    # Lazy import avoids circular import with auto_fix → guardian.
    from src.proxy_drift.auto_fix import assess_localhost_proxy_path

    path = assess_localhost_proxy_path(int(port), inject=path_health)
    proxy_ok = path.get("proxy_probe_ok")
    direct_ok = path.get("direct_probe_ok")
    broken = proxy_ok is False and direct_ok is True
    return broken, path


def run_dead_proxy_guardian_once(
    *,
    dry_run: bool = True,
    confirm: str = "",
    clear_broken: bool = False,
    confirm_broken: str = "",
    path_health: dict[str, Any] | None = None,
    audit_path: Path | None = None,
    run: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Check for dead or active-but-broken localhost WinINET proxy; optionally clear.

    Dead (no listener) requires ``confirm == CLEAR_DEAD_LOCALHOST_PROXY``.

    Active-but-broken (listener up, proxy path fail, direct HTTPS ok) is checked
    only when ``clear_broken`` is true, and live clear requires
    ``confirm_broken == PREFER_DIRECT_WININET``. Healthy active localhost proxies
    are never cleared by the guardian.
    """
    subprocess_run = run if run is not None else subprocess.run
    log_path = audit_path or Path("logs") / "proxy_guardian.jsonl"
    reg = read_proxy_registry(run=subprocess_run)
    parsed = parse_proxy_server(reg.proxy_server)
    enabled = int(reg.proxy_enable or 0) == 1
    port = parsed.localhost_port
    listener = _port_listening(int(port)) if port else False

    broken = False
    path: dict[str, Any] = {}
    proxy_probe_ok: bool | None = None
    direct_probe_ok: bool | None = None
    if clear_broken and enabled and parsed.is_localhost_proxy and port and listener:
        broken, path = _assess_broken(
            enabled=enabled,
            is_localhost=parsed.is_localhost_proxy,
            port=port,
            listener=listener,
            path_health=path_health,
        )
        raw_p = path.get("proxy_probe_ok")
        raw_d = path.get("direct_probe_ok")
        proxy_probe_ok = raw_p if isinstance(raw_p, bool) else None
        direct_probe_ok = raw_d if isinstance(raw_d, bool) else None

    classification = classify_proxy_drift(
        proxy_enable=reg.proxy_enable,
        proxy_server=reg.proxy_server,
        auto_config_url=reg.auto_config_url,
        listener_found=listener if port else None,
        proxy_probe_ok=proxy_probe_ok,
        direct_probe_ok=direct_probe_ok,
    )
    label = classification["classification"]
    dead = bool(enabled and parsed.is_localhost_proxy and port and not listener)
    # Prefer dead over broken if somehow both (shouldn't happen).
    if dead:
        broken = False

    limitations = list(classification.get("limitations") or [])
    if clear_broken:
        limitations.append(
            "clear_broken only remediates listener-up path failures (direct ok); "
            "healthy active localhost proxies are left alone."
        )

    result: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "dry_run": dry_run,
        "classification": label,
        "dead_localhost_proxy": dead,
        "broken_localhost_proxy": broken,
        "clear_broken": clear_broken,
        "proxy_enable": reg.proxy_enable,
        "proxy_server": reg.proxy_server,
        "localhost_port": port,
        "listener_found": listener,
        "proxy_probe_ok": proxy_probe_ok,
        "direct_probe_ok": direct_probe_ok,
        "proxy_status": path.get("proxy_status"),
        "action_taken": "none",
        "recommended_action": "No change required.",
        "limitations": limitations,
    }

    if not dead and not broken:
        result["reason"] = (
            "No dead localhost proxy detected."
            if not clear_broken
            else "No dead or active-but-broken localhost proxy detected."
        )
        _audit(log_path, {"event": "guardian_check", **result})
        return result

    if dead:
        result["recommended_action"] = (
            "Set ProxyEnable=0 and clear localhost ProxyServer (preview by default)."
        )
        required = CONFIRM_CLEAR_DEAD
        confirm_ok = confirm == CONFIRM_CLEAR_DEAD
        event_preview = "guardian_preview"
        event_blocked = "guardian_blocked"
        event_apply = "guardian_apply"
        preview_reason = "Dead localhost proxy detected; dry-run — no registry mutation."
        blocked_reason = f"Confirmation required: {CONFIRM_CLEAR_DEAD}"
    else:
        result["recommended_action"] = (
            "Clear active-but-broken localhost WinINET proxy "
            f"(confirm {CONFIRM_CLEAR_BROKEN})."
        )
        required = CONFIRM_CLEAR_BROKEN
        confirm_ok = confirm_broken == CONFIRM_CLEAR_BROKEN
        event_preview = "guardian_broken_preview"
        event_blocked = "guardian_broken_blocked"
        event_apply = "guardian_broken_apply"
        preview_reason = (
            "Active-but-broken localhost proxy detected; dry-run — no registry mutation."
        )
        blocked_reason = f"Confirmation required: {CONFIRM_CLEAR_BROKEN}"

    if dry_run:
        result["action_taken"] = "preview_only"
        result["reason"] = preview_reason
        result["confirmation_required"] = required
        _audit(log_path, {"event": event_preview, **result})
        return result

    if not confirm_ok:
        result["action_taken"] = "blocked"
        result["reason"] = blocked_reason
        result["confirmation_required"] = required
        _audit(log_path, {"event": event_blocked, **result})
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
    if broken:
        result["cleared_broken_localhost"] = True
    _audit(log_path, {"event": event_apply, **result})
    return result


def run_dead_proxy_guardian_loop(
    *,
    interval_seconds: float = 60.0,
    once: bool = False,
    dry_run: bool = True,
    confirm: str = "",
    clear_broken: bool = False,
    confirm_broken: str = "",
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
            clear_broken=clear_broken,
            confirm_broken=confirm_broken,
            audit_path=log_path,
            run=subprocess_run,
        )
        cycles += 1
        if once:
            break
        time.sleep(interval)
    return {"cycles": cycles, "last_result": last}
