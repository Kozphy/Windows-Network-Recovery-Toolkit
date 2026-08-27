"""Interpretable risk score — weights are documented assumptions, not science."""

from __future__ import annotations

from src.purple_team.models import DetectionResult, RiskScore, ScenarioDefinition

ASSUMPTIONS = [
    "Weights are engineering heuristics for lab control validation, not actuarial risk.",
    "detection_confidence is necessary but not sufficient for remediation authorization.",
    "Higher confidence alone cannot override safety policy (enforced outside this scorer).",
]

WEIGHTS = {
    "detection_confidence": 0.30,
    "asset_criticality": 0.20,
    "configuration_sensitivity": 0.20,
    "persistence": 0.15,
    "deviation": 0.15,
}


def _band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    if score >= 0.20:
        return "low"
    return "info"


def score_risk(
    scenario: ScenarioDefinition,
    detections: list[DetectionResult],
) -> RiskScore:
    det = next((d for d in detections if d.detected), None)
    detection_confidence = det.confidence if det else 0.0
    asset_criticality = {"low": 0.3, "medium": 0.55, "high": 0.8, "critical": 0.95}.get(
        scenario.risk_level.lower(), 0.4
    )
    configuration_sensitivity = 0.7 if "proxy" in scenario.category else 0.45
    persistence = 0.6 if scenario.expect_detection else 0.2
    deviation = detection_confidence

    components = {
        "detection_confidence": detection_confidence,
        "asset_criticality": asset_criticality,
        "configuration_sensitivity": configuration_sensitivity,
        "persistence": persistence,
        "deviation": deviation,
    }
    score = sum(WEIGHTS[k] * components[k] for k in WEIGHTS)
    return RiskScore(
        score=round(score, 4),
        band=_band(score),
        components=components,
        assumptions=list(ASSUMPTIONS),
        limitations=[
            "Risk score is ordinal lab guidance — not a threat attribution claim.",
            "Weights are not scientifically established.",
        ],
    )
