"""Structured error analysis for B3 failures."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1
from experiments.metrics import _normalize_label


def categorize_failure(
    case: BenchmarkCaseV1,
    prediction: BaselinePrediction,
) -> str:
    pred = _normalize_label(prediction.predicted_incident_class)
    expected = _normalize_label(case.expected_incident_class)
    if pred == expected:
        return "none"
    if prediction.abstained or pred in {"ERROR_INSUFFICIENT_DATA", "INSUFFICIENT_DATA"}:
        return "insufficient_evidence"
    if len(prediction.supporting_evidence) >= 2 and pred != expected:
        return "cross_signal_interaction"
    if case.provenance_category == "contradictory_evidence":
        return "contradictory_evidence"
    if case.provenance_category == "incomplete_evidence":
        return "insufficient_evidence"
    if case.ambiguity_allowed:
        return "label_ambiguity"
    if case.provenance_category == "adversarial_edge_case":
        return "fixture_artifact"
    if "mismatch" in pred or "mismatch" in expected:
        return "rule_boundary"
    if prediction.proof_tier != case.expected_min_proof_tier:
        return "proof_tier_failure"
    return "unknown_requires_human_review"


def build_error_analysis_rows(
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case, pred in zip(cases, predictions, strict=True):
        if _normalize_label(pred.predicted_incident_class) == _normalize_label(
            case.expected_incident_class
        ):
            continue
        category = categorize_failure(case, pred)
        rows.append(
            {
                "case_id": case.case_id,
                "expected": case.expected_incident_class,
                "predicted": pred.predicted_incident_class,
                "proof_tier": pred.proof_tier,
                "expected_min_proof_tier": case.expected_min_proof_tier,
                "failure_category": category,
                "supporting_evidence": "|".join(pred.supporting_evidence[:5]),
                "limitations": "|".join(pred.limitations[:3]),
                "provenance_category": case.provenance_category,
                "ambiguity_allowed": case.ambiguity_allowed,
                "root_cause_note": case.notes or category,
            }
        )
    return rows


def summarize_failure_modes(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        cat = row["failure_category"]
        counts[cat] = counts.get(cat, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def write_error_analysis_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "expected",
        "predicted",
        "proof_tier",
        "expected_min_proof_tier",
        "failure_category",
        "supporting_evidence",
        "limitations",
        "provenance_category",
        "ambiguity_allowed",
        "root_cause_note",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
