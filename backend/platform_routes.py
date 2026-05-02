"""FastAPI ``/platform/*`` routes for the optional Endpoint Reliability Platform prototype.

Module responsibility:
    Exposes heartbeat ingestion, sanitized snapshots/failure-event rows, deterministic remediation
    preview/execute, read-only audits (RBAC gated), and JSONL-derived metrics—all backed by
    :mod:`platform_core.storage` without an external database.

System placement:
    Mounted by ``backend/main.py``. The ``endpoint_agent`` package POSTs rows here when
    configured; standalone ``failure_system`` / ``python -m src`` flows do **not** require this
    router.

Key invariants:
    * Storage stays append-only JSONL; duplicate heartbeats imply “latest wins” readers.
    * Remediation executes only after a persisted preview ``preview_id`` resolves.
    * Live subprocess repair runs only when policy, registry tiering, confirmations, OS, script
      allowlisting, and ``SAFE_MODE`` / env gates align (see body of :func:`remediation_execute`).
    * Timestamps originate from agent/backend models (:func:`platform_core.models.utc_now_iso`);
      no implicit timezone normalization beyond UTC ISO helpers in models.

Input assumptions:
    Request bodies validate via Pydantic models declared below; remediation actions must resolve in
    :mod:`platform_core.remediation_registry`. Operator identity for RBAC derives from optional
    ``X-Operator-Id`` / ``X-Operator-Role`` headers parsed by :func:`get_demo_principal`.

Output guarantees:
    JSON payloads are plain ``dict[str, Any]`` suitable for FastAPI serialization; audits return
    redacted rationales tied to policy decisions.

Side effects:
    Every mutating handler appends JSONL via storage helpers **and** calls
    :func:`platform_core.audit.write_audit` where operator visibility matters. Successful live
    execution invokes ``subprocess.run`` on allowlisted repo-relative ``.bat`` scripts (Windows).

Idempotency:
    Retried POST bodies create **new** append rows; executions are not keyed for deduplication beyond
    caller-supplied UUID fields inside models.

Routes (summary):
    * ``GET /platform/health`` — build metadata + JSONL directory.
    * ``POST /platform/agent/heartbeat`` — register endpoint identity.
    * ``POST /platform/snapshots`` — ingest :class:`~platform_core.models.EndpointSnapshot`.
    * ``GET /platform/endpoints`` / ``GET /platform/endpoints/{id}`` — latest merged heartbeats.
    * ``GET/POST .../failure-events`` — list/ingest :class:`~platform_core.models.FailureEvent`.
    * ``POST /platform/remediation/preview|execute`` — policy-gated remediation pipeline.
    * ``GET /platform/audit`` — recent audit rows (RBAC reader role).
    * ``GET /platform/metrics`` — aggregate counters scanning JSONL (demo scale).
    * ``GET /platform/events`` — normalized envelopes (requires operator+/RBAC simulation).
    * ``GET /platform/policy/summary`` — registry roll-up for dashboards.
    * ``POST /platform/replay/preview`` — inline replay summaries (local-only-safe).

Audit Notes:
    Correlate ``audit.jsonl`` with ``remediation_executions.jsonl`` after contested runs. Treat
    ``SAFE_MODE``, ``ALLOW_PLATFORM_EXECUTE``, and blocked executions as authoritative signals—even
    when HTTP responses return 200 with ``result=blocked``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from platform_core.audit import write_audit
from platform_core.models import (
    EndpointIdentity,
    EndpointSnapshot,
    FailureEvent,
    RemediationExecution,
    RemediationPreview,
    utc_now_iso,
)
from platform_core.policy import (
    ACTION_REGISTRY,
    PolicyDecision,
    build_preview,
    evaluate_action,
    is_shell_injection,
    validate_confirmation_phrase,
)
from platform_core.rbac import (
    DemoPrincipal,
    assert_can_execute,
    assert_can_preview,
    assert_can_read_audit,
    parse_demo_principal,
)
from platform_core.remediation_registry import get_remediation_action
from platform_core.fleet import linked_failure_block_payload
from platform_core.privacy import redact_text, stable_endpoint_hash
from platform_core.remediation import allowlisted_script
from platform_core.event_bus import default_normalized_events_path, read_events
from platform_core.replay.runner import ReplaySummary, summarize_inline
from platform_core.storage import (
    append_failure_event,
    append_remediation_execution,
    append_remediation_preview,
    append_snapshot,
    find_by_id,
    list_metrics,
    platform_data_dir,
    read_recent_jsonl,
    upsert_endpoint,
    _path,
)

router = APIRouter(prefix="/platform", tags=["platform"])

SAFE_MODE = os.environ.get("PLATFORM_SAFE_MODE", "1") != "0"
BACKEND_VERSION = "0.3.0-platform-enterprise-demo"


def get_demo_principal(
    x_operator_id: str | None = Header(default=None),
    x_operator_role: str | None = Header(default=None),
) -> DemoPrincipal:
    """FastAPI dependency that maps optional operator headers into a demo :class:`~platform_core.rbac.DemoPrincipal`.

    Args:
        x_operator_id: Optional ``X-Operator-Id`` header (portfolio demo identifier).
        x_operator_role: Optional ``X-Operator-Role`` header controlling preview vs execute vs
            audit readability.

    Returns:
        Parsed principal with deterministic defaults documented in :mod:`platform_core.rbac`.

    Side effects:
        None — malformed header combinations fall back per :func:`~platform_core.rbac.parse_demo_principal`.
    """

    return parse_demo_principal(x_operator_id, x_operator_role)


class HealthResponse(BaseModel):
    status: str = "ok"
    backend_version: str = BACKEND_VERSION
    platform_mode: str = "local_jsonl"
    safe_mode: bool = True
    data_dir: str = ""


@router.get("/health", response_model=HealthResponse)
def platform_health() -> dict[str, Any]:
    """Expose process version flags, JSONL mode, ``SAFE_MODE`` snapshot, and data directory."""

    return {
        "status": "ok",
        "backend_version": BACKEND_VERSION,
        "platform_mode": "local_jsonl",
        "safe_mode": SAFE_MODE,
        "data_dir": str(platform_data_dir()),
    }


class HeartbeatIn(BaseModel):
    endpoint_id: str
    os_family: str = ""
    os_version: str = ""
    agent_version: str = ""


@router.post("/agent/heartbeat")
def agent_heartbeat(body: HeartbeatIn) -> dict[str, Any]:
    """Append an :class:`~platform_core.models.EndpointIdentity` heartbeat plus matching audit row."""

    ident = EndpointIdentity(
        endpoint_id=body.endpoint_id,
        os_family=body.os_family,
        os_version=body.os_version,
        agent_version=body.agent_version,
        last_seen_at=utc_now_iso(),
    )
    upsert_endpoint(ident.model_dump())
    write_audit(actor="agent", action="heartbeat", target_type="endpoint", target_id=body.endpoint_id)
    return {"stored": True, "endpoint_id": body.endpoint_id}


@router.post("/snapshots")
def post_snapshot(snapshot: EndpointSnapshot) -> dict[str, Any]:
    """Persist a privacy-scrubbed :class:`~platform_core.models.EndpointSnapshot` row."""

    append_snapshot(snapshot.model_dump())
    write_audit(actor="agent", action="snapshot", target_type="endpoint", target_id=snapshot.endpoint_id)
    return {"stored": True}


@router.get("/endpoints")
def list_endpoints() -> dict[str, Any]:
    """Return merged endpoint dicts keyed by ``endpoint_id`` (latest heartbeat wins within scan)."""

    seen: dict[str, dict[str, Any]] = {}
    for row in read_recent_jsonl(_path("endpoints.jsonl"), limit=2000):
        eid = row.get("endpoint_id")
        if isinstance(eid, str):
            seen[eid] = row
    return {"endpoints": list(seen.values())}


@router.get("/endpoints/{endpoint_id}")
def get_endpoint(endpoint_id: str) -> dict[str, Any]:
    """Fetch newest heartbeat dict for ``endpoint_id``."""

    row = find_by_id(_path("endpoints.jsonl"), "endpoint_id", endpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="endpoint not found")
    return row


@router.get("/failure-events")
def list_failure_events(limit: int = 100) -> dict[str, Any]:
    """Return capped recent failure-event rows newest-first semantics via :func:`read_recent_jsonl`."""

    rows = read_recent_jsonl(_path("failure_events.jsonl"), limit=max(1, min(limit, 500)))
    return {"items": rows}


@router.post("/failure-events/ingest")
def ingest_failure_event(body: FailureEvent) -> dict[str, Any]:
    """Append one sanitized :class:`~platform_core.models.FailureEvent` originating from collectors.

    Side effects:
        Writes ``failure_events.jsonl`` plus an audit row referencing ``event_id``.

    Note:
        Invalid payloads return FastAPI 422 responses rather than bespoke ``HTTPException`` rows.
    """
    append_failure_event(body.model_dump())
    write_audit(actor="agent", action="failure_event_ingest", target_type="event", target_id=body.event_id)
    return {"stored": True, "event_id": body.event_id}


@router.get("/failure-events/{event_id}")
def get_failure_event(event_id: str) -> dict[str, Any]:
    """Hydrate stored JSON plus optional FailureBlock-derived linkage via fleet helpers."""

    row = find_by_id(_path("failure_events.jsonl"), "event_id", event_id)
    if not row:
        raise HTTPException(status_code=404, detail="event not found")
    fb_raw = row.get("failure_block_id") if isinstance(row.get("failure_block_id"), str) else ""
    return {
        "failure_event": row,
        "failure_block_linked": linked_failure_block_payload(fb_raw),
    }


class PreviewIn(BaseModel):
    endpoint_id: str
    failure_event_id: str
    requested_action: str
    surface: Literal["api", "cli", "dashboard"] = "api"


@router.post("/remediation/preview")
def remediation_preview(
    body: PreviewIn,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Hydrate stored failure-event JSON, derive remediation preview rows, persist policy outcome.

    Args:
        body: Endpoint + failure event linkage plus requested remediation action slug.
        principal: Resolved via :func:`get_demo_principal` for RBAC gating.

    Returns:
        Serialized :class:`~platform_core.models.RemediationPreview` suitable for dashboards.

    Raises:
        HTTPException: 403 when RBAC forbids previews, 400 on shell injection heuristics, 404 when
            the referenced failure-event id is absent.

    Side effects:
        Appends ``remediation_previews.jsonl`` plus an audit entry carrying policy rationale.

    Engineering Notes:
        ``build_preview`` performs pure policy derivation; deterministic replays rely on immutable
        failure-event payloads.

    Audit Notes:
        Compare ``policy_reason`` embedded in previews with audits when auditors challenge blocks.
    """
    assert_can_preview(principal)
    if is_shell_injection(body.requested_action):
        raise HTTPException(status_code=400, detail="invalid action")
    ev_row = find_by_id(_path("failure_events.jsonl"), "event_id", body.failure_event_id)
    if not ev_row:
        raise HTTPException(status_code=404, detail="failure event not found")
    fe = FailureEvent.model_validate(ev_row)
    preview = build_preview(fe, body.requested_action, requested_surface=body.surface)
    append_remediation_preview(preview.model_dump())
    write_audit(
        actor=principal.operator_id,
        action="remediation_preview",
        target_type="failure_event",
        target_id=body.failure_event_id,
        decision="allowed" if preview.allowed_by_policy else "blocked",
        rationale=preview.policy_reason,
    )
    return preview.model_dump()


class ExecuteIn(BaseModel):
    preview_id: str
    confirmation_phrase: str = ""
    dry_run: bool = True
    actor: str = "operator_local"


@router.post("/remediation/execute")
def remediation_execute(
    body: ExecuteIn,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Finalize remediation by rehydrating previews, enforcing policy tiers, optionally running scripts.

    Args:
        body: Preview identifier, typed confirmation phrase, dry-run toggle, informational actor slug.
        principal: RBAC-bound operator used for confirmations and auditing.

    Returns:
        Serialized :class:`~platform_core.models.RemediationExecution` documenting ``dry_run``,
        ``blocked``, ``success``, or ``failure``.

    Raises:
        HTTPException: 403 RBAC denial, 404 missing preview, 400 unknown action/disallowed script,
            400 typed confirmation mismatches.

    Side effects:
        Always appends ``remediation_executions.jsonl``. Live Windows paths invoke ``cmd /c`` on
        repo-allowlisted bat files with redacted stdout/stderr caps; timeouts append failure rows.

    Idempotency:
        Not idempotent—each invocation issues a fresh ``execution_id`` even for identical payloads.

    Failure modes:
        Non-Windows hosts short-circuit to failure executions. Preview/policy drift yields blocked
        rows without subprocess execution.

    Audit Notes:
        Blocked executions still append JSONL rows—grep ``result`` + ``audit`` rows when operators
        report “silent failures.” Inspect redacted stderr for scripting errors; widen caps only with
        privacy review (:mod:`platform_core.privacy`).
    """
    assert_can_execute(principal, dry_run=body.dry_run)
    if not SAFE_MODE and os.environ.get("ALLOW_PLATFORM_EXECUTE") != "1":
        pass  # still enforce policy
    prev_row = find_by_id(_path("remediation_previews.jsonl"), "preview_id", body.preview_id)
    if not prev_row:
        raise HTTPException(status_code=404, detail="preview not found")
    preview = RemediationPreview.model_validate(prev_row)
    action_name = preview.proposed_action
    defn = get_remediation_action(action_name)
    if defn is None:
        raise HTTPException(status_code=400, detail="unknown action")

    pd: PolicyDecision = evaluate_action(action_name, "api")
    if not pd.allowed:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="blocked",
            stderr_redacted=pd.reason,
        )
        append_remediation_execution(ex.model_dump())
        write_audit(
            actor=principal.operator_id,
            action="execute",
            decision="blocked",
            rationale=pd.reason,
        )
        return ex.model_dump()

    if preview.requires_typed_confirmation:
        if not validate_confirmation_phrase(action_name, body.confirmation_phrase):
            raise HTTPException(status_code=400, detail="confirmation_phrase mismatch")

    if not body.dry_run and (defn.manual_only or not defn.api_execute_allowed):
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="blocked",
            stderr_redacted="manual_only_or_api_execute_disabled",
        )
        append_remediation_execution(ex.model_dump())
        write_audit(
            actor=principal.operator_id,
            action="execute",
            decision="blocked",
            rationale="manual_only_or_api_execute_disabled",
        )
        return ex.model_dump()

    script = defn.script_path
    if body.dry_run or script is None:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="dry_run",
            stdout_redacted="[dry-run] no subprocess",
        )
        append_remediation_execution(ex.model_dump())
        return ex.model_dump()

    if sys.platform != "win32":
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="failure",
            stderr_redacted="execution_only_supported_on_windows",
        )
        append_remediation_execution(ex.model_dump())
        return ex.model_dump()

    path = allowlisted_script(str(script), _REPO_ROOT)
    if path is None:
        raise HTTPException(status_code=400, detail="script not allowlisted")

    try:
        proc = subprocess.run(
            ["cmd", "/c", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
            cwd=str(_REPO_ROOT),
        )
        out = redact_text((proc.stdout or "")[:4000])
        err = redact_text((proc.stderr or "")[:4000])
        ok = proc.returncode == 0
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="success" if ok else "failure",
            stdout_redacted=out,
            stderr_redacted=err,
        )
        append_remediation_execution(ex.model_dump())
        write_audit(
            actor=principal.operator_id,
            action="execute",
            target_type="preview",
            target_id=body.preview_id,
            decision="success" if ok else "failure",
        )
        return ex.model_dump()
    except subprocess.TimeoutExpired:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=principal.operator_id,
            result="failure",
            stderr_redacted="timeout",
        )
        append_remediation_execution(ex.model_dump())
        return ex.model_dump()


@router.get("/audit")
def platform_audit(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """RBAC-filtered slice of newest ``audit.jsonl`` rows."""

    assert_can_read_audit(principal)
    return {"items": read_recent_jsonl(_path("audit.jsonl"), limit=max(1, min(limit, 200)))}


@router.get("/metrics")
def platform_metrics() -> dict[str, Any]:
    """Expose aggregate counters recomputed via :func:`platform_core.storage.list_metrics`."""

    return list_metrics()


@router.get("/events")
def list_normalized_events(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Read privacy-scrubbed normalized events emitted to ``normalized_events.jsonl``."""

    assert_can_preview(principal)
    path = default_normalized_events_path()
    items, errs = read_events(path, limit=max(1, min(limit, 200)))
    return {"items": items, "parse_errors": errs, "path": str(path)}


@router.get("/policy/summary")
def policy_catalog_summary() -> dict[str, Any]:
    """Static view of allowlisted remediation metadata (counts by risk tier)."""

    by_risk: dict[str, int] = defaultdict(int)
    manual_only = 0
    api_exec = 0
    for _name, meta in ACTION_REGISTRY.items():
        if not isinstance(meta, dict):
            continue
        rk = str(meta.get("risk") or "unknown")
        by_risk[rk] += 1
        if meta.get("manual_only"):
            manual_only += 1
        if meta.get("api_execute_allowed"):
            api_exec += 1
    return {
        "action_rows": len(ACTION_REGISTRY),
        "by_risk": dict(by_risk),
        "manual_only_rows": manual_only,
        "api_execute_allowed_rows": api_exec,
        "default_policy_requires_confirmation": True,
    }


class ReplayPreviewIn(BaseModel):
    """Inline JSON array for deterministic replay — **no filesystem path escalation**."""

    events: list[dict[str, Any]]


@router.post("/replay/preview")
def replay_preview(
    body: ReplayPreviewIn,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Recompute remediation gates server-side without mutating host state."""

    assert_can_preview(principal)
    summary: ReplaySummary = summarize_inline(body.events)
    return {"summary": summary.__dict__, "replay_mode": "read_only"}


def stable_id_from_host(os_version: str = "") -> str:
    """Hash ``platform.node()`` with release metadata to synthesize repeatable ``endpoint_id`` values.

    Args:
        os_version: Optional caller-provided OS string; defaults to ``platform.release()``.

    Returns:
        Stable hash string from :func:`platform_core.privacy.stable_endpoint_hash`.

    Side effects:
        Reads local hostname via ``platform.node`` inside this process only.

    Engineering Notes:
        Purely illustrative for demos—not a cryptographic device identifier.
    """
    import platform as plat

    hint = plat.node()
    return stable_endpoint_hash(hint, os_version or plat.release(), None)
