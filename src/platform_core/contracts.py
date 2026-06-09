"""Canonical typed contracts for the decision pipeline."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.platform_core import AUDIT_SCHEMA_VERSION, SCHEMA_VERSION

EvidenceTierName = Literal[
    "OBSERVED_ONLY",
    "CORRELATED",
    "PROVEN_REGISTRY_WRITER",
    "PROVEN_NETWORK_IMPACT",
    "FINAL_CAUSATION",
]

PolicyOutcomeName = Literal[
    "ALLOW",
    "PREVIEW_ONLY",
    "REQUIRE_HUMAN_APPROVAL",
    "BLOCK",
    "ROLLBACK_REQUIRED",
]

AuditActionType = Literal[
    "event_received",
    "evidence_attached",
    "hypothesis_created",
    "decision_created",
    "policy_evaluated",
    "remediation_previewed",
    "human_approval_requested",
    "human_approval_granted",
    "action_executed",
    "validation_completed",
    "rollback_completed",
    "outcome_recorded",
    "replay_certified",
]


class NormalizedEvent(BaseModel):
    event_id: str
    schema_version: str = SCHEMA_VERSION
    timestamp_utc: str
    source: str
    category: str
    title: str
    trace_id: str = ""
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    observations: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    evidence_id: str
    event_id: str
    schema_version: str = SCHEMA_VERSION
    timestamp_utc: str
    source: str
    signal: str
    observed_value: str = ""
    tier: EvidenceTierName = "OBSERVED_ONLY"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    bundle_id: str
    incident_id: str
    schema_version: str = SCHEMA_VERSION
    created_at: str
    host_id: str = "local"
    tier: EvidenceTierName = "OBSERVED_ONLY"
    items: list[EvidenceItem] = Field(default_factory=list)
    summary: str = ""
    tags: list[str] = Field(default_factory=list)


class Hypothesis(BaseModel):
    hypothesis_id: str
    event_id: str
    schema_version: str = SCHEMA_VERSION
    title: str
    explanation: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    incident_type: str = ""


class Decision(BaseModel):
    decision_id: str
    incident_id: str
    trace_id: str = ""
    schema_version: str = SCHEMA_VERSION
    timestamp_utc: str
    incident_type: str
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    evidence_tier: EvidenceTierName = "OBSERVED_ONLY"
    evidence_refs: list[str] = Field(default_factory=list)
    reasoning: str = ""
    requires_human_review: bool = False


class PolicyEvaluation(BaseModel):
    evaluation_id: str
    decision_id: str
    schema_version: str = SCHEMA_VERSION
    timestamp_utc: str
    requested_action: str
    evidence_tier: EvidenceTierName
    outcome: PolicyOutcomeName
    allowed: bool
    requires_approval: bool
    requires_rollback_plan: bool
    blocked_reasons: list[str] = Field(default_factory=list)
    rationale: str = ""


class PolicyOutcome(BaseModel):
    outcome: PolicyOutcomeName
    dry_run: bool = True
    allowed_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class OperatorAction(BaseModel):
    action_id: str
    decision_id: str
    schema_version: str = SCHEMA_VERSION
    timestamp_utc: str
    action_type: str
    approval_token: str = ""
    dry_run: bool = True
    operator_id: str = "local"


class IncidentOutcome(BaseModel):
    outcome_id: str
    decision_id: str
    incident_id: str
    schema_version: str = SCHEMA_VERSION
    created_at: str
    recommended_action: str
    policy_outcome: str
    operator_action: str = ""
    actual_outcome: str = ""
    time_to_resolution_seconds: float | None = None
    was_successful: bool | None = None
    was_false_positive: bool | None = None
    was_blocked_by_policy: bool = False
    notes: str = ""


class AuditRecord(BaseModel):
    audit_id: str
    schema_version: str = AUDIT_SCHEMA_VERSION
    timestamp_utc: str
    action_type: AuditActionType
    trace_id: str = ""
    decision_id: str = ""
    incident_id: str = ""
    actor: str = "platform"
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_hash: str = ""
    current_hash: str = ""
    signature_status: Literal["unsigned", "hash_chained", "signed"] = "hash_chained"


class ReplayCase(BaseModel):
    case_id: str
    schema_version: str = SCHEMA_VERSION
    fixture_path: str = ""
    signals: dict[str, Any] = Field(default_factory=dict)
    expected_tier: EvidenceTierName | None = None
    expected_policy: PolicyOutcomeName | None = None
    certification_hash: str = ""


class LearningRecord(BaseModel):
    record_id: str
    decision_id: str
    schema_version: str = SCHEMA_VERSION
    created_at: str
    feedback_type: str
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)


class DestructiveAction(StrEnum):
    REGISTRY_MODIFICATION = "registry_modification"
    KILL_PROCESS = "kill_process"
    DISABLE_PROXY = "disable_proxy"
    FIREWALL_RESET = "firewall_reset"
    ADAPTER_DISABLE = "adapter_disable"
    DELETE_FILES = "delete_files"
    SYSTEM_NETWORK_CHANGE = "system_network_change"
