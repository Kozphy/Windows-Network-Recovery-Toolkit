"""Decision explanations — why hypotheses win and what proof is missing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.platform_core.evidence.conflicts import EvidenceConflict, detect_conflicts
from src.platform_core.evidence.tiers import EvidenceTier, tier_rank


@dataclass
class DecisionExplanation:
    preferred_hypothesis: str
    why_selected: str
    missing_proof: list[str]
    unjustified_claims: list[str]
    conflicts: list[EvidenceConflict]


def build_explanation(
    *,
    incident_type: str,
    evidence_tier: EvidenceTier,
    confidence: float,
    signals: dict[str, Any],
    reasoning: str = "",
) -> DecisionExplanation:
    conflicts = detect_conflicts(signals)
    missing: list[str] = []
    unjustified: list[str] = []

    if tier_rank(evidence_tier) < tier_rank("PROVEN_REGISTRY_WRITER"):
        missing.append("Registry writer telemetry (e.g. Sysmon EID 13)")
    if tier_rank(evidence_tier) < tier_rank("PROVEN_NETWORK_IMPACT"):
        missing.append("Network path validation (direct vs proxy contrast)")
    if tier_rank(evidence_tier) < tier_rank("FINAL_CAUSATION"):
        missing.append("Process lineage + timestamp alignment for final causation")

    if tier_rank(evidence_tier) < tier_rank("FINAL_CAUSATION"):
        unjustified.append("Claiming certain root cause / writer identity")
    if tier_rank(evidence_tier) < tier_rank("CORRELATED"):
        unjustified.append("Attributing failure to a specific process")

    why = reasoning or f"Incident type {incident_type} ranked with ordinal confidence {confidence:.2f}."
    if conflicts:
        why += f" {len(conflicts)} signal conflict(s) limit stronger claims."

    return DecisionExplanation(
        preferred_hypothesis=incident_type,
        why_selected=why,
        missing_proof=missing,
        unjustified_claims=unjustified,
        conflicts=conflicts,
    )
