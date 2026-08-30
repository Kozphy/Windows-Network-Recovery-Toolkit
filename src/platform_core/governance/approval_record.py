"""Approval records bound to immutable decision material."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.platform_core.governance.risk_decision_record_v3 import RiskDecisionRecordV3


class ApprovalOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ApprovalRecord(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"apr-{uuid.uuid4().hex[:12]}")
    decision_id: str
    reviewer_id: str
    outcome: ApprovalOutcome
    scope: str = "decision"
    reason_codes: list[str] = Field(default_factory=list)
    comment: str = ""
    decision_hash: str
    created_at: str = Field(default_factory=_utc_now)

    def is_current_for(self, decision: RiskDecisionRecordV3) -> bool:
        """An approval becomes stale whenever decision material changes."""
        return self.decision_id == decision.decision_id and self.decision_hash == decision.refresh_decision_key()


def create_approval(
    decision: RiskDecisionRecordV3,
    *,
    reviewer_id: str,
    outcome: ApprovalOutcome,
    reason_codes: list[str] | None = None,
    comment: str = "",
) -> ApprovalRecord:
    return ApprovalRecord(
        decision_id=decision.decision_id,
        reviewer_id=reviewer_id,
        outcome=outcome,
        reason_codes=reason_codes or [],
        comment=comment,
        decision_hash=decision.refresh_decision_key(),
    )
