"""Epistemic caps: conclusion strength vs evidence."""

from __future__ import annotations

from platform_core.reasoning import cap_conclusion_strength, observation, run_reasoning
from platform_core.reasoning.layers import EpistemicLayer, evidence_level_for_layer


def test_cap_downgrades_strong_without_confirmed_proof() -> None:
    assert cap_conclusion_strength(desired="strong", evidence_level="inferred", proof_status="NOT_RUN") == "moderate"


def test_cap_allows_strong_with_confirmed_proof() -> None:
    from platform_core.reasoning_models import ProofResult

    run = run_reasoning(
        [
            observation("ping_ok"),
            observation("dns_ok"),
            observation("browser_https_failed"),
            observation("wininet_proxy_enabled"),
            observation("proxy_bypass_succeeded"),
            observation("proxied_path_failed"),
        ],
        proof_result=ProofResult(
            hypothesis="browser_proxy_path_regression",
            status="CONFIRMED",
            checks_run=["contrast"],
        ),
        requested_action="restore_proxy",
        explicit_confirmation=True,
    )
    assert run.policy_decision.outcome == "ALLOW"


def test_layer_evidence_mapping() -> None:
    assert evidence_level_for_layer(EpistemicLayer.OBSERVATION) == "observed"
    assert evidence_level_for_layer(EpistemicLayer.PROOF) == "proof"
