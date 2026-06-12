"""Risk scoring from classification and proof."""

from __future__ import annotations

from windows_network_toolkit.models import ClassificationResult, ProofResult


def score_risk(
    classification: ClassificationResult,
    proof: ProofResult | None = None,
) -> dict[str, object]:
    severity_map = {"info": 1, "low": 2, "medium": 3, "high": 4}
    base = severity_map.get(classification.severity, 2)
    score = classification.confidence * base
    if proof and proof.conclusion_status == "supported":
        score = min(4.0, score + 0.5)
    label = classification.severity
    if classification.primary_classification in {"SUSPICIOUS_PROXY", "POSSIBLE_MITM_RISK", "REVERTER_SUSPECTED"}:
        label = "high"
    return {
        "risk_level": label,
        "score": round(score, 2),
        "primary_classification": classification.primary_classification,
        "proof_status": proof.conclusion_status if proof else "not_run",
    }
