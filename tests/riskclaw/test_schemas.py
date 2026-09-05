"""RiskClaw contract validation tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from riskclaw.schemas import (
    AgentDefinition,
    ApprovalRecord,
    ApprovalStatus,
    InvestigationSession,
    RiskClawAuditEvent,
)


def test_agent_definition_rejects_duplicate_skills() -> None:
    with pytest.raises(ValidationError):
        AgentDefinition(
            agent_id="endpoint-analyst",
            display_name="Endpoint Analyst",
            description="Explains deterministic endpoint evidence.",
            allowed_skills=["proxy-risk-investigation", "proxy-risk-investigation"],
        )


def test_investigation_session_is_incident_scoped() -> None:
    session = InvestigationSession(
        incident_id="INC-2026-0059",
        endpoint_id="TW-ENDPOINT-023",
        agent_id="endpoint-analyst",
        limitations=["No process-writer evidence was collected."],
    )
    assert session.incident_id == "INC-2026-0059"
    assert session.status.value == "open"
    assert session.created_at.tzinfo is not None


def test_pending_approval_rejects_decision_metadata() -> None:
    with pytest.raises(ValidationError):
        ApprovalRecord(
            session_id=uuid4(),
            tool_name="proxy.disable",
            requested_by="endpoint-analyst",
            status=ApprovalStatus.PENDING,
            reason="Preview requires operator review.",
            decided_by="operator@example",
            decided_at=datetime.now(UTC),
        )


def test_decided_approval_requires_attribution() -> None:
    with pytest.raises(ValidationError):
        ApprovalRecord(
            session_id=uuid4(),
            tool_name="proxy.disable",
            requested_by="endpoint-analyst",
            status=ApprovalStatus.APPROVED,
            reason="Evidence and rollback plan reviewed.",
        )


def test_audit_event_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RiskClawAuditEvent(
            session_id=uuid4(),
            event_type="policy.evaluated",
            actor="riskclaw-runtime",
            unsupported_claim=True,
        )
