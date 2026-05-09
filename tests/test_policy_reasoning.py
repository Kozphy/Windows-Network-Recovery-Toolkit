from __future__ import annotations

from platform_core.reasoning_engine import evaluate_reasoning_policy, observation, run_reasoning
from platform_core.reasoning_models import ProofResult, StateTransition


def _high_confidence_proxy_observations():
    return [
        observation("ping_ok"),
        observation("dns_ok"),
        observation("tcp443_ok"),
        observation("browser_https_failed"),
        observation("wininet_proxy_changed"),
        observation("wininet_proxy_enabled"),
        observation("localhost_proxy_detected"),
        observation("proxy_bypass_succeeded"),
        observation("proxied_path_failed"),
    ]


def test_unproven_high_confidence_remains_preview() -> None:
    run = run_reasoning(_high_confidence_proxy_observations(), requested_action="restore_proxy")
    assert run.hypothesis_ranking[0]["confidence"] >= 0.80
    assert run.proof_result.status == "NOT_RUN"
    assert run.policy_decision.outcome == "PREVIEW"
    assert "unproven_high_confidence_is_not_execute_authority" in run.policy_decision.reason_codes
    assert "high_impact_requires_confirmed_proof_before_execute" in run.policy_decision.reason_codes


def test_confirmed_proof_still_requires_confirmation_boundary() -> None:
    proof = ProofResult(
        hypothesis="browser_proxy_path_regression",
        status="CONFIRMED",
        confidence=0.95,
        checks_run=["proxy_bypass_contrast"],
    )
    preview_run = run_reasoning(_high_confidence_proxy_observations(), proof_result=proof, requested_action="restore_proxy")
    assert preview_run.policy_decision.outcome == "PREVIEW"
    assert preview_run.policy_decision.requires_confirmation is True

    allowed_run = run_reasoning(
        _high_confidence_proxy_observations(),
        proof_result=proof,
        requested_action="restore_proxy",
        explicit_confirmation=True,
    )
    assert allowed_run.policy_decision.outcome == "ALLOW"


def test_conflicting_signals_downgrade_policy() -> None:
    proof = ProofResult(hypothesis="browser_proxy_path_regression", status="CONFIRMED", confidence=0.95)
    run = run_reasoning(
        _high_confidence_proxy_observations() + [observation("browser_https_ok")],
        proof_result=proof,
        requested_action="restore_proxy",
        explicit_confirmation=True,
    )
    assert run.policy_decision.outcome == "PREVIEW"
    assert "conflicting_signals_downgrade_to_preview" in run.policy_decision.reason_codes


def test_high_risk_actions_remain_blocked() -> None:
    run = run_reasoning(_high_confidence_proxy_observations(), requested_action="firewall_reset")
    assert run.policy_decision.outcome == "BLOCK"
    assert "destructive_or_manual_only_action_blocked" in run.policy_decision.reason_codes


def _confirmed_proof() -> ProofResult:
    return ProofResult(
        hypothesis="browser_proxy_path_regression",
        status="CONFIRMED",
        confidence=0.95,
        checks_run=["proxy_bypass_contrast"],
    )


def _proven_transition() -> list[StateTransition]:
    return [
        StateTransition(
            from_state="browser_path_failure_suspected",
            to_state="proxy_path_failure_confirmed",
            rule_id="proxy_path_confirmed",
            confidence=0.92,
            evidence_level="validated",
        )
    ]


def test_high_impact_unconfirmed_proof_forces_preview_defense_in_depth() -> None:
    """Unconfirmed proof + high impact MUST downgrade to PREVIEW even if upstream gate were widened."""
    decision = evaluate_reasoning_policy(
        hypothesis="browser_proxy_path_regression",
        transitions=_proven_transition(),
        proof_result=ProofResult(hypothesis="browser_proxy_path_regression", status="NOT_RUN"),
        confidence=0.95,
        impact_level="high",
        requested_action="restore_proxy",
        explicit_confirmation=True,
        conflicting_signals=False,
    )
    assert decision.outcome == "PREVIEW"
    assert "high_impact_requires_confirmed_proof_before_execute" in decision.reason_codes
    assert "unproven_high_confidence_is_not_execute_authority" in decision.reason_codes


def test_critical_impact_low_trust_forces_preview_defense_in_depth() -> None:
    """Critical impact without high trust MUST downgrade to PREVIEW; reason code is a real gate."""
    decision = evaluate_reasoning_policy(
        hypothesis="browser_proxy_path_regression",
        transitions=_proven_transition(),
        proof_result=ProofResult(hypothesis="browser_proxy_path_regression", status="NOT_RUN"),
        confidence=0.97,
        impact_level="critical",
        requested_action="restore_proxy",
        explicit_confirmation=True,
        conflicting_signals=False,
    )
    assert decision.outcome == "PREVIEW"
    assert "critical_impact_requires_high_trust_for_execute_authority" in decision.reason_codes
    assert "high_impact_requires_confirmed_proof_before_execute" in decision.reason_codes


def test_critical_impact_with_confirmed_proof_and_confirmation_can_allow() -> None:
    """The defense-in-depth gates do not trip when proof is CONFIRMED, trust is high, and confirmation is present."""
    decision = evaluate_reasoning_policy(
        hypothesis="browser_proxy_path_regression",
        transitions=_proven_transition(),
        proof_result=_confirmed_proof(),
        confidence=0.95,
        impact_level="critical",
        requested_action="restore_proxy",
        explicit_confirmation=True,
        conflicting_signals=False,
    )
    assert decision.outcome == "ALLOW"
    assert "high_impact_requires_confirmed_proof_before_execute" not in decision.reason_codes
    assert "critical_impact_requires_high_trust_for_execute_authority" not in decision.reason_codes
    assert "unproven_high_confidence_is_not_execute_authority" not in decision.reason_codes
