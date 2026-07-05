"""SQLModel tables for technology-risk evidence pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ClassificationStatus(StrEnum):
    PENDING = "pending"
    CLASSIFIED = "classified"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class Endpoint(SQLModel, table=True):
    __tablename__ = "trisk_endpoints"

    id: int | None = Field(default=None, primary_key=True)
    endpoint_id: str = Field(index=True, unique=True, max_length=128)
    hostname: str | None = Field(default=None, max_length=256)
    tenant_id: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class EvidenceEvent(SQLModel, table=True):
    __tablename__ = "trisk_evidence_events"
    __table_args__ = (
        UniqueConstraint("endpoint_id", "source_event_id", name="uq_endpoint_source_event"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(index=True, unique=True, max_length=64)
    source_event_id: str | None = Field(default=None, max_length=128)
    content_hash: str = Field(index=True, max_length=64)
    endpoint_id: str = Field(index=True, max_length=128)
    evidence_type: str = Field(max_length=64)
    evidence_tier: str = Field(default="T1_STATE_EVIDENCE", max_length=64)
    raw_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    normalized_fields: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    classification_status: str = Field(default=ClassificationStatus.PENDING.value, max_length=32)
    job_id: str | None = Field(default=None, max_length=64)
    tenant_id: str | None = Field(default=None, max_length=64, index=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class IncidentRecord(SQLModel, table=True):
    __tablename__ = "trisk_incidents"

    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(index=True, unique=True, max_length=64)
    evidence_event_id: str = Field(foreign_key="trisk_evidence_events.event_id", index=True)
    endpoint_id: str = Field(index=True, max_length=128)
    primary_classification: str = Field(max_length=64)
    secondary_signals: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    proof_tier: str = Field(default="T1_STATE_EVIDENCE", max_length=64)
    confidence: float = Field(default=0.5)
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tenant_id: str | None = Field(default=None, max_length=64, index=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ControlTestResult(SQLModel, table=True):
    __tablename__ = "trisk_control_tests"

    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(foreign_key="trisk_incidents.incident_id", index=True)
    control_id: str = Field(max_length=32)
    test_result: str = Field(max_length=32)
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)


class PolicyDecision(SQLModel, table=True):
    __tablename__ = "trisk_policy_decisions"

    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(foreign_key="trisk_incidents.incident_id", index=True)
    action: str = Field(max_length=64)
    outcome: str = Field(max_length=64)
    dry_run: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utc_now)


class RiskDecisionRecord(SQLModel, table=True):
    __tablename__ = "trisk_risk_decisions"

    id: int | None = Field(default=None, primary_key=True)
    decision_id: str = Field(unique=True, max_length=64)
    incident_id: str = Field(foreign_key="trisk_incidents.incident_id", index=True)
    actor: str = Field(max_length=128)
    reason: str = Field(default="")
    policy_decision_id: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(default_factory=_utc_now)


class HumanReviewItem(SQLModel, table=True):
    __tablename__ = "trisk_human_reviews"

    id: int | None = Field(default=None, primary_key=True)
    review_id: str = Field(unique=True, max_length=64)
    incident_id: str = Field(foreign_key="trisk_incidents.incident_id", index=True)
    evidence_id: str = Field(max_length=64)
    classification: str = Field(max_length=64)
    policy_decision_id: str = Field(default="", max_length=64)
    status: str = Field(default="PENDING_REVIEW", max_length=32)
    actor: str | None = Field(default=None, max_length=128)
    reason: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class AuditChainEntry(SQLModel, table=True):
    __tablename__ = "trisk_audit_chain"

    id: int | None = Field(default=None, primary_key=True)
    row_index: int = Field(index=True)
    prev_hash: str = Field(max_length=128)
    row_hash: str = Field(max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)


class TriskDomainEventRow(SQLModel, table=True):
    __tablename__ = "trisk_domain_events"

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(unique=True, max_length=64)
    event_type: str = Field(max_length=64, index=True)
    aggregate_id: str = Field(max_length=128, index=True)
    aggregate_type: str = Field(max_length=32)
    sequence: int = Field(ge=1)
    actor: str = Field(default="system", max_length=128)
    correlation_id: str = Field(default="", max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)


class TenantRecord(SQLModel, table=True):
    __tablename__ = "trisk_tenants"

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(unique=True, max_length=64, index=True)
    display_name: str = Field(max_length=256)
    status: str = Field(default="active", max_length=32)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ObservationRecord(SQLModel, table=True):
    __tablename__ = "trisk_observations"

    id: int | None = Field(default=None, primary_key=True)
    observation_id: str = Field(unique=True, max_length=64, index=True)
    tenant_id: str = Field(max_length=64, index=True)
    endpoint_id: str = Field(max_length=128)
    signal_type: str = Field(max_length=64)
    raw_observation: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    correlation_id: str = Field(default="", max_length=128)
    created_at: datetime = Field(default_factory=_utc_now)


class HypothesisRecord(SQLModel, table=True):
    __tablename__ = "trisk_hypotheses"

    id: int | None = Field(default=None, primary_key=True)
    hypothesis_id: str = Field(unique=True, max_length=64, index=True)
    tenant_id: str = Field(max_length=64, index=True)
    observation_id: str | None = Field(default=None, max_length=64)
    evidence_event_id: str | None = Field(default=None, max_length=64)
    label: str = Field(max_length=128)
    confidence_score: float = Field(default=0.5)
    confidence_ordinal: str = Field(default="medium", max_length=16)
    status: str = Field(default="proposed", max_length=32)
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class PlatformDecisionRecord(SQLModel, table=True):
    __tablename__ = "trisk_platform_decisions"

    id: int | None = Field(default=None, primary_key=True)
    decision_id: str = Field(unique=True, max_length=64, index=True)
    tenant_id: str = Field(max_length=64, index=True)
    incident_id: str | None = Field(default=None, max_length=64)
    hypothesis_id: str | None = Field(default=None, max_length=64)
    evidence_event_id: str = Field(max_length=64)
    confidence_score: float = Field(default=0.5)
    confidence_label: str = Field(default="medium", max_length=16)
    policy_outcome: str = Field(default="PREVIEW_ONLY", max_length=64)
    recommended_action: str = Field(default="OBSERVE", max_length=64)
    execution_authority: str = Field(default="preview_only", max_length=64)
    human_approval_required: bool = Field(default=True)
    human_approval_status: str = Field(default="pending", max_length=32)
    actor: str = Field(default="system", max_length=128)
    rationale: str = Field(default="")
    limitations: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class PolicyPackRecord(SQLModel, table=True):
    __tablename__ = "trisk_policy_packs"

    id: int | None = Field(default=None, primary_key=True)
    pack_id: str = Field(unique=True, max_length=64, index=True)
    tenant_id: str = Field(max_length=64, index=True)
    version: str = Field(default="1.0.0", max_length=32)
    yaml_content: str
    active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utc_now)


class AuditLogRecord(SQLModel, table=True):
    __tablename__ = "trisk_audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    log_id: str = Field(unique=True, max_length=64, index=True)
    tenant_id: str = Field(max_length=64, index=True)
    correlation_id: str = Field(default="", max_length=128, index=True)
    event_type: str = Field(max_length=64)
    actor: str = Field(default="system", max_length=128)
    resource_type: str = Field(default="decision", max_length=32)
    resource_id: str = Field(default="", max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    prev_hash: str = Field(default="genesis", max_length=128)
    row_hash: str = Field(max_length=128)
    created_at: datetime = Field(default_factory=_utc_now)
