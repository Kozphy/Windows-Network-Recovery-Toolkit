"""RiskDecisionRecord — structured technology risk decision artifact."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.platform_core.governance.evidence_to_action import (
    attach_governance_envelope,
    resolve_execution_authority,
)
from src.platform_core.governance.proof_tier import ProofTier, resolve_proof_tier
from src.platform_core.risk.business_impact import estimate_business_impact
from src.platform_core.risk.business_impact_mapping import map_business_impact
from src.platform_core.risk.control_test import run_control_tests
from src.platform_core.risk.finding import findings_from_fixture
from src.platform_core.risk.risk_rating import rate_risk
from src.platform_core.serialization import content_hash


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    if score >= 0.4:
        return "low"
    return "very_low"


class RiskDecisionRecord(BaseModel):
    schema_version: str = "risk_decision_record.v1"
    incident_id: str
    evidence_id: str = ""
    classification: str = ""
    secondary_signals: list[str] = Field(default_factory=list)
    proof_tier: ProofTier = ProofTier.T0_OBSERVATION_ONLY
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_label: str = "medium"
    risk_rating: str = "medium"
    business_impact: dict[str, Any] = Field(default_factory=dict)
    recommended_action: str = ""
    execution_authority: str = "preview_only"
    human_review_required: bool = True
    limitations: list[str] = Field(default_factory=list)
    operator_id: str = "unassigned"
    created_at: str = Field(default_factory=_utc_now)
    audit_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:12]}")
    evidence_hash: str = ""
    governance: dict[str, Any] = Field(default_factory=dict)


def build_risk_decision_record(
    fixture: dict[str, Any],
    *,
    operator_id: str = "unassigned",
    incident_id: str | None = None,
) -> RiskDecisionRecord:
    """Build a RiskDecisionRecord from a case or evidence fixture."""
    classification_block = fixture.get("classification") or {}
    primary = str(classification_block.get("primary_classification") or "").upper()
    secondary = list(classification_block.get("secondary_signals") or [])
    confidence = float(classification_block.get("confidence") or 0.5)

    proof = resolve_proof_tier(fixture)
    tests = run_control_tests(fixture)
    findings = findings_from_fixture(fixture, tests)
    rating = rate_risk(findings, tests, fixture)
    impact_est = estimate_business_impact(classification=primary, fixture=fixture)
    impact_map = map_business_impact(primary)

    policy = fixture.get("policy_decision") or {}
    proof_block = fixture.get("proof") or {}
    recommended = (
        policy.get("action")
        or (classification_block.get("recommended_next_actions") or ["Continue read-only investigation"])[0]
    )

    execution_authority = resolve_execution_authority(
        policy_outcome=policy.get("outcome"),
        dry_run=bool(fixture.get("dry_run", True) or policy.get("dry_run", True)),
        requires_confirmation=bool(policy.get("requires_confirmation", True)),
        executed=bool(policy.get("executed", False)),
    )

    human_review = bool(policy.get("requires_confirmation", True)) or primary in {
        "UNKNOWN_LOCAL_PROXY",
        "SUSPICIOUS_PROXY",
        "POSSIBLE_MITM_RISK",
        "REVERTER_SUSPECTED",
        "DEAD_PROXY_CONFIG",
    } or proof.proof_tier in (ProofTier.T0_OBSERVATION_ONLY, ProofTier.T1_LOCAL_CONFIG_EVIDENCE)

    limitations = list(classification_block.get("limitations") or [])
    limitations.extend(proof.limitations)
    limitations.extend(impact_est.limitations)
    limitations.extend(proof_block.get("limitations") or [])
    limitations = list(dict.fromkeys(limitations))

    inc_id = incident_id or str(fixture.get("case_id") or fixture.get("incident_id") or f"INC-{uuid.uuid4().hex[:8]}")
    evidence_id = f"ev-{inc_id}"

    body = {
        "incident_id": inc_id,
        "classification": primary,
        "secondary_signals": secondary,
        "proof_tier": proof.proof_tier.value,
        "confidence_score": confidence,
    }
    record = RiskDecisionRecord(
        incident_id=inc_id,
        evidence_id=evidence_id,
        classification=primary,
        secondary_signals=secondary,
        proof_tier=proof.proof_tier,
        confidence_score=confidence,
        confidence_label=_confidence_label(confidence),
        risk_rating=rating.residual_level,
        business_impact={
            "ordinal_estimate": impact_est.model_dump(),
            "forum_mapping": impact_map.model_dump(),
        },
        recommended_action=str(recommended),
        execution_authority=execution_authority,
        human_review_required=human_review,
        limitations=limitations,
        operator_id=operator_id,
        evidence_hash=content_hash(body),
    )

    envelope = attach_governance_envelope(
        record.model_dump(),
        primary_classification=primary,
        evidence_tier=proof.proof_tier.value,
        proof_conclusion=(proof_block.get("conclusion") or {}).get("status"),
        policy_outcome=policy.get("outcome"),
        dry_run=bool(fixture.get("dry_run", True) or policy.get("dry_run", True)),
        requires_confirmation=bool(policy.get("requires_confirmation", True)),
    )
    record.governance = envelope.get("governance", {})
    return record
