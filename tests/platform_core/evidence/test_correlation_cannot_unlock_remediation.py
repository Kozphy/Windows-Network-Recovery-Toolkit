"""Correlation-only must not unlock destructive remediation."""

from __future__ import annotations

from src.platform_core.evidence.guards import ProofInputs, can_unlock_destructive_remediation


def test_correlation_only_blocked() -> None:
    proof = ProofInputs(has_listener_correlation_only=True, has_registry_writer_telemetry=False)
    assert can_unlock_destructive_remediation("CORRELATED", proof) is False
