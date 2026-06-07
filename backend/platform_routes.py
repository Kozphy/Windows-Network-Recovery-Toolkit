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
    * ``POST /platform/agent/heartbeat`` (alias ``POST /platform/ingest/heartbeat``) — register endpoint identity (**operator/admin** headers).
    * ``POST /platform/snapshots`` (alias ``POST /platform/ingest/snapshot``) — ingest :class:`~platform_core.models.EndpointSnapshot`.
    * ``GET /platform/endpoints`` / ``GET /platform/endpoints/{id}`` — latest merged heartbeats.
    * ``GET/POST .../failure-events`` — list / ingest (POST alias ``POST /platform/ingest/failure-event``) — **operator/admin**.
    * ``POST /platform/remediation/preview|execute`` — policy-gated remediation pipeline.
    * ``GET /platform/audit`` — recent audit rows (**admin/security** readers).
    * ``GET /platform/metrics`` — aggregate counters (:func:`~platform_core.metrics.compute_platform_metrics` merge).
    * ``GET /platform/incidents`` — deterministic clustered failure timelines (viewer-capable RBAC tier).
    * ``GET /platform/attribution/{event_id}`` — evidence fused ``AttributionResult`` payload + optional persistence.
    * ``GET /platform/events`` — normalized envelopes (viewer+ headers).
    * ``GET /platform/policy/summary`` — registry roll-up for dashboards.
    * ``POST /platform/replay/preview`` — inline replay summaries (local-only-safe).

Audit Notes:
    Correlate ``audit.jsonl`` with ``remediation_executions.jsonl`` after contested runs. Treat
    ``SAFE_MODE``, ``ALLOW_PLATFORM_EXECUTE``, and blocked executions as authoritative signals—even
    when HTTP responses return 200 with ``result=blocked``.
"""

from __future__ import annotations

import os
import platform as plat
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

from evidence.attribution_engine import build_attribution, parse_sysmon_sequence
from evidence.procmon_importer import ProcmonRegistryWrite, iter_procmon_registry_writes_from_csv
from platform_core.agent_planner import plan_next_step
from platform_core.audit import write_audit
from platform_core.event_bus import default_normalized_events_path, read_events
from platform_core.fleet import linked_failure_block_payload
from platform_core.incidents import incident_summaries
from platform_core.metrics import compute_platform_metrics
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
from platform_core.privacy import redact_text, stable_endpoint_hash
from platform_core.product_contract import (
    AgentNextStepRequest,
    AgentNextStepResponse,
    DiagnosisRunRequest,
    LkgSnapshotRequest,
    PlatformAuditEvent,
    RollbackPreviewRequest,
    append_contract_audit,
    audit_tail,
    build_diagnosis_run,
    build_rollback_preview,
    get_diagnosis,
    latest_diagnosis,
    latest_lkg_snapshot,
    list_endpoint_summaries,
    replay_diagnosis,
    store_lkg_snapshot,
)
from platform_core.rbac import (
    DemoPrincipal,
    assert_can_execute,
    assert_can_preview,
    assert_can_read_attribution,
    assert_can_read_audit,
    assert_can_read_incidents,
    assert_can_read_metrics,
    assert_can_read_normalized_events,
    assert_can_write_platform_payload,
    parse_demo_principal,
)
from platform_core.remediation import allowlisted_script
from platform_core.remediation_registry import get_remediation_action
from platform_core.replay.runner import ReplaySummary, summarize_inline
from platform_core.storage import (
    _path,
    append_attribution_record,
    append_failure_event,
    append_remediation_execution,
    append_remediation_preview,
    append_snapshot,
    find_attribution_context,
    find_by_id,
    iter_jsonl,
    platform_data_dir,
    read_recent_jsonl,
    upsert_endpoint,
)

router = APIRouter(prefix="/platform", tags=["platform"])

SAFE_MODE = os.environ.get("PLATFORM_SAFE_MODE", "1") != "0"
BACKEND_VERSION = "0.5.0-endpoint-reliability-prototype"


def get_demo_principal(
    x_operator_id: str | None = Header(default=None),
    x_operator_role: str | None = Header(default=None),
) -> DemoPrincipal:
    """FastAPI dependency that maps optional operator headers into a demo :class:`~platform_core.rbac.DemoPrincipal`.

    Args:
        x_operator_id: Optional ``X-Operator-Id`` header (portfolio demo identifier).
        x_operator_role: Optional ``X-Operator-Role`` header controlling preview vs execute vs ingestion.
            Strings ``security`` and ``security_auditor`` converge inside :mod:`platform_core.rbac`.

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
    audit_store_status: str = "available"
    policy_mode: str = "safe_preview_default"
    local_first_mode: bool = True
    remediation_default: str = "dry_run"


@router.get("/health", response_model=HealthResponse)
def platform_health() -> dict[str, Any]:
    """Expose process version flags, JSONL mode, ``SAFE_MODE`` snapshot, and data directory."""

    return {
        "status": "ok",
        "backend_version": BACKEND_VERSION,
        "platform_mode": "local_jsonl",
        "safe_mode": SAFE_MODE,
        "data_dir": str(platform_data_dir()),
        "audit_store_status": "available",
        "policy_mode": "safe_preview_default",
        "local_first_mode": True,
        "remediation_default": "dry_run",
    }


class HeartbeatIn(BaseModel):
    endpoint_id: str
    os_family: str = ""
    os_version: str = ""
    agent_version: str = ""


@router.post("/agent/heartbeat")
def agent_heartbeat(
    body: HeartbeatIn,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Append an :class:`~platform_core.models.EndpointIdentity` heartbeat plus matching audit row."""

    assert_can_write_platform_payload(principal)
    ident = EndpointIdentity(
        endpoint_id=body.endpoint_id,
        os_family=body.os_family,
        os_version=body.os_version,
        agent_version=body.agent_version,
        last_seen_at=utc_now_iso(),
    )
    upsert_endpoint(ident.model_dump())
    from platform_core.fleet_store import append_heartbeat

    fleet_record = append_heartbeat(
        {
            "endpoint_id": body.endpoint_id,
            "hostname": body.endpoint_id[:12],
            "os_name": body.os_family or body.os_version,
            "agent_version": body.agent_version,
            "last_seen": ident.last_seen_at,
            "risk_state": "healthy",
        }
    )
    write_audit(
        actor="agent", action="heartbeat", target_type="endpoint", target_id=body.endpoint_id
    )
    return {
        "stored": True,
        "endpoint_id": body.endpoint_id,
        "fleet": fleet_record.to_summary_row(),
    }


@router.post("/ingest/heartbeat")
def ingest_heartbeat(
    body: HeartbeatIn,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Canonical portfolio path — identical semantics to ``/platform/agent/heartbeat``."""

    return agent_heartbeat(body, principal)


@router.post("/snapshots")
def post_snapshot(
    snapshot: EndpointSnapshot,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Persist a privacy-scrubbed :class:`~platform_core.models.EndpointSnapshot` row."""

    assert_can_write_platform_payload(principal)
    append_snapshot(snapshot.model_dump())
    write_audit(
        actor="agent", action="snapshot", target_type="endpoint", target_id=snapshot.endpoint_id
    )
    return {"stored": True}


@router.post("/ingest/snapshot")
def ingest_snapshot(
    snapshot: EndpointSnapshot,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Alias for ``POST /platform/snapshots`` — ingestion-only naming."""

    return post_snapshot(snapshot, principal)


@router.get("/endpoints")
def list_endpoints() -> dict[str, Any]:
    """Return frontend-contract endpoint summaries keyed by ``endpoint_id``."""

    return {"endpoints": [item.model_dump(mode="json") for item in list_endpoint_summaries()]}


@router.get("/endpoints/{endpoint_id}")
def get_endpoint(endpoint_id: str) -> dict[str, Any]:
    """Fetch latest frontend-contract endpoint summary for ``endpoint_id``."""

    summaries = {item.endpoint_id: item for item in list_endpoint_summaries()}
    summary = summaries.get(endpoint_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="endpoint not found")
    return summary.model_dump(mode="json")


@router.get("/diagnosis/latest")
def platform_diagnosis_latest() -> dict[str, Any]:
    """Return newest stored diagnosis, or a no-data envelope when none exists."""

    result = latest_diagnosis()
    if result is None:
        return {
            "diagnosis": None,
            "message": "no stored diagnosis; POST /platform/diagnosis/run to collect read-only observations",
        }
    return {"diagnosis": result.model_dump(mode="json")}


@router.get("/diagnosis/{run_id}")
def platform_diagnosis_get(run_id: str) -> dict[str, Any]:
    """Return one stored diagnosis by run id."""

    result = get_diagnosis(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="diagnosis not found")
    return result.model_dump(mode="json")


@router.post("/diagnosis/run")
def platform_diagnosis_run(
    body: DiagnosisRunRequest | None = None,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Run read-only probes, persist diagnosis, and append a replayable audit event."""

    request = body or DiagnosisRunRequest()
    result = build_diagnosis_run(
        endpoint_id=request.endpoint_id,
        include_live_probes=request.include_live_probes,
        actor=principal.operator_id,
    )
    return result.model_dump(mode="json")


@router.get("/failure-events")
def list_failure_events(limit: int = 100) -> dict[str, Any]:
    """Return capped recent failure-event rows newest-first semantics via :func:`read_recent_jsonl`."""

    rows = read_recent_jsonl(_path("failure_events.jsonl"), limit=max(1, min(limit, 500)))
    return {"items": rows}


@router.post("/failure-events/ingest")
def ingest_failure_event(
    body: FailureEvent,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Append one sanitized :class:`~platform_core.models.FailureEvent` originating from collectors.

    Side effects:
        Writes ``failure_events.jsonl`` plus an audit row referencing ``event_id``.

    Note:
        Invalid payloads return FastAPI 422 responses rather than bespoke ``HTTPException`` rows.
    """
    assert_can_write_platform_payload(principal)
    append_failure_event(body.model_dump())
    write_audit(
        actor="agent", action="failure_event_ingest", target_type="event", target_id=body.event_id
    )
    return {"stored": True, "event_id": body.event_id}


@router.post("/ingest/failure-event")
def ingest_failure_event_alias(
    body: FailureEvent,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Alias for ``POST /platform/failure-events/ingest``."""

    return ingest_failure_event(body, principal)


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


def _decision_for_preview(allowed: bool) -> Literal["preview_only", "blocked"]:
    """Map legacy policy booleans onto the frontend remediation contract."""

    return "preview_only" if allowed else "blocked"


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
    contract_decision = _decision_for_preview(preview.allowed_by_policy)
    audit_event_id = append_contract_audit(
        PlatformAuditEvent(
            endpoint_id=preview.endpoint_id,
            event_kind="remediation_preview",
            summary=f"Preview requested for {preview.proposed_action}",
            hypothesis=[preview.rationale] if preview.rationale else [],
            confidence=fe.confidence,
            evidence_level="inference",
            policy_decision=contract_decision,
            actor=principal.operator_id,
            replay_ref=preview.preview_id,
        )
    )
    payload = preview.model_dump()
    payload.update(
        {
            "action_id": preview.preview_id,
            "allowed": preview.allowed_by_policy,
            "decision": contract_decision,
            "reason": preview.policy_reason,
            "required_confirmation": preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
            "audit_event_id": audit_event_id,
            "dry_run": True,
        }
    )
    return payload


class ExecuteIn(BaseModel):
    preview_id: str
    confirmation_phrase: str = ""
    dry_run: bool = True
    actor: str = "operator_local"


def _execution_contract_payload(
    execution: RemediationExecution,
    *,
    decision: Literal["allow", "preview_only", "blocked"],
    reason: str,
    allowed: bool,
    audit_event_id: str,
    required_confirmation: str = "",
) -> dict[str, Any]:
    """Layer the productized remediation contract onto legacy execution records."""

    payload = execution.model_dump()
    payload.update(
        {
            "action_id": execution.execution_id,
            "allowed": allowed,
            "decision": decision,
            "reason": reason,
            "required_confirmation": required_confirmation,
            "audit_event_id": audit_event_id,
            "dry_run": execution.result == "dry_run",
        }
    )
    return payload


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
        append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_blocked",
                summary="unknown_action",
                confidence=1.0,
                evidence_level="observation",
                policy_decision="blocked",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_blocked",
                summary=pd.reason,
                confidence=0.9,
                evidence_level="inference",
                policy_decision="blocked",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="blocked",
            reason=pd.reason,
            allowed=False,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )

    if preview.requires_typed_confirmation:
        if not validate_confirmation_phrase(action_name, body.confirmation_phrase):
            append_contract_audit(
                PlatformAuditEvent(
                    endpoint_id=preview.endpoint_id,
                    event_kind="remediation_blocked",
                    summary="confirmation_phrase mismatch",
                    confidence=1.0,
                    evidence_level="observation",
                    policy_decision="blocked",
                    actor=principal.operator_id,
                    replay_ref=body.preview_id,
                )
            )
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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_blocked",
                summary="manual_only_or_api_execute_disabled",
                confidence=0.95,
                evidence_level="inference",
                policy_decision="blocked",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="blocked",
            reason="manual_only_or_api_execute_disabled",
            allowed=False,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )

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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_execute_attempt",
                summary="[dry-run] no subprocess",
                confidence=0.9,
                evidence_level="observation",
                policy_decision="preview_only",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="preview_only",
            reason="[dry-run] no subprocess",
            allowed=True,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )

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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_execute_attempt",
                summary="execution_only_supported_on_windows",
                confidence=1.0,
                evidence_level="observation",
                policy_decision="blocked",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="blocked",
            reason="execution_only_supported_on_windows",
            allowed=False,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )

    path = allowlisted_script(str(script), _REPO_ROOT)
    if path is None:
        append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_blocked",
                summary="script not allowlisted",
                confidence=1.0,
                evidence_level="observation",
                policy_decision="blocked",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        raise HTTPException(status_code=400, detail="script not allowlisted")

    write_audit(
        actor=principal.operator_id,
        action="execute_live_pending",
        target_type="preview",
        target_id=body.preview_id,
        decision="pending",
        rationale=f"spawn_allowlisted:{path.name}",
    )

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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_execute_attempt",
                summary="allowlisted subprocess completed"
                if ok
                else "allowlisted subprocess failed",
                confidence=1.0,
                evidence_level="observation",
                policy_decision="allow" if ok else "preview_only",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="allow" if ok else "preview_only",
            reason="success" if ok else "failure",
            allowed=ok,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )
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
        audit_event_id = append_contract_audit(
            PlatformAuditEvent(
                endpoint_id=preview.endpoint_id,
                event_kind="remediation_execute_attempt",
                summary="timeout",
                confidence=1.0,
                evidence_level="observation",
                policy_decision="preview_only",
                actor=principal.operator_id,
                replay_ref=body.preview_id,
            )
        )
        return _execution_contract_payload(
            ex,
            decision="preview_only",
            reason="timeout",
            allowed=False,
            audit_event_id=audit_event_id,
            required_confirmation=preview.confirmation_phrase
            if preview.requires_typed_confirmation
            else "",
        )


@router.get("/audit")
def platform_audit(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """RBAC-filtered slice of newest ``audit.jsonl`` rows."""

    assert_can_read_audit(principal)
    return {"items": read_recent_jsonl(_path("audit.jsonl"), limit=max(1, min(limit, 200)))}


@router.get("/audit/tail")
def platform_audit_tail(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Return the append-only audit tail using the product contract shape when present."""

    assert_can_read_audit(principal)
    return {"items": audit_tail(limit)}


@router.get("/lkg/{endpoint_id}")
def get_lkg_snapshot(endpoint_id: str) -> dict[str, Any]:
    """Return latest last-known-good snapshot metadata for an endpoint."""

    row = latest_lkg_snapshot(endpoint_id)
    return {"endpoint_id": endpoint_id, "available": row is not None, "snapshot": row}


@router.post("/lkg/snapshot")
def post_lkg_snapshot(
    body: LkgSnapshotRequest,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Store a local, operator-provided LKG snapshot; no system state is changed."""

    assert_can_preview(principal)
    return store_lkg_snapshot(body)


@router.post("/rollback/preview")
def rollback_preview(
    body: RollbackPreviewRequest,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Build a targeted rollback preview without applying registry or network changes."""

    assert_can_preview(principal)
    return build_rollback_preview(body)


@router.get("/metrics")
def platform_metrics(
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Expose aggregate counters from JSONL including extended portfolio KPI names."""

    assert_can_read_metrics(principal)
    return compute_platform_metrics()


@router.get("/events")
def list_normalized_events(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Read privacy-scrubbed normalized events emitted to ``normalized_events.jsonl``."""

    assert_can_read_normalized_events(principal)
    path = default_normalized_events_path()
    items, errs = read_events(path, limit=max(1, min(limit, 200)))
    return {"items": items, "parse_errors": errs, "path": str(path)}


@router.get("/incidents")
def list_incidents(
    limit: int = 50,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Return lifecycle incidents and deterministic failure-event clusters."""

    assert_can_read_incidents(principal)
    from platform_core.incident_store import list_incident_rows

    lifecycle = list_incident_rows()
    events_path = _path("failure_events.jsonl")
    rows = list(iter_jsonl(events_path))
    clusters = incident_summaries(rows)
    capped_lifecycle = lifecycle[-max(1, min(limit, 100)) :] if lifecycle else []
    capped_clusters = clusters[-max(1, min(limit, 100)) :] if clusters else []
    return {
        "items": capped_lifecycle,
        "clusters": capped_clusters,
        "total_lifecycle": len(lifecycle),
        "total_candidates": len(clusters),
    }


@router.get("/incidents/{incident_id}")
def get_incident_route(
    incident_id: str,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    assert_can_read_incidents(principal)
    from platform_core.incident_store import get_incident

    row = get_incident(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="incident not found")
    return row


class IncidentTransitionIn(BaseModel):
    note: str = ""


@router.post("/incidents/{incident_id}/ack")
def ack_incident(
    incident_id: str,
    body: IncidentTransitionIn | None = None,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    assert_can_write_platform_payload(principal)
    from platform_core.incident_engine import apply_transition

    record = apply_transition(incident_id, new_state="ACKNOWLEDGED", actor=principal.operator_id)
    return record.model_dump(mode="json")


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    body: IncidentTransitionIn | None = None,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    assert_can_write_platform_payload(principal)
    from platform_core.incident_engine import apply_transition

    record = apply_transition(incident_id, new_state="RESOLVED", actor=principal.operator_id)
    return record.model_dump(mode="json")


@router.post("/incidents/{incident_id}/false-positive")
def false_positive_incident(
    incident_id: str,
    body: IncidentTransitionIn | None = None,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    assert_can_write_platform_payload(principal)
    from platform_core.incident_engine import apply_transition

    record = apply_transition(incident_id, new_state="FALSE_POSITIVE", actor=principal.operator_id)
    return record.model_dump(mode="json")


@router.get("/attribution/{event_id}")
def platform_attribution(
    event_id: str,
    principal: DemoPrincipal = Depends(get_demo_principal),
    persist: bool = True,
) -> dict[str, Any]:
    """Evidence-backed attribution for a stored failure-event *id* (+ optional attribution context).

    Persisted bundles in ``platform_data/attribution_context.jsonl`` let offline demos/tests attach
    Sysmon/Procmon fixtures without querying live ETW/EventLog.
    """

    assert_can_read_attribution(principal)
    row = find_by_id(_path("failure_events.jsonl"), "event_id", event_id)
    if not row:
        raise HTTPException(status_code=404, detail="failure event not found")
    summary = str(row.get("summary") or "")
    ctx = find_attribution_context(event_id) or {}
    reg = ctx.get("registry_context") if isinstance(ctx.get("registry_context"), dict) else {}
    listeners = ctx.get("listeners") if isinstance(ctx.get("listeners"), list) else []
    inventory = (
        ctx.get("process_inventory") if isinstance(ctx.get("process_inventory"), dict) else {}
    )
    parent = ctx.get("parent_process") if isinstance(ctx.get("parent_process"), dict) else {}
    sysmon_dicts = ctx.get("sysmon") if isinstance(ctx.get("sysmon"), list) else []
    etw_ev = ctx.get("etw_events") if isinstance(ctx.get("etw_events"), list) else []

    proc_rows: list[Any] = []
    csv_txt = ctx.get("procmon_csv")
    if isinstance(csv_txt, str):
        proc_rows.extend(list(iter_procmon_registry_writes_from_csv(csv_txt)))
    embedded = ctx.get("procmon")
    if isinstance(embedded, list):
        for raw in embedded:
            if isinstance(raw, dict):
                proc_rows.append(
                    ProcmonRegistryWrite(
                        process_name=str(raw.get("Process Name") or raw.get("process_name") or ""),
                        operation=str(raw.get("Operation") or "RegSetValue"),
                        path=str(raw.get("Path") or ""),
                        detail=str(raw.get("Detail") or ""),
                    ),
                )

    reg_ctx: dict[str, Any] | None = None
    if reg:
        reg_ctx = dict(reg)
    elif isinstance(ctx.get("registry"), dict):
        reg_ctx = dict(ctx["registry"])  # type: ignore[arg-type]

    sysmon_ev = (
        parse_sysmon_sequence([dict(r) for r in sysmon_dicts if isinstance(r, dict)])
        if sysmon_dicts
        else []
    )

    res = build_attribution(
        event_id=event_id,
        failure_summary=summary,
        registry_context=reg_ctx,
        process_inventory=inventory if inventory else {},
        parent_process=parent if parent else None,
        listeners=listeners if listeners else [],
        sysmon_events=sysmon_ev,
        procmon_rows=proc_rows,
        etw_events=[dict(e) for e in etw_ev if isinstance(e, dict)],
    )
    payload = res.as_dict()
    if persist:
        append_attribution_record(payload)
        write_audit(
            actor=principal.operator_id,
            action="attribution_resolve",
            target_type="failure_event",
            target_id=event_id,
            decision="",
            rationale=res.attribution_level,
        )
    return payload


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


@router.get("/replay/{run_id}")
def replay_stored_diagnosis(
    run_id: str,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Replay a stored diagnosis from persisted observations only; never re-probes the host."""

    assert_can_read_normalized_events(principal)
    payload = replay_diagnosis(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="diagnosis not found")
    return payload


@router.post("/agent/next-step")
def agent_next_step(
    body: AgentNextStepRequest,
    principal: DemoPrincipal = Depends(get_demo_principal),
) -> dict[str, Any]:
    """Return a bounded agentic next step. The agent may suggest and explain, but never repair."""

    diag = get_diagnosis(body.run_id) if body.run_id else latest_diagnosis()
    goal_in = str(getattr(body, "goal", "suggest_next_probe") or "suggest_next_probe")
    goal_alias = (
        "recommend_preview_action" if goal_in == "generate_remediation_preview" else goal_in
    )
    if goal_alias not in {
        "suggest_next_probe",
        "rank_hypotheses",
        "explain_risk",
        "recommend_preview_action",
        "summarize_audit",
        "identify_missing_evidence",
    }:
        goal_alias = "suggest_next_probe"
    plan = plan_next_step(diag, goal=goal_alias)  # type: ignore[arg-type]
    response = AgentNextStepResponse(
        next_step=plan.next_step,
        reason=plan.reason,
        evidence_used=plan.evidence_used,
        confidence=plan.confidence,
        policy_boundary=plan.policy_boundary,
        blocked_actions=list(plan.blocked_actions),
    )
    append_contract_audit(
        PlatformAuditEvent(
            endpoint_id=body.endpoint_id or (diag.endpoint_id if diag else ""),
            event_kind="agent_next_step",
            observations=[
                {"evidence_used": plan.evidence_used, "blocked_actions": list(plan.blocked_actions)}
            ],
            summary=plan.reason,
            hypothesis=diag.inferred_hypotheses if diag else [],
            confidence=plan.confidence,
            evidence_level=diag.evidence_level if diag else "observation",
            policy_decision="preview_only",
            actor=principal.operator_id,
            replay_ref=diag.run_id if diag else "",
            run_id=diag.run_id if diag else "",
        )
    )
    return response.model_dump(mode="json")


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
        Uses the module-level ``plat`` import (stdlib ``platform``) per the workspace
        no-inline-imports rule.
    """
    hint = plat.node()
    return stable_endpoint_hash(hint, os_version or plat.release(), None)
