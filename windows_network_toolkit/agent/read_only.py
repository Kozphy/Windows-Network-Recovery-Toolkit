"""Read-only endpoint agent — evidence collection and JSONL spool only.

Module responsibility:
    Run observe-only collection cycles: gather endpoint evidence (live collectors or
    fixtures), append events to a local spool, emit observability metrics.

System placement:
    Invoked via ``python -m windows_network_toolkit agent *`` CLI. Does **not** call
    remediation executors listed in ``FORBIDDEN_REMEDIATION_MODULES``.

Key invariants:
    * ``READ_ONLY_POLICY_BOUNDARY`` = ``read_only_no_mutation``.
    * ``automatic_repair`` is always ``False`` on spool events.
    * Imports from ``windows_network_toolkit.safety.BLOCKED_ACTIONS`` for contract tests.

Side effects:
    Appends to spool JSONL (path from ``resolve_spool_path``); may increment in-memory
    operability counters.

Failure modes:
    Collector failures surface in evidence ``limitations``; spool write failures raise
    ``OSError`` to the CLI.

Audit Notes:
    Correlate spool ``collected_at_utc`` with ``trace_id`` / ``audit_id`` from
    ``observability_scope``. Spool files are local custody — not uploaded unless a
    separate sync path is configured.
"""

from __future__ import annotations

import json
import os
import signal
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from endpoint_agent.heartbeat import build_identity
from src.platform_core.evidence_collection import collect_endpoint_evidence
from src.platform_core.operability.context import (
    correlation_fields,
    new_audit_id,
    observability_scope,
    set_audit_id,
)
from src.platform_core.operability.events import (
    record_agent_heartbeat,
    record_evidence_collected,
    update_spool_queue_depth,
)
from windows_network_toolkit.agent.spool import (
    append_spool_event,
    read_last_spool_event,
    resolve_spool_path,
    spool_status,
)
from windows_network_toolkit.safety import BLOCKED_ACTIONS

READ_ONLY_POLICY_BOUNDARY = "read_only_no_mutation"
AGENT_VERSION = "0.2.0-read-only"

# Modules that must never be invoked from the read-only agent path (safety contract).
FORBIDDEN_REMEDIATION_MODULES = frozenset(
    {
        "windows_network_toolkit.proxy_remediation",
        "windows_network_toolkit.remediation.proxy_disable",
        "src.network_recovery.remediation_executor",
        "endpoint_agent.agent",
    }
)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def load_fixture_evidence(fixture_path: Path) -> dict[str, Any]:
    """Load evidence bundle from a JSON fixture file."""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if "evidence" in data and isinstance(data["evidence"], dict):
        return dict(data["evidence"])
    return dict(data)


def build_evidence_event(
    *,
    endpoint_id: str,
    os_family: str | None = None,
    fixture_path: Path | None = None,
) -> dict[str, Any]:
    """Normalize one read-only evidence collection cycle into a spool-ready event."""
    if fixture_path is not None:
        evidence = load_fixture_evidence(fixture_path)
        effective_os = str(evidence.get("os_family") or os_family or "unknown")
    else:
        evidence = collect_endpoint_evidence(os_family)  # type: ignore[arg-type]
        effective_os = str(evidence.get("os_family") or "unknown")

    return {
        "event_kind": "agent_evidence_collected",
        "endpoint_id": endpoint_id,
        "collected_at_utc": _utc_now(),
        "agent_version": AGENT_VERSION,
        "read_only": True,
        "automatic_repair": False,
        "remediation_executed": False,
        "policy_boundary": READ_ONLY_POLICY_BOUNDARY,
        "blocked_actions": sorted(BLOCKED_ACTIONS),
        "os_family": effective_os,
        "platform_support_level": evidence.get("platform_support_level"),
        "collector_id": evidence.get("collector_id"),
        "evidence": evidence,
        "limitations": list(evidence.get("limitations") or []),
    }


def collect_once(
    *,
    spool_path: Path | None = None,
    os_family: str | None = None,
    fixture_path: Path | None = None,
    endpoint_id: str | None = None,
) -> dict[str, Any]:
    """Run one read-only collection cycle and append to the local JSONL spool.

    Side effects:
        Appends one line to the spool file only — no registry/network mutation.

    Raises:
        OSError: Spool path not writable.
    """
    path = spool_path or resolve_spool_path(None)
    ident = endpoint_id or build_identity(agent_version=AGENT_VERSION).endpoint_id
    with observability_scope() as (trace_id, _):
        aid = new_audit_id()
        set_audit_id(aid)
        event = build_evidence_event(
            endpoint_id=ident,
            os_family=os_family,
            fixture_path=fixture_path,
        )
        event.update(correlation_fields())
        event["audit_id"] = aid
        append_spool_event(path, event)
        record_evidence_collected(endpoint_id=ident, source="read_only_agent")
        record_agent_heartbeat(endpoint_id=ident, health="ok")
        status = spool_status(path)
        update_spool_queue_depth(int(status["event_count"]))
    return {
        "status": "ok",
        "endpoint_id": ident,
        "spool_path": str(path),
        "event_kind": event["event_kind"],
        "read_only": True,
        "automatic_repair": False,
        "platform_support_level": event.get("platform_support_level"),
        "observation_count": len((event.get("evidence") or {}).get("observations") or []),
        "trace_id": trace_id,
        "audit_id": aid,
    }


def _shutdown_waiter(seconds: float) -> bool:
    """Sleep up to ``seconds``; return True when interrupt requested."""
    stop = threading.Event()

    def _on_signal(*_args: object) -> None:
        stop.set()

    try:
        signal.signal(signal.SIGINT, _on_signal)
        if os.name != "nt":
            signal.signal(signal.SIGTERM, _on_signal)
    except ValueError:
        pass
    return stop.wait(timeout=max(0.0, seconds))


def run_agent_loop(
    *,
    interval_seconds: float = 30.0,
    spool_path: Path | None = None,
    os_family: str | None = None,
    fixture_path: Path | None = None,
    max_cycles: int | None = None,
) -> int:
    """Run read-only collection cycles until interrupt or ``max_cycles`` reached."""
    interval = max(5.0, float(interval_seconds))
    cycles = 0
    while True:
        collect_once(
            spool_path=spool_path,
            os_family=os_family,
            fixture_path=fixture_path,
        )
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            return 0
        if _shutdown_waiter(interval):
            return 0


def probe_backend_health(api_base: str | None) -> dict[str, Any] | None:
    """Optional GET ``/health`` when a backend base URL is configured (read-only)."""
    if not api_base:
        return None
    base = api_base.rstrip("/")
    try:
        import httpx

        response = httpx.get(f"{base}/health", timeout=3.0)
        body: Any
        try:
            body = response.json()
        except json.JSONDecodeError:
            body = {"raw": response.text[:500]}
        return {
            "api_base": base,
            "reachable": True,
            "status_code": response.status_code,
            "body": body,
        }
    except Exception as exc:  # noqa: BLE001 — health probe is best-effort
        return {
            "api_base": base,
            "reachable": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }


def get_health_status(
    *,
    spool_path: Path | None = None,
    api_base: str | None = None,
) -> dict[str, Any]:
    """Return local agent health plus optional backend ``/health`` probe."""
    path = spool_path or resolve_spool_path(None)
    last = read_last_spool_event(path)
    status = spool_status(path)
    return {
        "agent_mode": "read_only",
        "health": "ok" if status["event_count"] > 0 else "idle",
        "read_only": True,
        "automatic_repair": False,
        "remediation_executed": False,
        "policy_boundary": READ_ONLY_POLICY_BOUNDARY,
        "blocked_actions": sorted(BLOCKED_ACTIONS),
        "agent_version": AGENT_VERSION,
        "spool": status,
        "last_event": last,
        "backend": probe_backend_health(api_base),
    }


def get_spool_status(spool_path: Path | None = None) -> dict[str, Any]:
    """Return spool depth and metadata (read-only inspection)."""
    path = spool_path or resolve_spool_path(None)
    return spool_status(path)
