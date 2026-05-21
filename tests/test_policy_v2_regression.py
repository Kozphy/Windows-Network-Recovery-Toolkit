"""Policy engine v2 reason codes and safety boundaries (offline)."""

from __future__ import annotations

from platform_core import policy_v2 as pv2
from platform_core.policy.engine import OperatorContext, evaluate
from platform_core.reasoning_engine import evaluate_reasoning_policy, observation, run_reasoning
from platform_core.reasoning_models import ProofResult, StateTransition
from src.decision_engine.hypothesis_decision import PolicyDecision, build_hypothesis_decisions
from src.proof.contracts import ProofStatus
from src.proof.contracts import ProofResult as CliProofResult


def test_high_confidence_unproven_stays_preview_with_v2_codes() -> None:
    run = run_reasoning(
        [
            observation("ping_ok"),
            observation("dns_ok"),
            observation("browser_https_failed"),
            observation("wininet_proxy_enabled"),
        ],
        requested_action="restore_proxy",
    )
    assert run.policy_decision.outcome == "PREVIEW"
    assert pv2.HIGH_CONFIDENCE_UNPROVEN in run.policy_decision.reason_codes
    assert "process_kill" in run.policy_decision.blocked_actions


def test_confirmed_safe_tier_with_confirmation_allows() -> None:
    proof = ProofResult(
        hypothesis="browser_proxy_path_regression",
        status="CONFIRMED",
        checks_run=["proxy_bypass_contrast"],
    )
    run = run_reasoning(
        [
            observation("ping_ok"),
            observation("dns_ok"),
            observation("tcp443_ok"),
            observation("browser_https_failed"),
            observation("wininet_proxy_enabled"),
            observation("proxy_bypass_succeeded"),
            observation("proxied_path_failed"),
        ],
        proof_result=proof,
        requested_action="restore_proxy",
        explicit_confirmation=True,
    )
    assert run.policy_decision.outcome == "ALLOW"
    assert pv2.CONFIRMED_SAFE_TIER_WITH_CONFIRMATION in run.policy_decision.reason_codes


def test_adapter_disable_and_process_kill_blocked_in_reasoning() -> None:
    for action in ("adapter_disable", "process_kill", "reset_firewall"):
        run = run_reasoning([observation("ping_ok")], requested_action=action)
        assert run.policy_decision.outcome == "BLOCK"
        assert pv2.DESTRUCTIVE_ACTION_BLOCKED in run.policy_decision.reason_codes


def test_platform_structured_policy_blocks_firewall_execute() -> None:
    gate = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert gate.execute_allowed is False
    assert "firewall_reset" in pv2.ALWAYS_BLOCKED_ACTIONS


def test_hypothesis_row_includes_reason_codes_when_unproven() -> None:
    rows = build_hypothesis_decisions(
        ranked=[("unexpected_user_proxy", 0.91, ("fixture",))],
        localhost_proxy_proof=None,
        proofs_enabled=True,
    )
    assert rows[0]["decision"] == PolicyDecision.PREVIEW.value
    assert pv2.HIGH_CONFIDENCE_UNPROVEN in rows[0]["reason_codes"]
    assert "process_kill" in rows[0]["blocked_actions"]


def test_heuristic_attribution_provider_never_proof() -> None:
    from platform_core.attribution.polling import PollingHeuristicProvider

    out = PollingHeuristicProvider().attribute({"process_names_sample": ["node.exe"]})
    assert out.confidence != "proof"


def test_evaluate_reasoning_policy_envelope_helper() -> None:
    pd = evaluate_reasoning_policy(
        hypothesis="browser_proxy_path_regression",
        transitions=[
            StateTransition(
                from_state="a",
                to_state="browser_path_failure_suspected",
                trigger_event_ids=[],
                rationale="fixture",
            )
        ],
        proof_result=ProofResult(hypothesis="browser_proxy_path_regression", status="NOT_RUN"),
        confidence=0.9,
        impact_level="high",
        requested_action="restore_proxy",
    )
    assert pd.outcome == "PREVIEW"
    assert pv2.HIGH_CONFIDENCE_UNPROVEN in pd.reason_codes


def test_confirmed_hypothesis_row_allow_carries_safe_tier_codes() -> None:
    pr = CliProofResult(
        proof_id="localhost_proxy_https_contrast",
        status=ProofStatus.CONFIRMED,
        hypothesis="fixture",
        summary="CONFIRMED",
    )
    rows = build_hypothesis_decisions(
        ranked=[("unexpected_user_proxy", 0.9, ("fixture",))],
        localhost_proxy_proof=pr,
        proofs_enabled=True,
    )
    assert rows[0]["decision"] == PolicyDecision.ALLOW.value
    assert pv2.SAFE_TIER_ACTION in rows[0]["reason_codes"]
