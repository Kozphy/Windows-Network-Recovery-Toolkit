"""Outcome classification tests."""

from __future__ import annotations

from src.platform_core.outcome.classification import OutcomeClassification, classify_outcome


def test_successful() -> None:
    assert classify_outcome(was_successful=True) == OutcomeClassification.SUCCESSFUL_REMEDIATION


def test_blocked_by_policy() -> None:
    assert classify_outcome(was_successful=None, was_blocked_by_policy=True) == OutcomeClassification.NO_IMPACT


def test_regression() -> None:
    assert classify_outcome(was_successful=False, was_false_positive=True) == OutcomeClassification.REGRESSION
