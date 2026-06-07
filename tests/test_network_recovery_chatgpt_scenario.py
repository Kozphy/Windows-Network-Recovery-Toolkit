"""Tests for CASE_CHATGPT_APP_FIREWALL_FILTERING_INTERACTION scenario."""

from __future__ import annotations

import json
from pathlib import Path

from src.network_recovery.audit import append_network_recovery_audit
from src.network_recovery.diagnosis_text import format_diagnosis_report
from src.network_recovery.engine import run_scenario_diagnosis
from src.network_recovery.models import (
    DESKTOP_APP_PATH_DEGRADED_EVENT,
    SCENARIO_CHATGPT_APP_FIREWALL,
    SignalBundle,
)
from src.network_recovery.remediation_catalog import remediation_previews_for_chatgpt_scenario
from src.network_recovery.scenarios.chatgpt_app_firewall import analyze_chatgpt_app_firewall


def _degraded_browser_healthy_signals(**overrides: object) -> SignalBundle:
    base = dict(
        browser_https_ok=True,
        chatgpt_https_ok=False,
        openai_https_ok=False,
        curl_https_ok=True,
        dns_ok=True,
        wininet_proxy_enable=0,
        wininet_proxy_server=None,
        wininet_auto_config_url=None,
        winhttp_direct_access=True,
        winhttp_loopback_hint=False,
        firewall_profiles_snapshot={"profiles": {"domain": "State ON"}},
        localhost_listener_ports=(),
        chatgpt_process_detected=True,
        electron_process_detected=True,
        vpn_adapter_hint=False,
        collector_notes=(),
    )
    base.update(overrides)
    return SignalBundle(**base)  # type: ignore[arg-type]


def test_browser_healthy_app_degraded_event() -> None:
    analysis = analyze_chatgpt_app_firewall(_degraded_browser_healthy_signals())
    assert DESKTOP_APP_PATH_DEGRADED_EVENT in analysis["events"]


def test_proxy_drift_raises_proxy_hypothesis() -> None:
    signals = _degraded_browser_healthy_signals(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:54321",
        localhost_listener_ports=(54321,),
    )
    analysis = analyze_chatgpt_app_firewall(signals)
    hypos = [h.hypothesis_id for h in analysis["hypotheses"]]  # type: ignore[index]
    assert "proxy_or_localhost_proxy_interaction" in hypos
    proxy_row = next(h for h in analysis["hypotheses"] if h.hypothesis_id == "proxy_or_localhost_proxy_interaction")  # type: ignore[index]
    assert proxy_row.confidence in {"medium", "high"}


def test_firewall_recovery_evidence_not_malware_claim() -> None:
    signals = _degraded_browser_healthy_signals()
    analysis = analyze_chatgpt_app_firewall(signals, recovery_firewall_reset_helped=True)
    assert analysis["verification_status"] == "supported_by_recovery_evidence"
    text = format_diagnosis_report(
        signals=signals,
        events=list(analysis["events"]),  # type: ignore[arg-type]
        hypotheses=analysis["hypotheses"],  # type: ignore[arg-type]
        verification_status="supported_by_recovery_evidence",
        primary_hypothesis_id="firewall_filtering_interaction",
        recovery_firewall_reset_helped=True,
    )
    assert "supported by recovery evidence" in text.lower()
    assert "not proof of malicious" in text.lower() or "not proof of malicious activity" in text.lower()
    assert "malware" not in text.lower() or "do not state malware" in text.lower()


def test_no_overclaiming_causality_in_limitations() -> None:
    result = run_scenario_diagnosis(
        SCENARIO_CHATGPT_APP_FIREWALL,
        signals=_degraded_browser_healthy_signals(),
        collect_live=False,
    )
    blob = "\n".join(result.limitations).lower()
    assert "registry-writer" in blob
    assert "do not" in blob and "malware" in blob
    summary = result.human_summary.lower()
    assert "caused" not in summary
    assert "do not state malware" in summary


def test_dry_run_default_blocks_execution() -> None:
    previews = remediation_previews_for_chatgpt_scenario(dry_run=True)
    assert all(a.dry_run_only for a in previews if a.risk == "low")
    blocked = [a for a in previews if a.policy_decision == "BLOCK"]
    assert blocked
    assert any(a.action_id == "disable_firewall" for a in blocked)


def test_high_risk_actions_blocked() -> None:
    previews = remediation_previews_for_chatgpt_scenario(dry_run=False)
    for action_id in ("disable_firewall", "kill_unknown_processes", "delete_certificates", "arbitrary_shell"):
        row = next(a for a in previews if a.action_id == action_id)
        assert row.policy_decision == "BLOCK"


def test_audit_jsonl_fields(tmp_path: Path) -> None:
    result = run_scenario_diagnosis(
        SCENARIO_CHATGPT_APP_FIREWALL,
        signals=_degraded_browser_healthy_signals(),
        recovery_firewall_reset_helped=True,
        collect_live=False,
    )
    path = append_network_recovery_audit(tmp_path, result)
    row = json.loads(path.read_text(encoding="utf-8").strip().splitlines()[-1])
    for key in (
        "timestamp",
        "run_id",
        "signals",
        "events",
        "hypotheses",
        "evidence_for",
        "evidence_against",
        "confidence_boundary",
        "recommended_actions",
        "policy_decision",
        "remediation_executed",
        "post_check_results",
        "limitations",
        "verification_status",
    ):
        assert key in row
