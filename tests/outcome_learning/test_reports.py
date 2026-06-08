from __future__ import annotations

from platform_core.outcome_learning import (
    build_learning_report,
    evaluate_outcomes,
    metrics_payload,
    report_to_json,
    report_to_markdown,
)


def test_markdown_report_contains_metrics(sample_outcomes) -> None:
    evaluations = evaluate_outcomes(sample_outcomes)
    report = build_learning_report(evaluations, content_digest="abc123")
    md = report_to_markdown(report)
    assert "decision_accuracy" in md
    assert "decision_precision" in md
    assert "decision_recall" in md
    assert "average_cost" in md
    assert "abc123" in md


def test_json_report_round_trip(sample_outcomes) -> None:
    evaluations = evaluate_outcomes(sample_outcomes)
    report = build_learning_report(evaluations)
    blob = report_to_json(report)
    assert "decision_accuracy" in blob
    payload = metrics_payload(report.metrics)
    assert set(payload) == {
        "decision_accuracy",
        "decision_precision",
        "decision_recall",
        "average_cost",
        "average_time_to_resolution",
        "sample_count",
    }
