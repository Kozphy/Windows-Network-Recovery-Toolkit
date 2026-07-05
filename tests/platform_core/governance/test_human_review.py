"""Tests for human review workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.governance.human_review import (
    HumanReviewDecision,
    HumanReviewStatus,
    ReviewAction,
    classification_needs_review,
    enqueue_from_incident,
    items_needing_review,
    record_decision,
)


def test_classification_needs_review() -> None:
    assert classification_needs_review("REVERTER_SUSPECTED")
    assert not classification_needs_review("DEAD_PROXY_CONFIG")


def test_enqueue_from_incident() -> None:
    item = enqueue_from_incident(
        incident_id="INC-1",
        classification="UNKNOWN_LOCAL_PROXY",
        evidence_id="EV-1",
        policy_decision_id="POL-1",
    )
    assert item is not None
    assert item.status == HumanReviewStatus.PENDING_REVIEW


def test_items_needing_review_from_audit_rows() -> None:
    rows = [
        {
            "incident_id": "INC-2",
            "classification": {"primary_classification": "POSSIBLE_MITM_RISK"},
        }
    ]
    queue = items_needing_review(rows)
    assert len(queue) == 1
    assert queue[0]["classification"] == "POSSIBLE_MITM_RISK"


def test_record_decision_writes_audit(tmp_path: Path) -> None:
    decision = HumanReviewDecision(
        review_id="HR-TEST",
        action=ReviewAction.ACCEPT_CLASSIFICATION,
        reason="Reviewer accepted triage label after evidence review.",
        actor="reviewer@example.com",
        evidence_id="EV-1",
        policy_decision_id="POL-1",
    )
    result = record_decision(decision, audit_dir=tmp_path)
    review_path = Path(result["review_path"])
    assert review_path.is_file()
    row = json.loads(review_path.read_text(encoding="utf-8").strip().splitlines()[0])
    assert row["action"] == ReviewAction.ACCEPT_CLASSIFICATION.value


def test_record_decision_rejects_ai_approve() -> None:
    decision = HumanReviewDecision(
        review_id="HR-AI",
        action=ReviewAction.APPROVE_REMEDIATION_PREVIEW,
        reason="AI tried to approve.",
        actor="ai_assistant",
        evidence_id="EV-1",
        policy_decision_id="POL-1",
    )
    with pytest.raises(ValueError, match="AI actors"):
        record_decision(decision, audit_dir=Path("."))


def test_record_decision_requires_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        HumanReviewDecision(
            review_id="HR-X",
            action=ReviewAction.REJECT_REMEDIATION,
            reason="   ",
            actor="reviewer@example.com",
            evidence_id="EV-1",
            policy_decision_id="POL-1",
        )
