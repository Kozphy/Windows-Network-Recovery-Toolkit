"""Benchmark metrics, baselines, ablation, and error analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.purple_team.models import FailureCategory, ScenarioRunResult


@dataclass
class ConfusionMetrics:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    @property
    def fnr(self) -> float:
        d = self.fn + self.tp
        return self.fn / d if d else 0.0

    @property
    def detection_rate(self) -> float:
        return self.recall

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "false_positive_rate": round(self.fpr, 4),
            "false_negative_rate": round(self.fnr, 4),
            "detection_rate": round(self.detection_rate, 4),
        }


@dataclass
class OperationalMetrics:
    mttd_values: list[float] = field(default_factory=list)
    remediation_success: list[bool] = field(default_factory=list)
    verification_success: list[bool] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        mttd = sum(self.mttd_values) / len(self.mttd_values) if self.mttd_values else None
        rem = (
            sum(1 for x in self.remediation_success if x) / len(self.remediation_success)
            if self.remediation_success
            else None
        )
        ver = (
            sum(1 for x in self.verification_success if x) / len(self.verification_success)
            if self.verification_success
            else None
        )
        return {
            "median_mttd_s": _median(self.mttd_values),
            "mean_mttd_s": mttd,
            "remediation_success_rate": rem,
            "verification_success_rate": ver,
            "n": len(self.mttd_values),
        }


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def accumulate_metrics(results: list[ScenarioRunResult]) -> dict[str, Any]:
    conf = ConfusionMetrics()
    ops = OperationalMetrics()
    per_scenario: list[dict[str, Any]] = []
    for r in results:
        conf.tp += int(r.true_positive)
        conf.fp += int(r.false_positive)
        conf.tn += int(r.true_negative)
        conf.fn += int(r.false_negative)
        mttd = r.timing.to_dict().get("mttd_s")
        if isinstance(mttd, (int, float)):
            ops.mttd_values.append(float(mttd))
        if r.remediation is not None:
            ops.remediation_success.append(bool(r.remediation.success and r.remediation.executed))
        if r.verification is not None:
            ops.verification_success.append(bool(r.verification.passed))
        fired = any(d.detected for d in r.detections)
        per_scenario.append(
            {
                "scenario_id": r.scenario_id,
                "detect": fired,
                "expect_detection": r.expected_detection,
                "tp": r.true_positive,
                "fp": r.false_positive,
                "tn": r.true_negative,
                "fn": r.false_negative,
                "mttd_s": mttd,
                "remediation": bool(r.remediation and r.remediation.success),
                "verified": bool(r.verification and r.verification.passed),
                "failure_category": r.failure_category.value,
            }
        )
    return {
        "confusion": conf.to_dict(),
        "operational": ops.to_dict(),
        "per_scenario": per_scenario,
        "scenario_coverage": len({r.scenario_id for r in results}),
    }


def classify_failure(result: ScenarioRunResult) -> FailureCategory:
    if result.failure_category != FailureCategory.NONE:
        return result.failure_category
    if result.false_negative:
        return FailureCategory.DETECTION_FALSE_NEGATIVE
    if result.false_positive:
        return FailureCategory.DETECTION_FALSE_POSITIVE
    if result.verification and not result.verification.passed:
        return FailureCategory.VERIFICATION_FAILURE
    if result.remediation and result.remediation.executed and not result.remediation.success:
        return FailureCategory.REMEDIATION_FAILURE
    return FailureCategory.NONE


def error_analysis_report(results: list[ScenarioRunResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in results:
        cat = classify_failure(r)
        if cat == FailureCategory.NONE and r.detection_matched_expectation:
            continue
        expected = r.scenario_id
        observed = [d.rule_id for d in r.detections if d.detected] or ["no detection"]
        rows.append(
            {
                "scenario_id": r.scenario_id,
                "run_id": r.run_id,
                "category": cat.value,
                "expected_detection": r.expected_detection,
                "observed": observed,
                "root_cause_hint": r.error
                or (
                    "detection outcome mismatched expectation"
                    if not r.detection_matched_expectation
                    else "see verification/remediation details"
                ),
                "improvement_hint": _improvement(cat),
            }
        )
        _ = expected
    return rows


def _improvement(cat: FailureCategory) -> str:
    return {
        FailureCategory.DETECTION_FALSE_NEGATIVE: "Widen correlation window or add telemetry source.",
        FailureCategory.DETECTION_FALSE_POSITIVE: "Strengthen authorized=true suppression / baselines.",
        FailureCategory.VERIFICATION_FAILURE: "Treat command success as insufficient; tighten post-conditions.",
        FailureCategory.TELEMETRY_MISSING: "Event-driven collector or fixture completeness check.",
        FailureCategory.SAFETY_DENIED: "Expected for unauthorized runs — use dry-run or lab token.",
    }.get(cat, "Inspect stage transitions and evidence bundle.")


BASELINE_NAMES = (
    "baseline_0_no_detection",
    "baseline_1_static_threshold",
    "baseline_2_repo_classifier_proxy",
    "proposed_purple_pipeline",
)


def baseline_compare(metrics_by_baseline: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "purple_baseline_compare.v1",
        "baselines": metrics_by_baseline,
        "notes": [
            "baseline_0 always predicts no detection.",
            "baseline_1 uses a static ProxyEnable==1 threshold on raw fixture after-state.",
            "baseline_2 reuses DET-PROXY-001 only (single-rule).",
            "proposed is the full purple pipeline.",
        ],
    }


ABLATION_PRESETS: dict[str, dict[str, bool]] = {
    "full": {},
    "minus_correlation": {"disable_correlation": True},
    "minus_verification": {"skip_verification": True},
    "minus_proxy_rule": {"disable_rules": True},
}
