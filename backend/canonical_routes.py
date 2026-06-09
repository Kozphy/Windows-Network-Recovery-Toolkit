"""Canonical platform API routes — single entry for decision pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.platform_core import SCHEMA_VERSION
from src.platform_core.audit.reader import read_audit_for_decision
from src.platform_core.audit.schema import export_schema_json
from src.platform_core.audit.writer import _DEFAULT_PATH as AUDIT_PATH
from src.platform_core.governance.control_mapping import map_policy_outcome_to_controls
from src.platform_core.governance.policy_compiler import compile_policy_matrix
from src.platform_core.learning.feedback import record_feedback
from src.platform_core.operability.health import health_payload
from src.platform_core.operability.slo import SLOSnapshot
from src.platform_core.outcome.metrics import compute_metrics
from src.platform_core.outcome.store import record_outcome
from src.platform_core.pipeline import run_decision_pipeline
from src.platform_core.policy.approval import generate_approval_token, validate_approval_token
from src.platform_core.replay.certifier import certify_case
from windows_network_toolkit import __version__
from windows_network_toolkit.remediation import preview_proxy_disable

router = APIRouter(prefix="/v1", tags=["canonical-platform"])

_REPO = Path(__file__).resolve().parent.parent
_SESSION: dict[str, Any] = {}
_APPROVAL_TOKENS: dict[str, str] = {}


class EventIn(BaseModel):
    signals: dict[str, Any] = Field(default_factory=dict)
    fixture_path: str | None = None
    incident_id: str | None = None


class PolicyEvalIn(BaseModel):
    decision_id: str
    requested_action: str = "disable_wininet_proxy"
    dry_run: bool = True


class ApproveIn(BaseModel):
    decision_id: str
    approval_token: str


class OutcomeIn(BaseModel):
    decision_id: str
    incident_id: str
    recommended_action: str
    policy_outcome: str
    operator_action: str = ""
    actual_outcome: str = ""
    time_to_resolution_seconds: float | None = None
    was_successful: bool | None = None
    was_false_positive: bool | None = None
    was_blocked_by_policy: bool = False
    notes: str = ""


@router.get("/health")
def v1_health() -> dict[str, Any]:
    return health_payload()


@router.get("/version")
def v1_version() -> dict[str, str]:
    return {"version": __version__, "schema_version": SCHEMA_VERSION}


@router.post("/events")
def v1_events(body: EventIn) -> dict[str, Any]:
    path = None
    if body.fixture_path:
        path = Path(body.fixture_path)
        if not path.is_file():
            path = _REPO / "windows_network_toolkit" / "examples" / body.fixture_path
    result = run_decision_pipeline(signals=body.signals or None, jsonl_path=path, incident_id=body.incident_id)
    _SESSION["latest"] = result
    token = generate_approval_token()
    _APPROVAL_TOKENS[result.decision.decision_id] = token
    return {
        "incident_id": result.bundle.incident_id,
        "decision_id": result.decision.decision_id,
        "tier": result.bundle.tier,
        "decision": result.decision.model_dump(),
        "policy": result.policy.model_dump(),
        "approval_token_hint": token if result.policy.requires_approval else None,
        "dry_run": True,
    }


@router.post("/decisions")
def v1_decisions(body: EventIn) -> dict[str, Any]:
    return v1_events(body)


@router.post("/policy/evaluate")
def v1_policy_evaluate(body: PolicyEvalIn) -> dict[str, Any]:
    latest = _SESSION.get("latest")
    if not latest or latest.decision.decision_id != body.decision_id:
        raise HTTPException(status_code=404, detail="decision not found in session")
    from src.platform_core.policy.engine import evaluate_policy

    policy = evaluate_policy(
        decision=latest.decision,
        bundle=latest.bundle,
        requested_action=body.requested_action,
        dry_run=body.dry_run,
    )
    return policy.model_dump()


@router.post("/remediation/preview")
def v1_remediation_preview() -> dict[str, Any]:
    preview = preview_proxy_disable(dry_run=True)
    return {"preview": preview, "dry_run": True}


@router.post("/remediation/approve")
def v1_remediation_approve(body: ApproveIn) -> dict[str, Any]:
    expected = _APPROVAL_TOKENS.get(body.decision_id, "")
    if not validate_approval_token(body.approval_token, expected):
        return {"approved": False, "reason": "invalid approval token"}
    return {"approved": True, "decision_id": body.decision_id, "dry_run": True}


@router.post("/remediation/execute")
def v1_remediation_execute(body: ApproveIn) -> dict[str, Any]:
    resp = v1_remediation_approve(body)
    if not resp.get("approved"):
        return {**resp, "executed": False, "reason": "execution blocked without approval"}
    return {**resp, "executed": False, "dry_run": True, "message": "Live execute blocked in safe mode"}


@router.post("/replay/certify")
def v1_replay_certify(body: EventIn) -> dict[str, Any]:
    path = None
    if body.fixture_path:
        path = _REPO / "windows_network_toolkit" / "examples" / body.fixture_path
    cert = certify_case(signals=body.signals or None, jsonl_path=path)
    return {
        "certified": cert.certified,
        "certification_hash": cert.certification_hash,
        "tier": cert.tier,
        "policy_outcome": cert.policy_outcome,
        "errors": cert.errors,
    }


@router.post("/outcomes")
def v1_outcomes(body: OutcomeIn) -> dict[str, Any]:
    row = record_outcome(**body.model_dump())
    record_feedback(decision_id=body.decision_id)
    return row.model_dump()


@router.get("/metrics")
def v1_metrics() -> dict[str, Any]:
    return {"slo": SLOSnapshot().to_dict(), "outcomes": compute_metrics()}


@router.get("/audit/{decision_id}")
def v1_audit(decision_id: str) -> dict[str, Any]:
    rows = read_audit_for_decision(path=AUDIT_PATH, decision_id=decision_id)
    return {"decision_id": decision_id, "records": rows}


@router.get("/governance/controls")
def v1_governance_controls(outcome: str = "PREVIEW_ONLY") -> dict[str, Any]:
    policy_path = _REPO / "src" / "policy" / "default_policy.yaml"
    return {
        "controls": map_policy_outcome_to_controls(outcome),
        "policy_matrix": compile_policy_matrix(policy_path),
        "audit_schema": export_schema_json(),
    }
