"""Canonical evidence tier enum and transition contracts."""

from __future__ import annotations

from src.platform_core.evidence.guards import ProofInputs, validate_tier_upgrade
from src.platform_core.evidence.tiers import EVIDENCE_TIER_ORDER, normalize_tier, tier_rank


def test_canonical_tier_order() -> None:
    assert EVIDENCE_TIER_ORDER == (
        "OBSERVED_ONLY",
        "CORRELATED",
        "PROVEN_REGISTRY_WRITER",
        "PROVEN_NETWORK_IMPACT",
        "FINAL_CAUSATION",
    )


def test_legacy_alias_normalization() -> None:
    assert normalize_tier("CORRELATED_PROCESS") == "CORRELATED"
    assert normalize_tier("PATH_VALIDATED") == "PROVEN_NETWORK_IMPACT"
    assert normalize_tier("PROVEN_NETWORK_IMPACT") == "PROVEN_NETWORK_IMPACT"


def test_cannot_skip_to_final_causation() -> None:
    ok, _ = validate_tier_upgrade("OBSERVED_ONLY", "FINAL_CAUSATION", ProofInputs())
    assert ok is False


def test_correlated_to_network_impact_requires_path_proof() -> None:
    ok, _ = validate_tier_upgrade("CORRELATED", "PROVEN_NETWORK_IMPACT", ProofInputs())
    assert ok is False
    ok2, _ = validate_tier_upgrade(
        "CORRELATED",
        "PROVEN_NETWORK_IMPACT",
        ProofInputs(has_path_validation=True),
    )
    assert ok2 is True


def test_tier_rank_monotonic() -> None:
    ranks = [tier_rank(t) for t in EVIDENCE_TIER_ORDER]
    assert ranks == sorted(ranks)
