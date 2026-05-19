"""Tests for proxy_reasoning: entity, scenarios, policy, replay, conservative copy."""

from __future__ import annotations

import json
from pathlib import Path

from proxy_reasoning import (
    build_proxy_entity,
    run_proxy_reasoning,
    signals_from_dict,
    to_audit_record,
)
from proxy_reasoning.audit import replay_proxy_reasoning_record as replay_fn
from proxy_reasoning.constants import (
    CASE_BROWSER_PROXY_PATH_ISSUE,
    CASE_LOCALHOST_PROXY_LISTENER,
    CASE_WININET_PROXY_DRIFT,
)
from proxy_reasoning.diagnosis_text import render_proxy_diagnosis
from proxy_reasoning.policy import evaluate_proxy_policy
from proxy_reasoning.scenarios import rank_hypotheses


def test_proxy_entity_serialization_roundtrip() -> None:
    payload = {
        "wininet": {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:8080"},
        "is_loopback_proxy": True,
        "listener": {"process_name": "node.exe", "pid": 1234, "listening": True},
        "dns_ok": True,
        "ping_ok": True,
    }
    entity = build_proxy_entity(payload)
    blob = entity.model_dump(mode="json")
    restored = build_proxy_entity({**payload, "parsed_proxy": blob.get("network_attributes") or {}})
    assert restored.configuration_attributes.proxy_enable is True
    assert restored.network_attributes.is_loopback is True


def test_localhost_node_not_malicious_classification() -> None:
    entity = build_proxy_entity(
        {
            "wininet": {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:7890"},
            "is_loopback_proxy": True,
            "listener": {"process_name": "node.exe", "path": r"C:\Program Files\nodejs\node.exe"},
        },
    )
    assert entity.trust_risk_attributes.classification == "KNOWN_DEV_PROXY"
    assert entity.trust_risk_attributes.risk_level == "low"
    assert "malware" not in " ".join(entity.trust_risk_attributes.rationale).lower()


def test_localhost_without_cert_not_mitm() -> None:
    entity = build_proxy_entity(
        {
            "proxy_enable": 1,
            "is_loopback_proxy": True,
            "listener": {"process_name": "unknown.exe", "path": r"C:\Users\public\foo.exe"},
        },
    )
    assert entity.trust_risk_attributes.classification == "UNKNOWN_LOCAL_PROXY"
    assert entity.trust_risk_attributes.classification != "POSSIBLE_MITM_RISK"


def test_wininet_winhttp_divergence_scenario() -> None:
    signals = signals_from_dict(
        {
            "wininet_proxy_enabled": True,
            "wininet_winhttp_divergent": True,
            "proxy_server_localhost": True,
        },
    )
    hyps = rank_hypotheses(signals)
    assert any(h.case_id == CASE_WININET_PROXY_DRIFT for h in hyps)


def test_browser_proxy_path_scenario() -> None:
    signals = signals_from_dict(
        {
            "ping_ok": True,
            "dns_ok": True,
            "browser_https_failed": True,
            "proxy_bypass_succeeded": True,
        },
    )
    hyps = rank_hypotheses(signals)
    assert hyps[0].case_id == CASE_BROWSER_PROXY_PATH_ISSUE


def test_process_attribution_limitation_present() -> None:
    entity = build_proxy_entity({"listener": {"process_name": "node.exe", "listening": True}})
    lims = entity.process_attribution_attributes.attribution_limitations
    assert any("listener correlation" in x.lower() for x in lims)


def test_policy_block_kill() -> None:
    entity = build_proxy_entity({"proxy_enable": 1})
    pol = evaluate_proxy_policy(requested_action="kill_process", entity=entity, verification_results=[])
    assert pol.decision == "BLOCK"


def test_policy_allow_read_only() -> None:
    entity = build_proxy_entity({})
    pol = evaluate_proxy_policy(requested_action="diagnose", entity=entity, verification_results=[])
    assert pol.decision == "ALLOW"


def test_policy_preview_unverified_mutation() -> None:
    entity = build_proxy_entity({"proxy_enable": 1})
    pol = evaluate_proxy_policy(requested_action="restore_proxy", entity=entity, verification_results=[])
    assert pol.decision == "PREVIEW"


def test_firewall_reset_not_proven_root_cause() -> None:
    run = run_proxy_reasoning(
        payload={
            "browser_works": True,
            "electron_app_failed": True,
            "firewall_reset_helped": True,
        },
    )
    fw = next((v for v in run.verification_results if v.check_id == "firewall_reset_outcome"), None)
    assert fw is not None
    assert fw.status == "INCONCLUSIVE"
    assert "before/after" in " ".join(fw.limitations).lower()


def test_replay_without_reprobe(tmp_path: Path) -> None:
    run1 = run_proxy_reasoning(
        payload={
            "ping_ok": True,
            "dns_ok": True,
            "browser_https_failed": True,
            "proxy_bypass_succeeded": True,
            "wininet_proxy_enabled": True,
        },
        requested_action="diagnose",
    )
    record = to_audit_record(run1)
    run2 = replay_fn(record)
    assert run2.accepted_hypothesis == run1.accepted_hypothesis
    assert run2.policy_decision.decision == run1.policy_decision.decision


def test_user_summary_never_claims_malware() -> None:
    run = run_proxy_reasoning(
        payload={
            "wininet": {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:8080"},
            "listener": {"process_name": "node.exe"},
            "is_loopback_proxy": True,
        },
    )
    summary = render_proxy_diagnosis(run)
    observed_inferred = json.dumps(summary.get("observed", []) + summary.get("inferred", [])).lower()
    assert "malware" not in observed_inferred
    assert "not proven" in json.dumps(summary.get("not_proven", [])).lower()


def test_localhost_listener_scenario() -> None:
    signals = signals_from_dict(
        {"proxy_server_localhost": True, "listener_on_proxy_port": True, "listener_process_name": "node.exe"},
    )
    hyps = rank_hypotheses(signals)
    assert any(h.case_id == CASE_LOCALHOST_PROXY_LISTENER for h in hyps)


def test_evidence_boundary_caps_confidence_without_proof() -> None:
    run = run_proxy_reasoning(payload={"ping_ok": True, "dns_ok": True, "browser_https_failed": True})
    assert run.entity.evidence_attributes.verification_status in {"UNVERIFIED", "INCONCLUSIVE", "REJECTED", "CONFIRMED"}
    assert "not_proof_tier" in run.confidence_boundary.caps or run.confidence_boundary.rank != "high"
