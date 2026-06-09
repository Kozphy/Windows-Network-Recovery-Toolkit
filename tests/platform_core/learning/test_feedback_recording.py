"""Learning feedback tests."""

from __future__ import annotations

from src.platform_core.learning.feedback import record_feedback


def test_feedback_record() -> None:
    rec = record_feedback(decision_id="d1")
    assert rec.decision_id == "d1"
    assert "sample_size" in rec.metrics_snapshot
