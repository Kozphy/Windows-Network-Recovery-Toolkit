"""Deterministic recurrence-risk baseline used when ML is unavailable or unapproved."""

from __future__ import annotations

from .contracts import ModelRecommendation, RiskFeatures


_BASELINE_VERSION = "1.0.0"


def deterministic_recurrence_score(
    incident_id: str,
    features: RiskFeatures,
    *,
    evidence_refs: list[str] | None = None,
) -> ModelRecommendation:
    """Return an explainable bounded score for review prioritization only."""
    score = 0.05
    reasons: list[str] = []

    if features.recurrence_count:
        contribution = min(features.recurrence_count * 0.12, 0.36)
        score += contribution
        reasons.append(f"Incident has {features.recurrence_count} recorded recurrence(s).")
    if features.failed_control_count:
        contribution = min(features.failed_control_count * 0.10, 0.30)
        score += contribution
        reasons.append(f"{features.failed_control_count} control test(s) failed.")
    if features.partial_control_count:
        contribution = min(features.partial_control_count * 0.04, 0.12)
        score += contribution
        reasons.append(f"{features.partial_control_count} control test(s) were partial.")
    if features.proxy_enabled and not features.listener_found:
        score += 0.16
        reasons.append("Proxy is enabled without a corroborating listener.")
    if features.proxy_probe_ok is False and features.direct_probe_ok is True:
        score += 0.12
        reasons.append("Direct path succeeds while the proxy path fails.")
    if not features.previous_restoration_verified:
        score += 0.08
        reasons.append("Previous restoration lacks independent verification.")
    if features.proof_tier < 2:
        score += 0.05
        reasons.append("Available evidence remains below runtime corroboration tier.")

    bounded = round(min(score, 1.0), 4)
    priority = "HIGH" if bounded >= 0.70 else "MEDIUM" if bounded >= 0.35 else "LOW"
    return ModelRecommendation(
        incident_id=incident_id,
        model_id="deterministic-recurrence-baseline",
        model_version=_BASELINE_VERSION,
        risk_score=bounded,
        review_priority=priority,
        explanation=reasons or ["No elevated recurrence indicators were present in the supplied features."],
        evidence_refs=evidence_refs or [],
        limitations=[
            "Score is a transparent prioritization heuristic, not a calibrated probability.",
            "Missing evidence is not inferred.",
        ],
    )
