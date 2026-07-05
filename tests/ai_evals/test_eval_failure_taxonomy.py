"""Tests for AI eval failure taxonomy labels."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.ai_evals import FailureLabel, evaluate_case, load_eval_cases

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "ai_evals" / "support_bot_cases.json"


def test_retrieval_miss_ae002() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-002")
    result = evaluate_case(case)
    assert FailureLabel.RETRIEVAL_MISS in result.failure_labels


def test_unsupported_claim_ae003() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-003")
    result = evaluate_case(case)
    assert FailureLabel.UNSUPPORTED_CLAIM in result.failure_labels


def test_format_violation_ae004() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-004")
    result = evaluate_case(case)
    assert FailureLabel.FORMAT_VIOLATION in result.failure_labels


def test_refusal_unexpected_ae005() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-005")
    result = evaluate_case(case)
    assert FailureLabel.REFUSAL_UNEXPECTED in result.failure_labels


def test_insufficient_evidence_ae006() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-006")
    result = evaluate_case(case)
    assert FailureLabel.INSUFFICIENT_EVIDENCE in result.failure_labels


def test_safety_review_ae007() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-007")
    result = evaluate_case(case)
    assert FailureLabel.SAFETY_REVIEW_REQUIRED in result.failure_labels


def test_latency_regression_ae008() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-008")
    result = evaluate_case(case)
    assert FailureLabel.LATENCY_OR_COST_REGRESSION in result.failure_labels
