"""Structured investigation artifacts (observation ≠ inference ≠ proof)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

ConfidenceRank = Literal["low", "medium", "high"]
AttributionStatus = Literal["unknown", "listener_correlation", "writer_proof"]
PolicyOutcome = Literal["ALLOW", "PREVIEW", "BLOCK"]
VerificationStatus = Literal["UNVERIFIED", "INCONCLUSIVE", "CONFIRMED", "REJECTED"]


def new_run_id() -> str:
    return f"inv_{uuid.uuid4().hex[:16]}"


@dataclass(frozen=True)
class Observation:
    """Raw measured fact."""

    id: str
    category: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Hypothesis:
    """Possible explanation — not proven."""

    hypothesis_id: str
    title: str
    confidence: ConfidenceRank
    evidence_for: tuple[str, ...]
    evidence_against: tuple[str, ...]
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RemediationPreview:
    """Preview-only remediation; never auto-executed from this workflow."""

    action_id: str
    title: str
    policy: PolicyOutcome
    detail: str
    command_preview: str | None = None


@dataclass
class ProxyInvestigationResult:
    """Full replayable investigation run."""

    run_id: str
    timestamp: str
    schema_version: str
    proxy_snapshot: dict[str, Any]
    listener_evidence: dict[str, Any]
    dev_process_evidence: dict[str, Any]
    validation: dict[str, Any]
    path_assessment: dict[str, Any] | None
    observations: list[Observation]
    hypotheses: list[Hypothesis]
    competing_hypotheses: list[str]
    primary_hypothesis_id: str
    confidence_boundary: str
    verification_strategy: list[str]
    attribution_status: AttributionStatus
    attribution_notes: list[str]
    risk_assessment: dict[str, Any]
    remediation_previews: list[RemediationPreview]
    limitations: list[str]
    human_report: str
    before_snapshot: dict[str, Any] | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "record_type": "proxy_investigation",
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "before_snapshot": self.before_snapshot,
            "proxy_snapshot": self.proxy_snapshot,
            "listener_evidence": self.listener_evidence,
            "dev_process_evidence": self.dev_process_evidence,
            "validation": self.validation,
            "path_assessment": self.path_assessment,
            "observations": [
                {"id": o.id, "category": o.category, "summary": o.summary, "detail": o.detail}
                for o in self.observations
            ],
            "hypotheses": [
                {
                    "hypothesis_id": h.hypothesis_id,
                    "title": h.title,
                    "confidence": h.confidence,
                    "evidence_for": list(h.evidence_for),
                    "evidence_against": list(h.evidence_against),
                    "limitations": list(h.limitations),
                }
                for h in self.hypotheses
            ],
            "competing_hypotheses": self.competing_hypotheses,
            "primary_hypothesis_id": self.primary_hypothesis_id,
            "confidence_boundary": self.confidence_boundary,
            "verification_strategy": self.verification_strategy,
            "attribution_status": self.attribution_status,
            "attribution_notes": self.attribution_notes,
            "risk_assessment": self.risk_assessment,
            "remediation_previews": [
                {
                    "action_id": r.action_id,
                    "title": r.title,
                    "policy": r.policy,
                    "detail": r.detail,
                    "command_preview": r.command_preview,
                }
                for r in self.remediation_previews
            ],
            "limitations": self.limitations,
        }
