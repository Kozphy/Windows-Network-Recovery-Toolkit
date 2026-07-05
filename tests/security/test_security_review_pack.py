"""Security review pack — CI contracts for Phase 7 guarantees.

Complements (does not replace):
  tests/test_policy_safety_contract.py
  tests/policy/test_safety_boundaries.py
  tests/test_governance_safety_contracts.py
  tests/windows_network_toolkit/test_safety_contract.py
  tests/security/*
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from platform_core.policy import OperatorContext, evaluate, validate_confirmation_phrase
from platform_core.remediation_registry import get_remediation_action
from src.network_recovery.remediation_executor import execute_low_risk_action
from src.platform_core.ai_risk_analyst.guardrails import enforce_advisory_only
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain
from windows_network_toolkit.evidence_schema import EvidenceEvent
from windows_network_toolkit.incident_classifier import classify_incident_from_events
from windows_network_toolkit.models import ClassificationResult
from windows_network_toolkit.platform.policy import evaluate_policy
from windows_network_toolkit.proxy_remediation import run_proxy_disable
from windows_network_toolkit.safety import BLOCKED_ACTIONS, is_blocked_action

REPO = Path(__file__).resolve().parents[2]


def _dead_classification() -> ClassificationResult:
    return ClassificationResult(
        primary_classification="DEAD_PROXY_CONFIG",
        secondary_signals=["DEAD_LOCALHOST_PORT"],
        severity="medium",
        confidence=0.92,
        reasoning="dead proxy",
        evidence=[],
        recommended_next_actions=[],
        limitations=[],
    )


# --- Dangerous actions blocked by default (safety.py + policy) ---


@pytest.mark.parametrize(
    "blocked_id",
    sorted(BLOCKED_ACTIONS),
)
def test_blocked_destructive_actions_denied_by_safety_registry(blocked_id: str) -> None:
    assert is_blocked_action(blocked_id)
    decision = evaluate_policy(
        blocked_id,
        _dead_classification(),
        dry_run=False,
        confirmation=blocked_id,
    )
    assert decision.allowed is False
    assert any("blocked" in check for check in decision.safety_checks)


def test_process_kill_blocked_by_default() -> None:
    gate = evaluate({}, "process_kill_forbidden", OperatorContext(role="admin", surface="api"))
    assert gate.execute_allowed is False
    assert gate.preview_allowed is False


def test_firewall_reset_blocked_by_default() -> None:
    gate = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert gate.execute_allowed is False
    assert "firewall_or_adapter_manual_only" in gate.reason_codes


def test_adapter_disable_blocked_by_default() -> None:
    gate = evaluate({}, "adapter_disable_forbidden", OperatorContext(role="admin", surface="api"))
    assert gate.execute_allowed is False
    assert gate.preview_allowed is False


# --- Registry mutation blocked without typed confirmation ---


def test_registry_mutation_blocked_by_default_without_confirmation() -> None:
    """WinINET disable stays preview-only until dry_run=false AND exact token."""
    preview = evaluate_policy(
        "DISABLE_WININET_PROXY",
        _dead_classification(),
        dry_run=True,
        confirmation="",
    )
    assert preview.allowed is False
    assert preview.requires_confirmation is True

    wrong_token = evaluate_policy(
        "DISABLE_WININET_PROXY",
        _dead_classification(),
        dry_run=False,
        confirmation="WRONG",
    )
    assert wrong_token.allowed is False

    with patch("windows_network_toolkit.proxy_remediation.platform.system", return_value="Windows"), patch(
        "windows_network_toolkit.proxy_remediation.read_proxy_registry"
    ) as mock_reg, patch(
        "windows_network_toolkit.proxy_remediation.collect_proxy_state_model"
    ) as mock_state, patch(
        "windows_network_toolkit.proxy_remediation.decide"
    ) as mock_decide:
        from src.core.models import ProxyRegistrySnapshot

        mock_reg.return_value = ProxyRegistrySnapshot(
            proxy_enable=1,
            proxy_server="127.0.0.1:59081",
            auto_config_url=None,
            auto_detect=None,
        )
        mock_state.return_value.to_dict.return_value = {"wininet_proxy_enabled": True}
        mock_decide.return_value = {
            "proof": {"hypothesis": "dead proxy"},
            "classification": {"limitations": []},
            "policy_decision": {},
        }
        result = run_proxy_disable(dry_run=True, confirm="")
    assert result["dry_run"] is True
    assert result["no_changes_made"] is True


def test_remediation_requires_typed_human_confirmation() -> None:
    for key in ("reset_proxy", "reset_dns", "stop_proxy_listener"):
        defn = get_remediation_action(key)
        assert defn is not None, key
        assert defn.requires_confirmation is True
        assert defn.confirmation_phrase.strip() != ""
        assert validate_confirmation_phrase(key, "") is False
        assert validate_confirmation_phrase(key, defn.confirmation_phrase) is True

    gate = evaluate({"summary": "dns"}, "reset_dns", OperatorContext(role="operator", surface="api"))
    assert gate.preview_allowed is True
    assert gate.execute_allowed is False

    admin_gate = evaluate({"summary": "dns"}, "reset_dns", OperatorContext(role="admin", surface="api"))
    assert admin_gate.required_confirmation
    assert validate_confirmation_phrase("reset_dns", "") is False


def test_chatgpt_executor_blocks_medium_risk_actions_even_when_confirmed() -> None:
    with pytest.raises(ValueError, match="blocked from automated execution"):
        execute_low_risk_action("kill_unknown_processes", dry_run=False)


# --- AI cannot authorize execution ---


def test_ai_cannot_authorize_execution() -> None:
    payloads = [
        {"execution_authority": "full_auto", "summary": "Safe to execute automatically."},
        {"execution_authority": "automated_execute", "narrative": "execute automatically now"},
        {"execution_authority": "auto_apply", "recommended_action": "DISABLE_WININET_PROXY"},
    ]
    allowed_authorities = {"preview_only", "human_required", "blocked"}
    for raw in payloads:
        sanitized = enforce_advisory_only(raw)
        assert sanitized["execution_authority"] in allowed_authorities
        assert sanitized["execution_authority"] not in {"full_auto", "automated_execute", "auto_apply"}


# --- Classifications include limitations ---


def test_classifications_include_limitations() -> None:
    empty = classify_incident_from_events([])
    assert empty.limitations
    assert "INSUFFICIENT_DATA" == empty.incident_class

    event = EvidenceEvent(
        event_id="evt-sec-test-001",
        timestamp_utc="2026-06-12T12:00:00+00:00",
        endpoint_id="ep-sec-1",
        evidence_type="proxy_state",
        source_command="test",
        raw_snapshot={"wininet_proxy_enabled": True},
        normalized_fields={"wininet_proxy_enabled": True, "wininet_winhttp_mismatch": False},
        evidence_tier="T0",
        evidence_summary="fixture proxy state",
        limitations=[],
    )
    record = classify_incident_from_events([event])
    assert record.limitations
    assert record.incident_class

    case = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"
    fixture = json.loads(case.read_text(encoding="utf-8"))
    assert fixture["classification"]["limitations"]


# --- Audit tamper detection (contract) ---


def test_audit_hash_chain_detects_tampering(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "review-audit.jsonl"
    r1 = append_audit("event_received", incident_id="sec-1", path=path)
    r2 = append_audit("decision_created", incident_id="sec-1", path=path)
    ok, _ = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True
    tampered = dict(r2.model_dump())
    tampered["incident_id"] = "tampered"
    ok2, msg = verify_chain([r1.model_dump(), tampered])
    assert ok2 is False
    assert msg


# --- Secrets / gitignore contract ---


def test_env_and_platform_data_gitignored() -> None:
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert "platform_data/" in gitignore
