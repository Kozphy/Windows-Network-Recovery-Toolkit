"""Tests for passing AI eval cases."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.ai_evals import (
    EvalCase,
    EvalPolicyGate,
    FailureLabel,
    evaluate_case,
    load_eval_cases,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "ai_evals" / "support_bot_cases.json"


def test_ae001_passes_with_correct_and_allow() -> None:
    cases = load_eval_cases(FIXTURE)
    case = next(c for c in cases if c.case_id == "AE-001")
    result = evaluate_case(case)
    assert result.status == "pass"
    assert FailureLabel.CORRECT in result.failure_labels
    assert result.policy_decision.gate == EvalPolicyGate.ALLOW
    assert result.limitations
    assert "not proof" in result.limitations[0].lower() or "triage" in result.limitations[0].lower()


def test_synthetic_correct_case() -> None:
    case = EvalCase.model_validate(
        {
            "case_id": "SYN-PASS",
            "prompt": "test",
            "expected_answer": "hello world",
            "model_output": {"text": "hello world"},
        }
    )
    result = evaluate_case(case)
    assert result.status == "pass"
    assert result.policy_decision.gate == EvalPolicyGate.ALLOW
