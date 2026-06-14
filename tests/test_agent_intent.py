"""Intent classification tests."""

from __future__ import annotations

from src.platform_core.agent.intent import AgentIntent, classify_intent


def test_proxy_message_maps_to_diagnose_proxy() -> None:
    assert classify_intent("browser cannot connect ERR_PROXY_CONNECTION_FAILED") == AgentIntent.DIAGNOSE_PROXY
    assert classify_intent("proxy broken on localhost") == AgentIntent.DIAGNOSE_PROXY


def test_tls_message_maps_to_check_tls() -> None:
    assert classify_intent("check certificate chain for MITM") == AgentIntent.CHECK_TLS
    assert classify_intent("TLS root CA mismatch") == AgentIntent.CHECK_TLS


def test_website_risk_intent() -> None:
    assert classify_intent("is this URL risky phishing site") == AgentIntent.SCORE_WEBSITE_RISK


def test_remediation_intent() -> None:
    assert classify_intent("please fix it disable proxy") == AgentIntent.PREVIEW_REMEDIATION


def test_audit_verify_intent() -> None:
    assert classify_intent("verify audit hash chain") == AgentIntent.VERIFY_AUDIT_CHAIN


def test_unknown_intent() -> None:
    assert classify_intent("hello world random question") == AgentIntent.UNKNOWN
