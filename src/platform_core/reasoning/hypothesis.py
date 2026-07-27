"""Deterministic hypothesis and evidence-binding models for decision provenance."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EvidenceRelationship(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class HypothesisStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceBinding(BaseModel):
    """Bind one evidence item to a hypothesis with a stable reason code."""

    evidence_id: str = Field(min_length=1)
    relationship: EvidenceRelationship
    rationale_code: str = Field(min_length=1)
    weight: int = Field(default=50, ge=0, le=100)


class Hypothesis(BaseModel):
    """A falsifiable explanation evaluated against explicit evidence."""

    hypothesis_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    status: HypothesisStatus = HypothesisStatus.INSUFFICIENT_EVIDENCE
    evidence_bindings: list[EvidenceBinding] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_status_has_evidence(self) -> "Hypothesis":
        supporting = any(
            binding.relationship == EvidenceRelationship.SUPPORTS
            for binding in self.evidence_bindings
        )
        contradicting = any(
            binding.relationship == EvidenceRelationship.CONTRADICTS
            for binding in self.evidence_bindings
        )
        if self.status == HypothesisStatus.SUPPORTED and not supporting:
            raise ValueError("supported hypotheses require supporting evidence")
        if self.status == HypothesisStatus.CONTRADICTED and not contradicting:
            raise ValueError("contradicted hypotheses require contradicting evidence")
        return self

    @property
    def supporting_evidence(self) -> list[EvidenceBinding]:
        return [
            binding
            for binding in self.evidence_bindings
            if binding.relationship == EvidenceRelationship.SUPPORTS
        ]

    @property
    def contradicting_evidence(self) -> list[EvidenceBinding]:
        return [
            binding
            for binding in self.evidence_bindings
            if binding.relationship == EvidenceRelationship.CONTRADICTS
        ]
