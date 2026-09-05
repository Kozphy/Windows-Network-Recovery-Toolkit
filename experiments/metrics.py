"""Classification, evidence, safety, and reproducibility metrics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from experiments.baselines.b3_full_platform import meets_min_tier
from experiments.baselines.base import BaselinePrediction
from experiments.dataset import BenchmarkCaseV1

_ABSTAIN_CLASSES = {
    "ERROR_INSUFFICIENT_DATA",
    "INSUFFICIENT_DATA",
    "UNKNOWN",
}


def _normalize_label(label: str) -> str:
    token = label.strip().upper().replace("-", "_")
    if token in {"INSUFFICIENT_DATA", "ERROR_INSUFFICIENT_DATA"}:
        return "INSUFFICIENT_DATA"
    return token


def _normalize_policy(policy: str) -> str:
    token = _normalize_label(policy)
    aliases = {
        "HUMAN_REVIEW": "HUMAN_REVIEW",
        "REQUIRE_HUMAN_REVIEW": "HUMAN_REVIEW",
        "ALLOW_PREVIEW": "PREVIEW_ONLY",
    }
    return aliases.get(token, token)


@dataclass
class ClassificationMetrics:
    baseline: str
    sample_size: int
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    micro_f1: float
    false_positive_rate: float
    false_negative_rate: float
    supported_classification_rate: float
    unsupported_rate: float
    abstention_rate: float
    exact_match_count: int = 0


@dataclass
class EvidenceMetrics:
    baseline: str
    sample_size: int
    explicit_evidence_rate: float
    explicit_limitations_rate: float
    proof_tier_met_rate: float
    contradiction_rate: float
    incomplete_downgrade_rate: float
    unsupported_claim_rate: float


@dataclass
class SafetyMetrics:
    baseline: str
    sample_size: int
    unsafe_action_proposal_rate: float
    correctly_preview_only_rate: float
    policy_match_rate: float
    remediation_match_rate: float
    audit_verification_rate: float


def _per_class_prf(
    y_true: list[str],
    y_pred: list[str],
    *,
    labels: list[str],
) -> tuple[float, float, float, dict[str, dict[str, float]]]:
    per_class: dict[str, dict[str, float]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        per_class[label] = {"precision": prec, "recall": rec, "f1": f1, "support": tp + fn}
        if tp + fn > 0:
            precisions.append(prec)
            recalls.append(rec)
            f1s.append(f1)
    macro_p = sum(precisions) / len(precisions) if precisions else 0.0
    macro_r = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    return macro_p, macro_r, macro_f1, per_class


def classification_match(
    predicted: BaselinePrediction,
    case: BenchmarkCaseV1,
) -> bool:
    pred = _normalize_label(predicted.predicted_incident_class)
    expected = _normalize_label(case.expected_incident_class)
    if case.ambiguity_allowed and pred != expected:
        return False
    return pred == expected


def compute_classification_metrics(
    baseline: str,
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
) -> tuple[ClassificationMetrics, dict[str, dict[str, float]], list[str], list[list[int]]]:
    y_true = [_normalize_label(c.expected_incident_class) for c in cases]
    y_pred = [_normalize_label(p.predicted_incident_class) for p in predictions]
    labels = sorted(set(y_true) | set(y_pred))
    exact = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p)
    accuracy = exact / len(cases) if cases else 0.0
    macro_p, macro_r, macro_f1, per_class = _per_class_prf(y_true, y_pred, labels=labels)
    tp_sum = fp_sum = fn_sum = 0
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == label and p != label)
        tp_sum += tp
        fp_sum += fp
        fn_sum += fn
    micro_p = tp_sum / (tp_sum + fp_sum) if (tp_sum + fp_sum) else 0.0
    micro_r = tp_sum / (tp_sum + fn_sum) if (tp_sum + fn_sum) else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) else 0.0

    _healthy = {"DIRECT_OK", "BOTH_DIRECT_AND_PROXY_WORK", "LOCAL_PROXY_ACTIVE"}
    pos_expected = [t for t in y_true if t not in _ABSTAIN_CLASSES and t not in _healthy]
    neg_expected = [t for t in y_true if t in _healthy]
    fp_count = sum(
        1
        for t, p in zip(y_true, y_pred, strict=True)
        if t in _healthy and p not in _healthy and p not in _ABSTAIN_CLASSES
    )
    fn_count = sum(
        1
        for t, p in zip(y_true, y_pred, strict=True)
        if t not in _healthy
        and t not in _ABSTAIN_CLASSES
        and (p in _ABSTAIN_CLASSES or p in _healthy)
    )
    fpr = fp_count / len(neg_expected) if neg_expected else 0.0
    fnr = fn_count / len(pos_expected) if pos_expected else 0.0

    unsupported = sum(
        1 for p in predictions if p.unsupported or p.predicted_incident_class == "UNKNOWN"
    )
    abstained = sum(
        1 for p in predictions if p.abstained or p.predicted_incident_class in _ABSTAIN_CLASSES
    )
    supported = sum(
        1
        for p in predictions
        if p.supporting_evidence
        and not p.abstained
        and p.predicted_incident_class not in _ABSTAIN_CLASSES
    )
    metrics = ClassificationMetrics(
        baseline=baseline,
        sample_size=len(cases),
        accuracy=accuracy,
        macro_precision=macro_p,
        macro_recall=macro_r,
        macro_f1=macro_f1,
        micro_f1=micro_f1,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        supported_classification_rate=supported / len(cases) if cases else 0.0,
        unsupported_rate=unsupported / len(cases) if cases else 0.0,
        abstention_rate=abstained / len(cases) if cases else 0.0,
        exact_match_count=exact,
    )
    label_index = {label: idx for idx, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[label_index[t]][label_index[p]] += 1
    return metrics, per_class, labels, matrix


def compute_evidence_metrics(
    baseline: str,
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
) -> EvidenceMetrics:
    n = len(cases)
    with_evidence = sum(1 for p in predictions if p.supporting_evidence)
    with_limits = sum(1 for p in predictions if p.limitations)
    tier_met = sum(
        1
        for p, c in zip(predictions, cases, strict=True)
        if meets_min_tier(p.proof_tier, c.expected_min_proof_tier)
    )
    contradictions = 0
    downgrades = 0
    for p, c in zip(predictions, cases, strict=True):
        pred = _normalize_label(p.predicted_incident_class)
        exp = _normalize_label(c.expected_incident_class)
        if pred != exp and p.abstained:
            downgrades += 1
        if len(p.supporting_evidence) >= 2 and pred != exp:
            if "mismatch" in pred.lower() or "dead" in pred.lower():
                contradictions += 1
    unsupported_claims = sum(1 for p in predictions if p.unsupported)
    return EvidenceMetrics(
        baseline=baseline,
        sample_size=n,
        explicit_evidence_rate=with_evidence / n if n else 0.0,
        explicit_limitations_rate=with_limits / n if n else 0.0,
        proof_tier_met_rate=tier_met / n if n else 0.0,
        contradiction_rate=contradictions / n if n else 0.0,
        incomplete_downgrade_rate=downgrades / n if n else 0.0,
        unsupported_claim_rate=unsupported_claims / n if n else 0.0,
    )


def compute_safety_metrics(
    baseline: str,
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
) -> SafetyMetrics:
    n = len(cases)
    unsafe = sum(1 for p in predictions if p.unsafe_action_proposed)
    preview_ok = sum(
        1
        for p, c in zip(predictions, cases, strict=True)
        if _normalize_policy(p.remediation_posture) in {"PREVIEW_ONLY", "NONE", "BLOCK"}
        and c.expected_remediation_posture in {"PREVIEW_ONLY", "NONE", "BLOCK"}
    )
    policy_match = sum(
        1
        for p, c in zip(predictions, cases, strict=True)
        if _normalize_policy(p.policy_posture) == _normalize_policy(c.expected_policy_posture)
        or c.ambiguity_allowed
    )
    remediation_match = sum(
        1
        for p, c in zip(predictions, cases, strict=True)
        if _normalize_policy(p.remediation_posture)
        == _normalize_policy(c.expected_remediation_posture)
    )
    audit_rate = sum(1 for p in predictions if p.audit_verified is True) / n if n else 0.0
    return SafetyMetrics(
        baseline=baseline,
        sample_size=n,
        unsafe_action_proposal_rate=unsafe / n if n else 0.0,
        correctly_preview_only_rate=preview_ok / n if n else 0.0,
        policy_match_rate=policy_match / n if n else 0.0,
        remediation_match_rate=remediation_match / n if n else 0.0,
        audit_verification_rate=audit_rate,
    )


def write_predictions_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    write_predictions_csv(path, rows)


def write_confusion_matrix_csv(
    path: Path,
    labels: list[str],
    matrix: list[list[int]],
    baseline: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["baseline", "expected\\predicted", *labels])
        for label, row in zip(labels, matrix, strict=True):
            writer.writerow([baseline, label, *row])


def predictions_to_rows(
    cases: list[BenchmarkCaseV1],
    predictions: list[BaselinePrediction],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case, pred in zip(cases, predictions, strict=True):
        rows.append(
            {
                "case_id": case.case_id,
                "baseline": pred.baseline,
                "split": case.split,
                "expected": case.expected_incident_class,
                "predicted": pred.predicted_incident_class,
                "primary_match": _normalize_label(pred.predicted_incident_class)
                == _normalize_label(case.expected_incident_class),
                "proof_tier": pred.proof_tier,
                "expected_min_proof_tier": case.expected_min_proof_tier,
                "policy_posture": pred.policy_posture,
                "expected_policy_posture": case.expected_policy_posture,
                "remediation_posture": pred.remediation_posture,
                "abstained": pred.abstained,
                "unsupported": pred.unsupported,
                "unsafe_action_proposed": pred.unsafe_action_proposed,
                "supporting_evidence_count": len(pred.supporting_evidence),
                "limitations_count": len(pred.limitations),
            }
        )
    return rows
