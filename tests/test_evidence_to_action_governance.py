"""Evidence-to-Action Governance Model — envelope, language, and safety contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform_core.governance.evidence_to_action import (
    GOVERNANCE_MODEL,
    attach_governance_envelope,
    build_governance_envelope,
    causal_language_allowed,
    narrative_passes_governance_language,
)
from src.platform_core.principles.models import RiskDecision
from src.platform_core.principles.rules import check_classification_not_accusation
from src.platform_core.principles.validator import validate_principles
from src.platform_core.risk import assess_risk, load_fixture
from windows_network_toolkit.diagnostics.proxy import run_proxy_status
from windows_network_toolkit.proxy_remediation import run_proxy_disable
from windows_network_toolkit.safety import BLOCKED_ACTIONS

REPO = Path(__file__).resolve().parents[1]
CASE_1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"
DEAD_PROXY = REPO / "tests" / "fixtures" / "enert" / "dead_proxy_59081.json"


@pytest.mark.parametrize(
    "claim_strength",
    ["observation", "correlation", "proof"],
)
def test_low_evidence_tiers_disallow_causal_language(claim_strength: str) -> None:
    assert not causal_language_allowed(claim_strength=claim_strength)
    assert not narrative_passes_governance_language(
        "This was caused by malware on the endpoint.",
        claim_strength=claim_strength,
    )


def test_attribution_tier_allows_bounded_causal_language() -> None:
    assert causal_language_allowed(claim_strength="attribution")
    assert narrative_passes_governance_language(
        "Writer telemetry supports attribution to process X.",
        claim_strength="attribution",
    )


def test_suspicious_proxy_does_not_imply_malware_proof() -> None:
    envelope = build_governance_envelope(primary_classification="SUSPICIOUS_PROXY")
    assert envelope["classification_is_accusation"] is False
    check = check_classification_not_accusation(
        risk=RiskDecision(primary_classification="SUSPICIOUS_PROXY"),
        narrative_text="This proved malware on the host.",
    )
    assert not check.passed
    assert not narrative_passes_governance_language(
        "proved malware on the proxy path",
        claim_strength="correlation",
        primary_classification="SUSPICIOUS_PROXY",
    )


def test_possible_mitm_risk_does_not_imply_confirmed_mitm() -> None:
    envelope = build_governance_envelope(primary_classification="POSSIBLE_MITM_RISK")
    assert envelope["classification_is_accusation"] is False
    assert "POSSIBLE_MITM_RISK" in envelope["limitations"][-1]
    assert not narrative_passes_governance_language(
        "This confirms MITM interception.",
        claim_strength="correlation",
        primary_classification="POSSIBLE_MITM_RISK",
    )


def test_governance_envelope_confidence_type_ordinal() -> None:
    envelope = build_governance_envelope()
    assert envelope["governance_model"] == GOVERNANCE_MODEL
    assert envelope["confidence_type"] == "ordinal_not_probability"


def test_risk_assess_includes_governance_envelope() -> None:
    fixture = load_fixture(CASE_1)
    payload = assess_risk(fixture)
    gov = payload["governance"]
    assert gov["governance_model"] == GOVERNANCE_MODEL
    assert gov["confidence_type"] == "ordinal_not_probability"
    assert gov["classification_is_accusation"] is False
    assert gov["execution_authority"] in ("preview_only", "human_required", "blocked")


def test_proxy_status_fixture_includes_governance() -> None:
    data = json.loads(DEAD_PROXY.read_text(encoding="utf-8"))
    payload = run_proxy_status(inject=data)
    assert "governance" in payload
    assert payload["governance"]["execution_authority"] == "preview_only"


def test_proxy_disable_dry_run_preview_only_authority() -> None:
    with patch("windows_network_toolkit.proxy_remediation.platform.system", return_value="Windows"), patch(
        "windows_network_toolkit.proxy_remediation.collect_proxy_state_model"
    ), patch(
        "windows_network_toolkit.proxy_remediation.read_proxy_registry"
    ), patch(
        "windows_network_toolkit.proxy_remediation.decide",
        return_value={
            "policy_decision": {"outcome": "PREVIEW_ONLY", "dry_run": True},
            "classification": {"primary_classification": "DEAD_PROXY_CONFIG", "limitations": []},
            "proof": {"hypothesis": "dead proxy"},
        },
    ), patch(
        "windows_network_toolkit.proxy_remediation.build_user_proxy_disable_mutations",
        return_value=([], ["Set ProxyEnable=0"]),
    ), patch(
        "windows_network_toolkit.proxy_remediation.parse_proxy_server",
        return_value=type("P", (), {"is_missing": True})(),
    ), patch(
        "windows_network_toolkit.proxy_remediation.registry_with_parsed",
        return_value={},
    ), patch(
        "windows_network_toolkit.proxy_remediation.append_audit_dict",
        return_value=(True, None),
    ):
        payload = run_proxy_disable(dry_run=True, confirm="")
    assert payload["dry_run"] is True
    assert payload["governance"]["execution_authority"] == "preview_only"
    assert payload["governance"]["causal_language_allowed"] is False


def test_proxy_disable_without_confirmation_stays_human_required() -> None:
    with patch("windows_network_toolkit.proxy_remediation.platform.system", return_value="Windows"), patch(
        "windows_network_toolkit.proxy_remediation.collect_proxy_state_model"
    ), patch(
        "windows_network_toolkit.proxy_remediation.read_proxy_registry"
    ), patch(
        "windows_network_toolkit.proxy_remediation.decide",
        return_value={
            "policy_decision": {"outcome": "ALLOW"},
            "classification": {"primary_classification": "DEAD_PROXY_CONFIG", "limitations": []},
            "proof": {"hypothesis": "dead proxy"},
        },
    ), patch(
        "windows_network_toolkit.proxy_remediation.build_user_proxy_disable_mutations",
        return_value=([], []),
    ), patch(
        "windows_network_toolkit.proxy_remediation.parse_proxy_server",
        return_value=type("P", (), {"is_missing": True})(),
    ), patch(
        "windows_network_toolkit.proxy_remediation.registry_with_parsed",
        return_value={},
    ), patch(
        "windows_network_toolkit.proxy_remediation.append_audit_dict",
        return_value=(True, None),
    ):
        payload = run_proxy_disable(dry_run=False, confirm="")
    assert payload["action_allowed"] is False
    assert payload["governance"]["execution_authority"] == "human_required"


def test_autonomous_execution_language_fails_principles() -> None:
    data = json.loads(CASE_1.read_text(encoding="utf-8"))
    data["executive_summary"] = "It is safe to execute automatically without review."
    result = validate_principles(data)
    check_ids = {c.principle_id for c in result.checks if not c.passed}
    assert "recommendation_not_execution" in check_ids


def test_attach_governance_backward_compatible() -> None:
    original = {"classification": "DEAD_PROXY_CONFIG", "dry_run": True}
    enriched = attach_governance_envelope(original)
    assert enriched["classification"] == "DEAD_PROXY_CONFIG"
    assert "governance" in enriched


def test_blocked_actions_remain_forbidden() -> None:
    assert "KILL_PROXY_PROCESS" in BLOCKED_ACTIONS
    assert "FIREWALL_RESET" in BLOCKED_ACTIONS
    assert "ADAPTER_DISABLE" in BLOCKED_ACTIONS


def test_analytics_summary_includes_governance() -> None:
    from src.platform_core.analytics import build_analytics_summary

    sample = REPO / "tests" / "fixtures" / "analytics" / "audit_sample"
    payload = build_analytics_summary(sample)
    assert payload["governance"]["governance_model"] == GOVERNANCE_MODEL
    assert payload["governance"]["confidence_type"] == "ordinal_not_probability"
