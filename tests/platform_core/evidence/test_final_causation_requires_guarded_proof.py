"""FINAL_CAUSATION requires guarded proof."""

from __future__ import annotations

from src.platform_core.evidence.guards import ProofInputs, validate_tier_upgrade


def test_final_causation_with_full_proof() -> None:
    proof = ProofInputs(
        has_registry_writer_telemetry=True,
        has_process_lineage=True,
        has_timestamp_alignment=True,
        has_path_validation=True,
    )
    ok, reason = validate_tier_upgrade("PROVEN_REGISTRY_WRITER", "FINAL_CAUSATION", proof)
    assert ok is True
    assert "guarded" in reason
