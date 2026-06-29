"""Reviewer proof contracts — deterministic governance spine (no live LLM).

Run with:
    pytest -q tests/reviewer/test_reviewer_proof_contracts.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.ai_risk_analyst.explanation_guardrails import validate_explanation_text
from src.platform_core.ai_risk_analyst.models import AnalystEvidenceBundle
from src.platform_core.ai_risk_analyst.providers.local_rule_based import LocalRuleBasedAnalyst
from src.platform_core.attribution.models import ProcessAttribution, ProxyStateSnapshot
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.classification.engine import classify_proxy
from src.platform_core.contracts import Decision, EvidenceBundle, EvidenceItem
from src.platform_core.governance.chain_of_custody import verify_chain
from src.platform_core.governance.proof_tier import resolve_proof_tier
from src.platform_core.policy.approval import generate_approval_token
from src.platform_core.policy.engine import evaluate_policy
from src.platform_core.remediation.planner import plan_proxy_drift_remediation
from src.platform_core.remediation.rollback import (
    ROLLBACK_LIMITATIONS,
    attempt_rollback_execute,
    build_rollback_preview_package,
    can_execute_rollback,
    capture_pre_change_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
DEAD_FIXTURE = ROOT / "fixtures" / "dead_proxy_config" / "raw_signals.json"


def _dead_signals() -> dict:
    return json.loads(DEAD_FIXTURE.read_text(encoding="utf-8"))


def test_classification_is_deterministic_and_includes_limitations() -> None:
    proxy = ProxyStateSnapshot(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:59081",
        winhttp_proxy_access_type="direct",
    )
    first = classify_proxy(proxy, ProcessAttribution(), listener_detected=False)
    second = classify_proxy(proxy, ProcessAttribution(), listener_detected=False)
    assert first["primary_classification"] == second["primary_classification"]
    assert first["limitations"]
    assert any("not" in lim.lower() or "correlation" in lim.lower() for lim in first["limitations"])


def test_proof_tier_carries_limitations() -> None:
    result = resolve_proof_tier(_dead_signals())
    assert result.limitations
    assert result.proof_tier_label


def test_policy_gate_preview_only_by_default() -> None:
    plan = plan_proxy_drift_remediation(
        incident_id="reviewer-inc",
        signals={"evidence_tier": "OBSERVED_ONLY"},
        dry_run=True,
    )
    assert plan["dry_run"] is True
    assert plan["approval"]["can_execute"] is False
    assert plan["policy_gate"]["outcome"] in {"PREVIEW_ONLY", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}


def test_policy_engine_blocks_weak_tier_without_proof() -> None:
    bundle = EvidenceBundle(
        bundle_id="b-1",
        incident_id="i-1",
        created_at="2026-01-01T00:00:00Z",
        tier="OBSERVED_ONLY",
        items=[
            EvidenceItem(
                evidence_id="e1",
                event_id="i-1",
                timestamp_utc="2026-01-01T00:00:00Z",
                source="test",
                signal="wininet_proxy_enabled",
                observed_value="true",
                tier="OBSERVED_ONLY",
            )
        ],
    )
    decision = Decision(
        decision_id="d-1",
        incident_id="i-1",
        timestamp_utc="2026-01-01T00:00:00Z",
        incident_type="WININET_PROXY_DRIFT",
        recommended_action="disable_wininet_proxy",
        confidence=0.5,
        risk_level="medium",
        evidence_tier="OBSERVED_ONLY",
        requires_human_review=True,
        reasoning="test",
    )
    pe = evaluate_policy(
        decision=decision,
        bundle=bundle,
        requested_action="disable_wininet_proxy",
        dry_run=True,
    )
    assert pe.outcome in {"PREVIEW_ONLY", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}


def test_audit_hash_chain_detects_tampering(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "audit.jsonl"
    r1 = append_audit("event_received", incident_id="inc-a", path=path)
    r2 = append_audit("policy_evaluated", incident_id="inc-a", path=path)
    ok, _ = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True
    tampered = dict(r2.model_dump())
    tampered["incident_id"] = "tampered"
    ok2, msg = verify_chain([r1.model_dump(), tampered])
    assert ok2 is False
    assert msg


def test_rollback_preview_never_executes_live() -> None:
    token = generate_approval_token()
    snapshot = capture_pre_change_snapshot(endpoint_id="ep", incident_id="inc", proxy_enable=1)
    from src.platform_core.remediation.rollback import build_proposed_mutation_preview

    package = build_rollback_preview_package(
        endpoint_id="ep",
        incident_id="inc",
        action_id="disable_wininet_proxy",
        pre_change_snapshot=snapshot,
        proposed_mutation=build_proposed_mutation_preview(action_id="disable_wininet_proxy", endpoint_id="ep"),
        approval_token=token,
        dry_run=False,
    )
    assert package["limitations"] == ROLLBACK_LIMITATIONS
    can, reason = can_execute_rollback(
        dry_run=False,
        confirmation_token=token,
        expected_token=token,
        typed_confirmation="RESTORE_PROXY_LKG",
    )
    assert can is False
    result = attempt_rollback_execute(
        package,
        confirmation_token=token,
        typed_confirmation="RESTORE_PROXY_LKG",
        dry_run=False,
    )
    assert result["executed"] is False
    assert reason == "live_rollback_executor_disabled_preview_only" or not result["can_execute"]


def test_ai_explanation_guardrails_reject_unsafe_authority() -> None:
    unsafe = "Malware confirmed. AI approved remediation. Safe to disable automatically."
    result = validate_explanation_text(unsafe)
    assert result.is_safe is False
    assert result.violations


def test_rule_based_analyst_default_has_limitations() -> None:
    analyst = LocalRuleBasedAnalyst()
    rec = analyst.analyze(
        AnalystEvidenceBundle(
            incident_id="i-1",
            classification={"primary_classification": "DEAD_PROXY_CONFIG"},
            proxy_status={"proxy_server": "127.0.0.1:59081"},
        )
    )
    assert rec.limitations
    assert rec.provider == "local_rule_based"
