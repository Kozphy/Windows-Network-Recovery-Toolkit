"""Unified outcome tracking and learning metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.platform.models import DecisionOption, DecisionOutcome


@dataclass
class OutcomeMetrics:
    decision_accuracy: float
    success_rate: float
    average_confidence: float
    average_risk: float
    time_to_resolution: float
    success_rate_by_domain: dict[str, float] = field(default_factory=dict)
    failure_rate_by_decision_type: dict[str, float] = field(default_factory=dict)
    total_outcomes: int = 0


def record_outcome(
    decision: DecisionOption,
    *,
    success: bool,
    observed_result: str,
    cost_score: float = 0.0,
    time_to_resolution_seconds: float = 0.0,
    lessons_learned: str = "",
    outcome_id: str | None = None,
) -> DecisionOutcome:
    return DecisionOutcome(
        outcome_id=outcome_id or f"out-{decision.decision_id}",
        decision_id=decision.decision_id,
        success=success,
        observed_result=observed_result,
        cost_score=cost_score,
        time_to_resolution_seconds=time_to_resolution_seconds,
        lessons_learned=lessons_learned,
    )


def compute_metrics(
    outcomes: list[DecisionOutcome],
    decisions_by_id: dict[str, DecisionOption],
    *,
    domain_by_decision: dict[str, str] | None = None,
) -> OutcomeMetrics:
    domain_by_decision = domain_by_decision or {}
    if not outcomes:
        return OutcomeMetrics(0.0, 0.0, 0.0, 0.0, 0.0, total_outcomes=0)

    successes = sum(1 for o in outcomes if o.success)
    confidences: list[float] = []
    risks: list[float] = []
    times: list[float] = []
    by_domain: dict[str, list[bool]] = {}
    by_type: dict[str, list[bool]] = {}

    for oc in outcomes:
        dec = decisions_by_id.get(oc.decision_id)
        if dec:
            confidences.append(dec.confidence)
            risks.append(dec.risk_score)
            by_type.setdefault(dec.action_type, []).append(not oc.success)
        times.append(oc.time_to_resolution_seconds)
        dom = domain_by_decision.get(oc.decision_id, "unknown")
        by_domain.setdefault(dom, []).append(oc.success)

    return OutcomeMetrics(
        decision_accuracy=round(successes / len(outcomes), 4),
        success_rate=round(successes / len(outcomes), 4),
        average_confidence=round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        average_risk=round(sum(risks) / len(risks), 4) if risks else 0.0,
        time_to_resolution=round(sum(times) / len(times), 2) if times else 0.0,
        success_rate_by_domain={d: round(sum(v) / len(v), 4) for d, v in by_domain.items()},
        failure_rate_by_decision_type={t: round(sum(v) / len(v), 4) for t, v in by_type.items()},
        total_outcomes=len(outcomes),
    )


def metrics_to_dict(m: OutcomeMetrics) -> dict[str, Any]:
    return {
        "decision_accuracy": m.decision_accuracy,
        "success_rate": m.success_rate,
        "average_confidence": m.average_confidence,
        "average_risk": m.average_risk,
        "time_to_resolution": m.time_to_resolution,
        "success_rate_by_domain": m.success_rate_by_domain,
        "failure_rate_by_decision_type": m.failure_rate_by_decision_type,
        "total_outcomes": m.total_outcomes,
    }
