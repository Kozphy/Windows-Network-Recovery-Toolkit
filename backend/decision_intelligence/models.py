"""Typed OpenAPI models for the Decision Intelligence API.

Request/response shapes for ``/decision-intelligence/*`` routes. Timestamps are
UTC ISO-8601 strings unless noted on individual fields.

Validation boundaries:
    - Pagination: ``page`` >= 1, ``page_size`` 1–100.
    - Confidence filters: 0.0–1.0 when present.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    has_more: bool


class EventFilters(BaseModel):
    domain: str | None = None
    category: str | None = None
    event_id: str | None = None
    since: str | None = None
    until: str | None = None


class EvidenceFilters(BaseModel):
    event_id: str | None = None
    decision_id: str | None = None
    kind: str | None = None


class DecisionFilters(BaseModel):
    domain: str | None = None
    decision_id: str | None = None
    policy_status: str | None = None
    min_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class OutcomeFilters(BaseModel):
    decision_id: str | None = None
    success: bool | None = None


class EventCreate(BaseModel):
    event_id: str
    domain: str = "generic"
    title: str
    category: str = ""
    timestamp_utc: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EventRecord(EventCreate):
    created_at: str | None = None


class EvidenceCreate(BaseModel):
    evidence_id: str
    event_id: str = ""
    decision_id: str = ""
    label: str
    kind: str = "observation"
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    supports_decision: bool | None = None
    detail: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EvidenceRecord(EvidenceCreate):
    created_at: str | None = None


class DecisionCreate(BaseModel):
    decision_id: str
    domain: str
    title: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=100.0)
    policy_status: str = "PREVIEW"
    payload: dict[str, Any] = Field(default_factory=dict)
    content_digest: str = ""
    timestamp_utc: str


class DecisionRecord(DecisionCreate):
    created_at: str | None = None


class OutcomeCreate(BaseModel):
    outcome_id: str
    decision_id: str
    outcome: str
    success: bool
    predicted_success: bool = True
    cost: float = Field(ge=0.0, default=0.0)
    time_to_resolution: float = Field(ge=0.0, default=0.0)
    notes: str = ""
    recorded_at_utc: str


class OutcomeRecord(OutcomeCreate):
    created_at: str | None = None


class ReplayRequest(BaseModel):
    fixture_path: str | None = None
    include_engine_digest: bool = True


class ReplayResponse(BaseModel):
    outcome_count: int
    content_digest: str
    metrics: dict[str, Any]
    report_excerpt: str = ""


class MetricsResponse(BaseModel):
    store: dict[str, int]
    learning: dict[str, Any]
    storage_backend: str
