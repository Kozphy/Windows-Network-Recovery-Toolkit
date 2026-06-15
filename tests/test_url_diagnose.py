"""URL diagnose tests — mocked probes, CI-safe (no live LinkedIn)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.platform_core.url_diagnostics.classifier import classify_url_failure
from src.platform_core.url_diagnostics.domain_profiles import get_profile
from src.platform_core.url_diagnostics.models import (
    ClassificationPrimary,
    DnsObservation,
    HttpObservation,
    ProbeStatus,
    RedirectObservation,
    Soft404Observation,
    TcpObservation,
    TlsObservation,
)
from src.platform_core.url_diagnostics.redirect_analyzer import analyze_redirects
from src.platform_core.url_diagnostics.soft404_detector import detect_soft404
from windows_network_toolkit.cli import main
from windows_network_toolkit.diagnostics.bad_gateway.runner import run_bad_gateway_diagnose
from windows_network_toolkit.url_diagnose import diagnose_url, explain_report

LINKEDIN_URL = "https://www.linkedin.com/in/example-profile"
LINKEDIN_BODY = (
    "This page doesn't exist. Please check your URL or return to LinkedIn home. "
    "Go to your feed."
)


def _stack(**overrides: object) -> dict:
    base = {
        "dns": {"status": "OK", "resolved_ips": ["13.107.42.14"]},
        "tcp": {"status": "OK", "remote_host": "www.linkedin.com", "remote_port": 443},
        "tls": {
            "status": "OK",
            "issuer": "CN=DigiCert",
            "subject": "CN=www.linkedin.com",
            "sni": "www.linkedin.com",
        },
        "http": {
            "status": "OK",
            "status_code": 404,
            "final_url": LINKEDIN_URL,
            "redirect_chain": [LINKEDIN_URL],
            "content_type": "text/html",
            "title": "This page doesn't exist | LinkedIn",
            "body_fingerprint": "abc123",
            "body_length": 1200,
        },
        "body_text": LINKEDIN_BODY,
    }
    http_over = overrides.pop("http", None)
    redirect_over = overrides.pop("redirect", None)
    base.update(overrides)
    if isinstance(http_over, dict):
        base["http"] = {**base["http"], **http_over}
    if isinstance(redirect_over, dict):
        base["redirect"] = redirect_over
    return base


def test_dns_failure_classification() -> None:
    report = diagnose_url("https://example.com", inject={"dns": {"status": "FAIL", "error": "nxdomain"}})
    assert report["classification"]["primary"] == "DNS_FAILURE"
    assert report["classification"]["network_reachable"] is False


def test_tcp_failure_classification() -> None:
    inj = _stack(tcp={"status": "FAIL", "error": "timeout"})
    report = diagnose_url(LINKEDIN_URL, inject=inj)
    assert report["classification"]["primary"] == "TCP_CONNECT_FAILURE"


def test_tls_failure_classification() -> None:
    inj = _stack(tls={"status": "FAIL", "sni": "www.linkedin.com", "error": "cert verify failed"})
    report = diagnose_url(LINKEDIN_URL, inject=inj)
    assert report["classification"]["primary"] == "TLS_FAILURE"


def test_http_404_classification() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    cls = report["classification"]
    assert cls["primary"] == "APPLICATION_RESOURCE_NOT_FOUND"
    assert cls["network_reachable"] is True
    assert cls["resource_reachable"] is False


def test_http_403_classification() -> None:
    inj = _stack(http={"status_code": 403})
    report = diagnose_url(LINKEDIN_URL, inject=inj)
    assert report["classification"]["primary"] == "PERMISSION_OR_ACCESS_DENIED"


def test_http_410_classification() -> None:
    inj = _stack(http={"status_code": 410})
    report = diagnose_url(LINKEDIN_URL, inject=inj)
    assert report["classification"]["primary"] == "APPLICATION_RESOURCE_NOT_FOUND"


def test_http_500_classification() -> None:
    inj = _stack(http={"status_code": 502})
    report = diagnose_url(LINKEDIN_URL, inject=inj)
    assert report["classification"]["primary"] == "REMOTE_SERVER_ERROR"


def test_linkedin_soft_404_detection() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    signals = report["observations"]["http"]["soft_404_signals"]
    assert signals
    assert "LINKEDIN_SOFT_404" in report["classification"]["secondary"]
    assert report["classification"]["confidence"] >= 0.9


def test_redirect_chain_recording() -> None:
    inj = _stack(
        http={
            "final_url": "https://www.linkedin.com/in/final",
            "redirect_chain": [
                "https://lnkd.in/abc",
                "https://www.linkedin.com/redirect",
                "https://www.linkedin.com/in/final",
            ],
        },
        redirect={
            "hop_count": 2,
            "domain_changed": False,
            "original_domain": "lnkd.in",
            "final_domain": "www.linkedin.com",
            "suspicious_shortlink": True,
            "expanded_url": "https://www.linkedin.com/in/final",
        },
    )
    report = diagnose_url("https://lnkd.in/abc", domain_profile="linkedin", inject=inj)
    chain = report["observations"]["http"]["redirect_chain"]
    assert len(chain) == 3
    assert report["observations"]["redirect"]["suspicious_shortlink"] is True


def test_tracking_url_expansion() -> None:
    inj = _stack(
        http={"status_code": 404, "final_url": "https://www.linkedin.com/in/missing"},
        redirect={
            "hop_count": 1,
            "suspicious_shortlink": True,
            "expanded_url": "https://www.linkedin.com/in/missing",
            "original_domain": "lnkd.in",
            "final_domain": "www.linkedin.com",
            "domain_changed": True,
        },
    )
    report = diagnose_url("https://lnkd.in/xyz", domain_profile="linkedin", inject=inj)
    assert "REDIRECT_DOMAIN_CHANGE" in report["classification"]["secondary"] or (
        report["classification"]["primary"] == "APPLICATION_RESOURCE_NOT_FOUND"
    )


def test_json_schema_stability() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    for key in (
        "schema_version",
        "command",
        "input",
        "observations",
        "classification",
        "risk_assessment",
        "recommended_next_steps",
        "decision",
        "audit",
    ):
        assert key in report
    assert report["schema_version"] == "1.0"
    assert report["command"] == "url-diagnose"
    json.dumps(report)


def test_no_auto_fix_for_application_404() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    assert report["decision"]["safe_to_auto_fix_network"] is False
    assert "HTTP content" in report["decision"]["reason"]


def test_confidence_score_bounds() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    conf = report["classification"]["confidence"]
    assert 0.0 <= conf <= 1.0


def test_linkedin_404_recommendations() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    steps = " ".join(report["recommended_next_steps"]).lower()
    assert "linkedin.com/feed" in steps or "logged in" in steps
    assert "url" in steps


def test_existing_proxy_diagnostics_not_broken() -> None:
    inj = {
        "dns": {"ok": True, "addresses": ["93.184.216.34"]},
        "tcp": {"ok": True, "host": "example.com", "port": 443},
        "http_system_proxy": {"ok": False, "status_code": 502, "via_system_proxy": True},
        "http_direct": {"ok": True, "status_code": 200, "via_system_proxy": False},
        "wininet_proxy": {"proxy_enable": 1, "proxy_server": "127.0.0.1:8888"},
        "winhttp_proxy": {"ok": True},
        "local_proxy_process": {"detected": True, "port": 8888},
    }
    bg = run_bad_gateway_diagnose("https://example.com", inject=inj, run=MagicMock())
    assert bg["classification"] == "LOCAL_LOOPBACK_PROXY"
    linkedin = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    assert linkedin["classification"]["primary"] == "APPLICATION_RESOURCE_NOT_FOUND"
    assert linkedin["classification"]["primary"] != "DEAD_PROXY_CONFIG"


def test_linkedin_404_not_classified_as_proxy_drift() -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    not_evidence = report["risk_assessment"]["not_evidence_of"]
    assert "WinINET proxy drift" in not_evidence
    assert "DNS outage" in not_evidence


def test_redirect_loop_classification() -> None:
    inj = _stack(
        http={"status_code": 200, "redirect_chain": ["https://a.com", "https://b.com", "https://a.com"]},
        redirect={"loop_detected": True, "hop_count": 5},
    )
    report = diagnose_url("https://a.com", inject=inj)
    assert report["classification"]["primary"] == "REDIRECT_LOOP_OR_CHAIN_FAILURE"


def test_soft_404_status_200() -> None:
    inj = _stack(http={"status_code": 200})
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=inj)
    assert report["classification"]["primary"] in {
        "SOFT_404_OR_CONTENT_NOT_FOUND",
        "APPLICATION_RESOURCE_NOT_FOUND",
    }


def test_cli_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "url-diagnose",
            "--url",
            LINKEDIN_URL,
            "--domain-profile",
            "linkedin",
            "--fixture",
            "tests/fixtures/url_diagnostics/linkedin_404.json",
            "--json",
        ],
        prog="windows_network_toolkit",
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["classification"]["primary"] == "APPLICATION_RESOURCE_NOT_FOUND"


def test_explain_output(capsys: pytest.CaptureFixture[str]) -> None:
    report = diagnose_url(LINKEDIN_URL, domain_profile="linkedin", inject=_stack())
    text = explain_report(report)
    assert "APPLICATION_RESOURCE_NOT_FOUND" in text
    assert "Safe to auto-fix" in text


def test_unit_classifier_dns() -> None:
    profile = get_profile("generic")
    cls = classify_url_failure(
        dns=DnsObservation(status=ProbeStatus.FAIL),
        tcp=TcpObservation(status=ProbeStatus.OK),
        tls=TlsObservation(status=ProbeStatus.OK),
        http=HttpObservation(status=ProbeStatus.OK, status_code=200),
        redirect=RedirectObservation(),
        soft404=Soft404Observation(),
        profile=profile,
    )
    assert cls.primary == ClassificationPrimary.DNS_FAILURE


def test_soft404_detector_unit() -> None:
    http = HttpObservation(
        status=ProbeStatus.OK,
        status_code=404,
        title="This page doesn't exist | LinkedIn",
    )
    soft = detect_soft404(
        LINKEDIN_URL,
        http,
        profile=get_profile("linkedin"),
        body_text=LINKEDIN_BODY,
    )
    assert soft.detected
    assert http.soft_404_signals


def test_redirect_analyzer_domain_change() -> None:
    http = HttpObservation(
        status=ProbeStatus.OK,
        status_code=200,
        final_url="https://www.linkedin.com/in/x",
        redirect_chain=["https://lnkd.in/x", "https://www.linkedin.com/in/x"],
    )
    obs = analyze_redirects("https://lnkd.in/x", http, profile=get_profile("linkedin"))
    assert obs.domain_changed is True
    assert obs.suspicious_shortlink is True
