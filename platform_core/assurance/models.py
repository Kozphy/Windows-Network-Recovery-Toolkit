from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceQuality(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    description: str
    collected_at: str
    tier: str
    relevance: EvidenceQuality
    reliability: EvidenceQuality
    completeness: EvidenceQuality
    timeliness: EvidenceQuality
    independent: bool = False
    limitations: list[str] = Field(default_factory=list)


class SamplingPlan(BaseModel):
    population_id: str
    population_size: int = Field(gt=0)
    method: Literal["full_population", "random", "systematic", "judgmental"]
    sample_size: int = Field(gt=0)
    seed: int | None = None
    rationale: str
    selected_items: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_sample(self) -> "SamplingPlan":
        if self.sample_size > self.population_size:
            raise ValueError("sample_size cannot exceed population_size")
        if self.method == "random" and self.seed is None:
            raise ValueError("random sampling requires a seed for reproducibility")
        if self.selected_items and len(self.selected_items) != self.sample_size:
            raise ValueError("selected_items must match sample_size when materialized")
        return self


class ExceptionAssessment(BaseModel):
    exception_id: str
    observation: str
    criteria: str
    impact: Literal["low", "moderate", "high", "critical"]
    likelihood: Literal["rare", "unlikely", "possible", "likely", "almost_certain"]
    materiality: Literal["clearly_trivial", "non_material", "potentially_material", "material"]
    residual_risk: Literal["low", "moderate", "high", "critical"]
    rationale: str
    requires_human_review: bool = True


class ReviewDecision(BaseModel):
    reviewer: str
    decision: Literal["approve", "reject", "override", "needs_more_evidence"]
    rationale: str
    reviewed_at: str


class ControlTest(BaseModel):
    control_id: str
    risk: str
    control_objective: str
    criteria: list[str]
    procedure: list[str]
    scope: str
    evidence: list[EvidenceItem]
    sampling: SamplingPlan | None = None
    exceptions: list[ExceptionAssessment] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class AssuranceConclusion(BaseModel):
    control_id: str
    operating_effectiveness: Literal[
        "effective", "effective_with_exceptions", "ineffective", "inconclusive"
    ]
    confidence: Literal["low", "moderate", "high"]
    basis: str
    scope: str
    limitations: list[str] = Field(default_factory=list)
    exception_ids: list[str] = Field(default_factory=list)
    reviewer_required: bool = True
    review: ReviewDecision | None = None

    @model_validator(mode="after")
    def prevent_false_assurance(self) -> "AssuranceConclusion":
        if self.operating_effectiveness == "effective" and self.exception_ids:
            raise ValueError("effective conclusion cannot contain unresolved exceptions")
        if self.review is not None and self.review.decision in {"reject", "needs_more_evidence"}:
            if self.operating_effectiveness != "inconclusive":
                raise ValueError("rejected or evidence-deficient conclusions must be inconclusive")
        return self
