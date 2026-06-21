"""Tests for AI eval policy gate mapping."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.ai_evals import (
    EvalCase,
    EvalPolicyGate,
    FailureLabel,
    evaluate_case,
    evaluate_eval_policy,
    load_eval_cases,
    normalize_eval_policy,
)
from src.platform_core.ai_evals.schemas import FailureSignal

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "ai_evals" / "support_bot_cases.json"


def test_normalize_eval_policy_aliases() -> None:
    assert normalize_eval_policy("PREVIEW_ONLY") == EvalPolicyGate.PREVIEW
    assert normalize_eval_policy("REQUIRE_HUMAN_APPROVAL") == EvalPolicyGate.REQUIRE_HUMAN_REVIEW


def test_correct_maps_to_allow() -> None:
    case = EvalCase.model_validate({"case_id": "P1", "prompt": "p", "model_output": {"text": "x"}})
    policy = evaluate_eval_policy(case, failure_labels=[FailureLabel.CORRECT], failure_signals=[])
    assert policy.gate == EvalPolicyGate.ALLOW


def test_insufficient_evidence_gate() -> None:
    case = EvalCase.model_validate({"case_id": "P2", "prompt": "p", "model_output": {"text": "x"}})
    policy = evaluate_eval_policy(
        case,
        failure_labels=[FailureLabel.INSUFFICIENT_EVIDENCE],
        failure_signals=[
            FailureSignal(label=FailureLabel.INSUFFICIENT_EVIDENCE, detail="missing citation")
        ],
    )
    assert policy.gate == EvalPolicyGate.INSUFFICIENT_EVIDENCE
    assert policy.requires_human_review is True


def test_safety_maps_to_block() -> None:
    case = next(c for c in load_eval_cases(FIXTURE) if c.case_id == "AE-007")
    result = evaluate_case(case)
    assert result.policy_decision.gate == EvalPolicyGate.BLOCK


def test_fixture_expected_policies() -> None:
    cases = {c.case_id: c for c in load_eval_cases(FIXTURE)}
    for case_id in ("AE-001", "AE-002", "AE-003", "AE-004", "AE-005", "AE-006", "AE-007", "AE-008"):
        case = cases[case_id]
        result = evaluate_case(case)
        expected = normalize_eval_policy(case.expected_policy or "")
        assert result.policy_decision.gate == expected, f"{case_id}: got {result.policy_decision.gate}"
