from __future__ import annotations

from platform_core.decision_pipeline_contract import (
    MIN_TIER_FOR_EXECUTE_AUTHORITY_PROXY_REGISTRY,
    ORDERED_PIPELINE_STAGES,
    policy_outcome_hint,
    resolve_evidence_tier,
    tier_ordinal,
)
from platform_core.reasoning_models import ProofResult


def test_ordered_pipeline_stages_length_and_monotonicity() -> None:
    assert len(ORDERED_PIPELINE_STAGES) == 10
    assert ORDERED_PIPELINE_STAGES[0] == "OBSERVE"
    assert ORDERED_PIPELINE_STAGES[-1] == "AUDIT"


def test_resolve_evidence_tier_confirmed_is_tier_3() -> None:
    proof = ProofResult(
        hypothesis="browser_proxy_path_regression",
        status="CONFIRMED",
        checks_run=["proxy_bypass_contrast"],
    )
    assert resolve_evidence_tier(proof=proof, observation_evidence_ceiling="observed") == "TIER_3_CAUSAL_PROOF"


def test_resolve_evidence_tier_inconclusive_with_checks_is_tier_2() -> None:
    proof = ProofResult(
        hypothesis="browser_proxy_path_regression",
        status="INCONCLUSIVE",
        checks_run=["proxy_bypass_contrast"],
    )
    assert resolve_evidence_tier(proof=proof) == "TIER_2_CONTRAST_TESTED"


def test_resolve_evidence_tier_not_run_falls_back_to_observation_ceiling() -> None:
    proof = ProofResult(hypothesis="browser_proxy_path_regression", status="NOT_RUN")
    assert resolve_evidence_tier(proof=proof, observation_evidence_ceiling="observed") == "TIER_0_RAW_OBSERVATION"
    assert resolve_evidence_tier(proof=proof, observation_evidence_ceiling="inferred") == "TIER_1_CORRELATED_SIGNAL"


def test_min_tier_constant_matches_tier_3() -> None:
    assert MIN_TIER_FOR_EXECUTE_AUTHORITY_PROXY_REGISTRY == "TIER_3_CAUSAL_PROOF"
    assert tier_ordinal("TIER_3_CAUSAL_PROOF") == 3


def test_policy_outcome_hint_registry_high_risk_needs_tier_3_and_confirm() -> None:
    assert (
        policy_outcome_hint(
            tier="TIER_2_CONTRAST_TESTED",
            requires_registry_mutation=True,
            explicit_confirmation=True,
            risk_tier_high_or_critical=True,
        )
        == "PREVIEW"
    )
    assert (
        policy_outcome_hint(
            tier="TIER_3_CAUSAL_PROOF",
            requires_registry_mutation=True,
            explicit_confirmation=True,
            risk_tier_high_or_critical=True,
        )
        == "ALLOW"
    )
