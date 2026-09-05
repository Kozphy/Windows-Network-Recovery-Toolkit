"""Strict interchange schemas for the RiskClaw runtime foundation."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_NAME_PATTERN = r"^[a-z][a-z0-9_.-]*$"


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    """Reject unknown fields so runtime contracts fail closed."""

    model_config = ConfigDict(extra="forbid")


class ToolDecision(StrEnum):
    ALLOW = "ALLOW"
    PREVIEW = "PREVIEW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BLOCK = "BLOCK"


class ToolRiskClass(StrEnum):
    READ_ONLY = "read_only"
    PREVIEW_ONLY = "preview_only"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class SkillRiskLevel(StrEnum):
    READ_ONLY = "read_only"
    PREVIEW_ONLY = "preview_only"
    CONTROLLED = "controlled"


class SessionStatus(StrEnum):
    OPEN = "open"
    COLLECTING = "collecting"
    CLASSIFIED = "classified"
    AWAITING_REVIEW = "awaiting_review"
    CLOSED = "closed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ToolDefinition(StrictModel):
    """Public metadata for one deterministic, allowlisted capability."""

    name: str = Field(pattern=_NAME_PATTERN)
    description: str = Field(min_length=1)
    risk_class: ToolRiskClass
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("tags", "limitations")
    @classmethod
    def unique_strings(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("values must be unique")
        return normalized


class SkillDefinition(StrictModel):
    """Parsed SKILL.md metadata plus its instructions."""

    name: str = Field(pattern=_NAME_PATTERN)
    description: str = Field(min_length=1)
    allowed_tools: list[str] = Field(min_length=1)
    risk_level: SkillRiskLevel = SkillRiskLevel.READ_ONLY
    requires_human_approval: bool = False
    instructions: str = Field(min_length=1)
    source_path: str

    @field_validator("allowed_tools")
    @classmethod
    def validate_allowed_tools(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if not normalized:
            raise ValueError("allowed_tools must contain at least one tool")
        if len(normalized) != len(set(normalized)):
            raise ValueError("allowed_tools must be unique")
        return normalized


class AgentDefinition(StrictModel):
    """Agent identity and the skills it may select."""

    agent_id: str = Field(pattern=_NAME_PATTERN)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    allowed_skills: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("allowed_skills")
    @classmethod
    def validate_allowed_skills(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if not normalized:
            raise ValueError("allowed_skills must contain at least one skill")
        if len(normalized) != len(set(normalized)):
            raise ValueError("allowed_skills must be unique")
        return normalized


class ToolPolicyResult(StrictModel):
    """Policy decision for one proposed tool call."""

    tool_name: str = Field(pattern=_NAME_PATTERN)
    skill_name: str = Field(pattern=_NAME_PATTERN)
    decision: ToolDecision
    reasons: list[str] = Field(min_length=1)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Policy permission is not a safety guarantee.",
            "Recommendation is not execution authority.",
        ]
    )
    canonical_outcome: str | None = None


class InvestigationSession(StrictModel):
    """Incident-scoped context; this is not a generic chat session."""

    session_id: UUID = Field(default_factory=uuid4)
    incident_id: str = Field(min_length=1)
    endpoint_id: str = Field(min_length=1)
    agent_id: str = Field(pattern=_NAME_PATTERN)
    status: SessionStatus = SessionStatus.OPEN
    evidence_refs: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    classification: str | None = None
    proof_tier: str | None = None
    limitations: list[str] = Field(default_factory=list)
    approval_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_timestamps(self) -> InvestigationSession:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        return self


class ApprovalRecord(StrictModel):
    """Human decision record for a proposed approval-required tool."""

    approval_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    tool_name: str = Field(pattern=_NAME_PATTERN)
    requested_by: str = Field(min_length=1)
    status: ApprovalStatus = ApprovalStatus.PENDING
    reason: str = Field(min_length=1)
    decided_by: str | None = None
    requested_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None

    @model_validator(mode="after")
    def validate_decision_fields(self) -> ApprovalRecord:
        decided = self.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}
        if decided and (not self.decided_by or self.decided_at is None):
            raise ValueError("decided approvals require decided_by and decided_at")
        if not decided and (self.decided_by is not None or self.decided_at is not None):
            raise ValueError("pending approvals cannot contain decision metadata")
        return self


class RiskClawAuditEvent(StrictModel):
    """Append-ready event envelope for future integration with canonical audit writers."""

    event_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    event_type: str = Field(pattern=_NAME_PATTERN)
    actor: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
