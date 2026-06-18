"""Endpoint Network Evidence & Risk Toolkit engine tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.attribution.classifier import classify_listener
from src.platform_core.attribution.models import (
    ListenerClassification,
    ProcessAttribution,
    ProxyStateSnapshot,
)
from src.platform_core.attribution.writer_engine import run_proxy_writer_attribution
from src.platform_core.evidence_report import generate_evidence_report, merge_evidence_timeline
from src.platform_core.tls import run_tls_proof
from src.platform_core.website_risk import run_website_risk
from src.platform_core.website_risk.heuristics import score_local_heuristics
from windows_network_toolkit.diagnostics.evidence import run_evidence_assessment

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "enert"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_no_proxy_fixture():
    data = _load("no_proxy.json")
    result = run_proxy_writer_attribution(inject=data["writer_attribution"])
    assert result.classification == "NO_PROXY"
    assert result.registry_writer_confirmed is False
    assert result.confidence_score < 0.3


def test_known_dev_proxy_fixture():
    data = _load("known_dev_proxy.json")
    result = run_proxy_writer_attribution(inject=data["writer_attribution"])
    assert result.classification == "KNOWN_DEV_PROXY"
    assert result.correlated_process.process_name == "node.exe"


def test_unknown_localhost_proxy_fixture():
    data = _load("unknown_localhost_proxy.json")
    result = run_proxy_writer_attribution(inject=data["writer_attribution"])
    assert result.classification == "UNKNOWN_LOCAL_PROXY"
    assert result.registry_writer_confirmed is False


def test_registry_writer_observed_fixture():
    data = _load("registry_writer_observed.json")
    result = run_proxy_writer_attribution(
        inject=data["writer_attribution"],
        inject_sysmon=data["sysmon_events"],
    )
    assert result.registry_writer_confirmed is True
    assert result.writer_evidence[0].process_name == "mitmproxy.exe"
    assert result.attribution_confidence.value == "very_high"


def test_tls_certificate_mismatch_fixture():
    data = _load("tls_cert_mismatch.json")
    result = run_tls_proof("https://example.com", inject=data["tls_proof"])
    assert result.certificate_mismatch is True
    assert "issuer" in result.mismatch_fields
    assert result.mitm_risk_level.value == "HIGH"


def test_suspicious_root_ca_fixture():
    data = _load("suspicious_root_ca.json")
    result = run_tls_proof(
        "https://example.com",
        inject=data["tls_proof"],
        inject_roots=data["root_store"],
    )
    assert result.mitm_risk_level.value == "MEDIUM"
    assert len(result.suspicious_roots) == 1


def test_suspicious_domain_fixture():
    data = _load("suspicious_domain.json")
    result = run_website_risk(data["website_risk"]["url"], inject=data["website_risk"])
    assert result.risk_level.value == "HIGH"
    assert result.score >= 0.65


def test_redirect_phishing_fixture():
    data = _load("redirect_phishing.json")
    result = run_website_risk(data["website_risk"]["url"], inject=data["website_risk"])
    assert result.risk_level.value == "HIGH"
    signals = {e.signal for e in result.evidence}
    assert "excessive_redirects" in signals


def test_heuristic_punycode_scoring():
    score, evidence, level = score_local_heuristics(
        "https://xn--pypal-4ve.com",
        https_ok=True,
        final_url="https://xn--pypal-4ve.com",
        redirect_chain=["https://xn--pypal-4ve.com"],
        html_excerpt="<input name='password'>",
    )
    assert score > 0.5
    assert level.value in {"MEDIUM", "HIGH"}
    assert any(e.signal == "punycode_homograph" for e in evidence)


def test_possible_mitm_risk_external_proxy():
    proxy = ProxyStateSnapshot(wininet_proxy_enable=1, wininet_proxy_server="203.0.113.50:8080")
    classification, _, _ = classify_listener(proxy, ProcessAttribution(), listener_detected=False)
    assert classification == ListenerClassification.POSSIBLE_MITM_RISK


def test_merge_evidence_timeline():
    data = _load("registry_writer_observed.json")
    timeline = merge_evidence_timeline(
        incident_id="inc-test",
        proxy_writer=data["writer_attribution"],
        tls_proof=_load("tls_cert_mismatch.json")["tls_proof"],
        website_risk=_load("suspicious_domain.json")["website_risk"],
    )
    types = {e["event_type"] for e in timeline}
    assert "proxy_registry_observed" in types
    assert "registry_write_observed" in types
    assert "tls_proof" in types
    assert "website_risk_assessed" in types


def test_evidence_report_formats():
    tls = _load("tls_cert_mismatch.json")["tls_proof"]
    web = _load("suspicious_domain.json")["website_risk"]
    writer = _load("no_proxy.json")["writer_attribution"]
    proof = {
        "proof_id": "proof-test",
        "timestamp_utc": "2026-06-04T12:00:00Z",
        "target_url": "https://example.com",
        "observations": [],
        "outcome": "UNKNOWN_INCONCLUSIVE",
        "outcome_rationale": "fixture",
        "confidence_level": "medium",
        "limitations": [],
        "is_proof": False,
    }
    package = run_evidence_assessment(
        "https://example.com",
        inject_writer=writer,
        inject_proof=proof,
        inject_tls=tls,
        inject_website=web,
        include_tls=True,
        include_website_risk=True,
    )
    assert "timeline" in package
    assert package["confidence_model"]
    md = generate_evidence_report(package, fmt="markdown")
    assert "Endpoint Network Evidence" in md
    assert "Disclaimer" in md or "Disclaimer" in md
    html = generate_evidence_report(package, fmt="html")
    assert "<table" in html
    jsonl = generate_evidence_report(package, fmt="jsonl")
    assert jsonl.count("\n") >= 2
