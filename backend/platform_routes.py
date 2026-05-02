"""Local-first platform API — no auth by default (bind 127.0.0.1 in production)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
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
    DEFAULT_POLICY,
    PolicyDecision,
    build_preview,
    evaluate_action,
    is_shell_injection,
    validate_confirmation_phrase,
)
from platform_core.privacy import redact_text, stable_endpoint_hash
from platform_core.remediation import allowlisted_script
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
BACKEND_VERSION = "0.2.0-platform"


class HealthResponse(BaseModel):
    status: str = "ok"
    backend_version: str = BACKEND_VERSION
    platform_mode: str = "local_jsonl"
    safe_mode: bool = True
    data_dir: str = ""


@router.get("/health", response_model=HealthResponse)
def platform_health() -> dict[str, Any]:
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
    append_snapshot(snapshot.model_dump())
    write_audit(actor="agent", action="snapshot", target_type="endpoint", target_id=snapshot.endpoint_id)
    return {"stored": True}


@router.get("/endpoints")
def list_endpoints() -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    for row in read_recent_jsonl(_path("endpoints.jsonl"), limit=2000):
        eid = row.get("endpoint_id")
        if isinstance(eid, str):
            seen[eid] = row
    return {"endpoints": list(seen.values())}


@router.get("/endpoints/{endpoint_id}")
def get_endpoint(endpoint_id: str) -> dict[str, Any]:
    row = find_by_id(_path("endpoints.jsonl"), "endpoint_id", endpoint_id)
    if not row:
        raise HTTPException(status_code=404, detail="endpoint not found")
    return row


@router.get("/failure-events")
def list_failure_events(limit: int = 100) -> dict[str, Any]:
    rows = read_recent_jsonl(_path("failure_events.jsonl"), limit=max(1, min(limit, 500)))
    return {"items": rows}


@router.post("/failure-events/ingest")
def ingest_failure_event(body: FailureEvent) -> dict[str, Any]:
    """Append one sanitized FailureEvent (from local endpoint_agent)."""
    append_failure_event(body.model_dump())
    write_audit(actor="agent", action="failure_event_ingest", target_type="event", target_id=body.event_id)
    return {"stored": True, "event_id": body.event_id}


@router.get("/failure-events/{event_id}")
def get_failure_event(event_id: str) -> dict[str, Any]:
    row = find_by_id(_path("failure_events.jsonl"), "event_id", event_id)
    if not row:
        raise HTTPException(status_code=404, detail="event not found")
    return row


class PreviewIn(BaseModel):
    endpoint_id: str
    failure_event_id: str
    requested_action: str
    surface: Literal["api", "cli", "dashboard"] = "api"


@router.post("/remediation/preview")
def remediation_preview(body: PreviewIn) -> dict[str, Any]:
    if is_shell_injection(body.requested_action):
        raise HTTPException(status_code=400, detail="invalid action")
    ev_row = find_by_id(_path("failure_events.jsonl"), "event_id", body.failure_event_id)
    if not ev_row:
        raise HTTPException(status_code=404, detail="failure event not found")
    fe = FailureEvent.model_validate(ev_row)
    preview = build_preview(fe, body.requested_action, requested_surface=body.surface)
    append_remediation_preview(preview.model_dump())
    write_audit(
        actor="operator",
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
def remediation_execute(body: ExecuteIn) -> dict[str, Any]:
    if not SAFE_MODE and os.environ.get("ALLOW_PLATFORM_EXECUTE") != "1":
        pass  # still enforce policy
    prev_row = find_by_id(_path("remediation_previews.jsonl"), "preview_id", body.preview_id)
    if not prev_row:
        raise HTTPException(status_code=404, detail="preview not found")
    preview = RemediationPreview.model_validate(prev_row)
    action_name = preview.proposed_action
    meta = ACTION_REGISTRY.get(action_name, {})
    risk = meta.get("risk", "medium")
    pd: PolicyDecision = evaluate_action(action_name, risk, "api")
    if not pd.allowed:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=body.actor,
            result="blocked",
            stderr_redacted=pd.reason,
        )
        append_remediation_execution(ex.model_dump())
        write_audit(actor=body.actor, action="execute", decision="blocked", rationale=pd.reason)
        return ex.model_dump()

    if preview.requires_typed_confirmation:
        if not validate_confirmation_phrase(action_name, body.confirmation_phrase):
            raise HTTPException(status_code=400, detail="confirmation_phrase mismatch")

    script = meta.get("script")
    if body.dry_run or script is None:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=body.actor,
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
            confirmed_by=body.actor,
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
            confirmed_by=body.actor,
            result="success" if ok else "failure",
            stdout_redacted=out,
            stderr_redacted=err,
        )
        append_remediation_execution(ex.model_dump())
        write_audit(actor=body.actor, action="execute", target_type="preview", target_id=body.preview_id, decision="success" if ok else "failure")
        return ex.model_dump()
    except subprocess.TimeoutExpired:
        ex = RemediationExecution(
            execution_id=str(uuid.uuid4()),
            preview_id=body.preview_id,
            endpoint_id=preview.endpoint_id,
            action=action_name,
            confirmed_by=body.actor,
            result="failure",
            stderr_redacted="timeout",
        )
        append_remediation_execution(ex.model_dump())
        return ex.model_dump()


@router.get("/audit")
def platform_audit(limit: int = 50) -> dict[str, Any]:
    return {"items": read_recent_jsonl(_path("audit.jsonl"), limit=max(1, min(limit, 200)))}


@router.get("/metrics")
def platform_metrics() -> dict[str, Any]:
    return list_metrics()


def stable_id_from_host(os_version: str = "") -> str:
    """Derive demo endpoint id without storing raw hostname."""
    import platform as plat

    hint = plat.node()
    return stable_endpoint_hash(hint, os_version or plat.release(), None)
