from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RiskRating(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelVersion(BaseModel):
    provider: str
    model_name: str
    version: str
    deployment_id: str | None = None


class PromptVersion(BaseModel):
    prompt_id: str
    version: str
    template_hash: str

    @classmethod
    def from_template(cls, prompt_id: str, version: str, template: str) -> "PromptVersion":
        return cls(
            prompt_id=prompt_id,
            version=version,
            template_hash=sha256(template.encode("utf-8")).hexdigest(),
        )


class DataLineage(BaseModel):
    source_system: str
    dataset_id: str
    record_ids: list[str] = Field(default_factory=list)
    classification: str = "internal"
    collected_at: datetime = Field(default_factory=utc_now)
    content_hash: str | None = None


class ControlResult(BaseModel):
    control_id: str
    framework: str
    objective: str
    passed: bool
    evidence_refs: list[str] = Field(default_factory=list)
    details: str = ""


class ApprovalRecord(BaseModel):
    approver: str
    role: str
    approved: bool
    rationale: str
    approved_at: datetime = Field(default_factory=utc_now)


class AIDecisionRecord(BaseModel):
    decision_id: str
    use_case: str
    model: ModelVersion
    prompt: PromptVersion
    lineage: list[DataLineage]
    input_hash: str
    output_hash: str
    rationale_summary: str
    risk_rating: RiskRating
    controls: list[ControlResult]
    approval: ApprovalRecord | None = None
    action: str | None = None
    verification_status: str = "pending"
    rollback_ref: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def controls_passed(self) -> bool:
        return bool(self.controls) and all(control.passed for control in self.controls)

    @property
    def requires_human_approval(self) -> bool:
        return self.risk_rating in {RiskRating.HIGH, RiskRating.CRITICAL}

    def evidence_digest(self) -> str:
        payload = self.model_dump_json(exclude={"metadata"}, exclude_none=True)
        return sha256(payload.encode("utf-8")).hexdigest()
