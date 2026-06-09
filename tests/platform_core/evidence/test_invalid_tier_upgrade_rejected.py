"""Invalid tier upgrades rejected."""

from __future__ import annotations

from src.platform_core.evidence.guards import ProofInputs, validate_tier_upgrade


def test_manual_final_causation_override_rejected() -> None:
    proof = ProofInputs(manual_tier_override=True)
    ok, reason = validate_tier_upgrade("OBSERVED_ONLY", "FINAL_CAUSATION", proof)
    assert ok is False
    assert "forbidden" in reason.lower()


def test_final_without_proof_rejected() -> None:
    proof = ProofInputs()
    ok, _ = validate_tier_upgrade("OBSERVED_ONLY", "FINAL_CAUSATION", proof)
    assert ok is False
