"""Platform API routes for stakeholder / timing / decision-context (preview-first)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.platform_core.decision_context import (
    build_decision_envelope,
    explain_decision_envelope,
    load_decision_envelope,
    load_latest_decision_envelope,
    save_decision_envelope,
)
from src.platform_core.stakeholder import resolve_stakeholders
from src.platform_core.timing import evaluate_timing

router = APIRouter(prefix="/platform", tags=["decision-context"])


class StakeholderResolveIn(BaseModel):
    case_id: str = Field(min_length=1)
    classification: str = ""
    policy_outcome: str = "PREVIEW_ONLY"
    policy_requires_approval: bool = True
    proof_status: str = ""
    control_ids: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)


class TimingEvaluateIn(BaseModel):
    case_id: str = Field(min_length=1)
    detected_at_utc: str
    timezone: str | None = None
    classification: str = ""
    policy_outcome: str = "PREVIEW_ONLY"
    urgency: str | None = None
    maintenance_window_required: bool = False
    change_freeze_active: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class DecisionContextEvaluateIn(BaseModel):
    case_id: str = Field(min_length=1)
    decision_id: str = ""
    classification: str = ""
    policy_decision: str = "PREVIEW_ONLY"
    policy_allowed: bool = False
    policy_requires_approval: bool = True
    proof_status: str = ""
    proof_result: dict[str, Any] = Field(default_factory=dict)
    detected_at_utc: str | None = None
    timezone: str | None = None
    stakeholder_config: dict[str, Any] = Field(default_factory=dict)
    timing_config: dict[str, Any] = Field(default_factory=dict)
    remediation_preview: dict[str, Any] = Field(default_factory=dict)
    persist: bool = True
    write_audit: bool = True


@router.post("/stakeholders/resolve")
def post_stakeholders_resolve(body: StakeholderResolveIn) -> dict[str, Any]:
    ctx = resolve_stakeholders(
        case_id=body.case_id,
        classification=body.classification,
        evidence_summary=body.evidence_summary,
        proof_status=body.proof_status,
        policy_outcome=body.policy_outcome,
        policy_requires_approval=body.policy_requires_approval,
        control_ids=body.control_ids,
        config=body.config,
    )
    return ctx.to_dict()


@router.post("/timing/evaluate")
def post_timing_evaluate(body: TimingEvaluateIn) -> dict[str, Any]:
    tm = evaluate_timing(
        case_id=body.case_id,
        detected_at_utc=body.detected_at_utc,
        timezone_name=body.timezone,
        classification=body.classification,
        policy_outcome=body.policy_outcome,
        urgency=body.urgency,
        maintenance_window_required=body.maintenance_window_required,
        change_freeze_active=body.change_freeze_active,
        config=body.config,
    )
    return tm.to_dict()


@router.post("/decision-context/evaluate")
def post_decision_context_evaluate(body: DecisionContextEvaluateIn) -> dict[str, Any]:
    envelope = build_decision_envelope(
        case_id=body.case_id,
        decision_id=body.decision_id,
        classification=body.classification,
        policy_decision=body.policy_decision,
        policy_allowed=body.policy_allowed,
        policy_requires_approval=body.policy_requires_approval,
        proof_status=body.proof_status,
        proof_result=body.proof_result,
        detected_at_utc=body.detected_at_utc,
        timezone_name=body.timezone,
        stakeholder_config=body.stakeholder_config,
        timing_config=body.timing_config,
        remediation_preview=body.remediation_preview or {
            "dry_run": True,
            "preview_only": True,
            "message": "API evaluate is preview-only; does not execute remediation.",
        },
        write_audit=body.write_audit,
    )
    if body.persist:
        save_decision_envelope(envelope)
    out = envelope.to_dict()
    out["explanation"] = explain_decision_envelope(envelope)
    return out


@router.get("/decision-context/latest")
def get_decision_context_latest(case_id: str | None = None) -> dict[str, Any]:
    if case_id:
        env = load_decision_envelope(case_id)
    else:
        env = load_latest_decision_envelope()
    if env is None:
        raise HTTPException(status_code=404, detail="No decision context found")
    return env.to_dict()
