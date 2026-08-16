from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high"]


class IncidentCreate(BaseModel):
    title: str
    description: str
    endpoint: str | None = None


class IncidentRecord(IncidentCreate):
    id: str
    created_at: datetime
    status: str = "open"

    @classmethod
    def from_create(cls, payload: IncidentCreate) -> "IncidentRecord":
        return cls(
            id=str(uuid4()),
            created_at=datetime.now(timezone.utc),
            **payload.model_dump(),
        )


class AgentRequest(BaseModel):
    message: str
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    incident_id: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class ProposedAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool: ToolCall
    risk: RiskLevel
    reason: str
    requires_approval: bool = True
    approved: bool | None = None


class AgentResponse(BaseModel):
    conversation_id: str
    answer: str
    evidence: list[str] = Field(default_factory=list)
    proposed_action: ProposedAction | None = None


class ApprovalRequest(BaseModel):
    approved: bool
