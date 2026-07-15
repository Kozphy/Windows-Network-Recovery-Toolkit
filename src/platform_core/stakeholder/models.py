"""Immutable stakeholder models — roles and configured identities only.

Stakeholder assignment is not approval. Never invent named persons.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_STAKEHOLDER = "stakeholder_context.v1"


class StakeholderResolutionSource(StrEnum):
    EXPLICIT_CONFIGURATION = "explicit_configuration"
    ASSET_METADATA = "asset_metadata"
    CONTROL_MAPPING = "control_mapping"
    CLASSIFICATION_MAPPING = "classification_mapping"
    DEFAULT_ROLE_MAPPING = "default_role_mapping"
    UNRESOLVED = "unresolved"


class StakeholderReasonCode(StrEnum):
    STAKEHOLDER_RESOLVED = "STAKEHOLDER_RESOLVED"
    OWNER_UNRESOLVED = "OWNER_UNRESOLVED"
    APPROVER_REQUIRED = "APPROVER_REQUIRED"
    SECURITY_ESCALATION_REQUIRED = "SECURITY_ESCALATION_REQUIRED"
    SEGREGATION_OF_DUTIES_REQUIRED = "SEGREGATION_OF_DUTIES_REQUIRED"
    EXECUTION_AUTHORITY_MISSING = "EXECUTION_AUTHORITY_MISSING"
    INFORMED_ROLE_MAPPED = "INFORMED_ROLE_MAPPED"
    AFFECTED_PARTY_MAPPED = "AFFECTED_PARTY_MAPPED"


class RoleRef(BaseModel):
    """A role or explicitly configured identity — never a guessed person."""

    model_config = ConfigDict(frozen=True)

    role_id: str
    display_name: str
    kind: Literal["role", "configured_identity"] = "role"
    identity: str | None = None
    source: StakeholderResolutionSource = StakeholderResolutionSource.DEFAULT_ROLE_MAPPING
    reason_code: StakeholderReasonCode = StakeholderReasonCode.STAKEHOLDER_RESOLVED
    rationale: str = ""


class EscalationHop(BaseModel):
    model_config = ConfigDict(frozen=True)

    order: int
    role: RoleRef
    trigger: str = ""


class StakeholderContext(BaseModel):
    """Organizational ownership and authority — separate from technical proof."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = SCHEMA_STAKEHOLDER
    case_id: str = ""
    classification: str = ""
    asset_owner: RoleRef | None = None
    control_owner: RoleRef | None = None
    affected_parties: tuple[RoleRef, ...] = ()
    approver_roles: tuple[RoleRef, ...] = ()
    executor_roles: tuple[RoleRef, ...] = ()
    informed_roles: tuple[RoleRef, ...] = ()
    escalation_path: tuple[EscalationHop, ...] = ()
    execution_authority: RoleRef | None = None
    segregation_of_duties_required: bool = True
    resolution_confidence: Literal["unresolved", "role_only", "configured", "partial"] = "role_only"
    unresolved_fields: tuple[str, ...] = ()
    reason_codes: tuple[StakeholderReasonCode, ...] = ()
    limitations: tuple[str, ...] = (
        "Stakeholder assignment is not approval.",
        "Resolver never invents named persons.",
        "Roles come from configuration or deterministic mappings only.",
    )
    inputs_fingerprint: str = ""
    config_refs: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
