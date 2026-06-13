"""Decision Intelligence Platform — federated multi-domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.platform_core import SCHEMA_VERSION
from src.platform_core.contracts import EvidenceBundle, EvidenceTierName

PolicyPosture = Literal["ALLOW", "PREVIEW", "OBSERVE", "DEFER", "BLOCK"]


class DecisionDomain(StrEnum):
    IT_OPERATIONS = "it_operations"
    SECURITY = "security"
    RISK = "risk"
    BUSINESS = "business"
    COMPLIANCE = "compliance"


class EvidenceTrace(BaseModel):
    evidence_id: str
    signal: str = ""
    tier: EvidenceTierName = "OBSERVED_ONLY"
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    role: Literal["supporting", "contradicting", "missing"] = "supporting"


class ScoreExplain(BaseModel):
    benefit: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    final_score: int = Field(ge=0, le=100)
    benefit_components: dict[str, float] = Field(default_factory=dict)
    risk_components: dict[str, float] = Field(default_factory=dict)
    confidence_components: dict[str, float] = Field(default_factory=dict)
    formulas: dict[str, str] = Field(default_factory=dict)


class DomainRecommendation(BaseModel):
    domain: DecisionDomain
    recommendation_id: str
    title: str
    recommendation: str
    policy_posture: PolicyPosture
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_display: str
    evidence_trace: list[EvidenceTrace] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    explain: ScoreExplain
    ranked_alternatives: list[str] = Field(default_factory=list)


class FederatedEvidenceInput(BaseModel):
    incident_id: str
    bundle: EvidenceBundle
    hypothesis_primary: str | None = None
    classification: str | None = None
    proof_status: str | None = None
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplainabilityGraph(BaseModel):
    nodes: list[dict[str, str]] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)


class AuditRecord(BaseModel):
    audit_id: str
    incident_id: str
    timestamp_utc: str
    content_digest: str
    domains_evaluated: list[str] = Field(default_factory=list)
    policy_postures: dict[str, str] = Field(default_factory=dict)
    replay_anchor: str = ""


class FederatedDecisionResult(BaseModel):
    incident_id: str
    schema_version: str = SCHEMA_VERSION
    recommendations: list[DomainRecommendation]
    explainability: ExplainabilityGraph
    audit: AuditRecord
    epistemic_notice: str = (
        "Domain recommendations are advisory; execution requires policy gates and human approval."
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
