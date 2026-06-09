"""Explainable ordinal confidence scoring."""

from __future__ import annotations

_RANK_TO_FLOAT = {"low": 0.45, "medium": 0.72, "high": 0.88}
_EVIDENCE_BONUS = {
    "OBSERVED_ONLY": 0.0,
    "CORRELATED": 0.05,
    "PROVEN_REGISTRY_WRITER": 0.12,
    "PROVEN_NETWORK_IMPACT": 0.15,
    "FINAL_CAUSATION": 0.18,
}


def ordinal_confidence(rank: str, *, evidence_level: str | None = None) -> float:
    base = _RANK_TO_FLOAT.get(str(rank).lower(), 0.5)
    bonus = _EVIDENCE_BONUS.get(str(evidence_level or "").upper(), 0.0)
    return min(0.98, base + bonus)


def explain_confidence(rank: str, *, evidence_level: str | None = None, supporting: list[str] | None = None) -> str:
    score = ordinal_confidence(rank, evidence_level=evidence_level)
    parts = [f"Ordinal confidence {score:.2f} derived from rank={rank!r}."]
    if evidence_level:
        parts.append(f"Evidence tier {evidence_level} adjusts score (not calibrated probability).")
    if supporting:
        parts.append(f"Supporting signals: {', '.join(supporting)}.")
    parts.append("Confidence is not certainty; correlation is not causation.")
    return " ".join(parts)
