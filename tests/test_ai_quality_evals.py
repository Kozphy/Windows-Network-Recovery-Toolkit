from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.ai_risk_analyst.evals import (
    EvalCase,
    QualityThresholds,
    evaluate,
    load_jsonl,
    quality_gate,
)


def test_metrics_and_gate_pass_for_safe_predictions() -> None:
    cases = [
        EvalCase(case_id="1", expected_class="DEAD_PROXY", predicted_class="DEAD_PROXY"),
        EvalCase(case_id="2", expected_class="HEALTHY", predicted_class="HEALTHY"),
        EvalCase(
            case_id="3",
            expected_class="UNKNOWN",
            predicted_class="UNKNOWN",
            abstained=True,
        ),
    ]
    metrics = evaluate(cases)

    assert metrics.macro_f1 == pytest.approx(1.0)
    assert metrics.schema_valid_rate == pytest.approx(1.0)
    assert metrics.unsafe_action_rate == pytest.approx(0.0)
    assert metrics.abstention_rate == pytest.approx(1 / 3)
    assert quality_gate(
        metrics,
        QualityThresholds(max_abstention_rate=0.34),
    ) == []


def test_gate_blocks_unsafe_regression_even_when_f1_is_perfect() -> None:
    metrics = evaluate(
        [
            EvalCase(
                case_id="unsafe",
                expected_class="DEAD_PROXY",
                predicted_class="DEAD_PROXY",
                unsafe_action=True,
            )
        ]
    )

    failures = quality_gate(metrics, QualityThresholds())

    assert any("unsafe_action_rate" in failure for failure in failures)


def test_abstention_counts_as_false_negative_when_no_class_is_returned() -> None:
    metrics = evaluate(
        [
            EvalCase(
                case_id="abstain",
                expected_class="DEAD_PROXY",
                predicted_class=None,
                abstained=True,
            ),
            EvalCase(case_id="healthy", expected_class="HEALTHY", predicted_class="HEALTHY"),
        ]
    )

    assert metrics.macro_f1 < 1.0
    assert metrics.abstention_rate == pytest.approx(0.5)


def test_load_jsonl_reports_bad_line_number(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "valid",
                "expected_class": "HEALTHY",
                "predicted_class": "HEALTHY",
            }
        )
        + "\nnot-json\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r":2: invalid evaluation case"):
        load_jsonl(dataset)
