from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class EvidenceKind(str, Enum):
    FACT = "fact"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str = Field(min_length=1)
    kind: EvidenceKind
    source: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Criterion(BaseModel):
    name: str = Field(min_length=1)
    weight: float = Field(gt=0.0)


class Option(BaseModel):
    name: str = Field(min_length=1)
    scores: dict[str, float]
    risk: float = Field(default=0.5, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)


class DecisionRequest(BaseModel):
    question: str = Field(min_length=3)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    criteria: list[Criterion] = Field(min_length=1)
    options: list[Option] = Field(min_length=2)
    risk_penalty: float = Field(default=0.25, ge=0.0, le=1.0)
    uncertainty_penalty: float = Field(default=0.20, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_scores(self) -> "DecisionRequest":
        criterion_names = {c.name for c in self.criteria}
        if len(criterion_names) != len(self.criteria):
            raise ValueError("criterion names must be unique")
        for option in self.options:
            missing = criterion_names - option.scores.keys()
            extra = option.scores.keys() - criterion_names
            if missing or extra:
                raise ValueError(
                    f"option '{option.name}' scores must match criteria; "
                    f"missing={sorted(missing)}, extra={sorted(extra)}"
                )
            for value in option.scores.values():
                if not 0.0 <= value <= 1.0:
                    raise ValueError("all option scores must be between 0 and 1")
        return self


class OptionAssessment(BaseModel):
    option: str
    utility_score: float
    adjusted_score: float
    risk: float
    uncertainty: float


class Recommendation(BaseModel):
    decision_id: str
    question: str
    recommended_option: str
    confidence: float
    evidence_coverage: float
    assessments: list[OptionAssessment]
    assumptions: list[str]
    unknowns: list[str]
    requires_human_approval: Literal[True] = True
    status: Literal["pending_human_review"] = "pending_human_review"


class HumanDecision(BaseModel):
    approver: str = Field(min_length=1)
    action: Literal["approve", "reject"]
    rationale: str = Field(min_length=3)


class HumanDecisionResult(BaseModel):
    decision_id: str
    action: Literal["approve", "reject"]
    approver: str
    rationale: str
    status: Literal["approved", "rejected"]
