from __future__ import annotations

from agent.schemas import DiagnosticEvidence
from agent.verifier import verify_after_repair


def test_verifier_improvement_passes() -> None:
    before = DiagnosticEvidence.from_dict(
        {
            "ping_ok": True,
            "dns_ok": False,
            "tcp_443_ok": False,
            "https_ok": False,
            "winhttp_proxy_summary": "",
            "user_proxy_enabled": False,
            "user_proxy_server": None,
            "tls_cert_issue_detected": False,
            "firewall_blocking_suspected": False,
            "time_wait_count": 0,
            "established_count": 0,
            "recent_processes": [],
            "notes": "",
        },
    )
    after = DiagnosticEvidence.from_dict(
        {
            "ping_ok": True,
            "dns_ok": True,
            "tcp_443_ok": True,
            "https_ok": True,
            "winhttp_proxy_summary": "",
            "user_proxy_enabled": False,
            "user_proxy_server": None,
            "tls_cert_issue_detected": False,
            "firewall_blocking_suspected": False,
            "time_wait_count": 0,
            "established_count": 0,
            "recent_processes": [],
            "notes": "",
        },
    )

    result = verify_after_repair(before, lambda: after)
    assert result.passed is True


def test_verifier_regression_fails() -> None:
    before = DiagnosticEvidence.from_dict(
        {
            "ping_ok": True,
            "dns_ok": True,
            "tcp_443_ok": True,
            "https_ok": True,
            "winhttp_proxy_summary": "",
            "user_proxy_enabled": False,
            "user_proxy_server": None,
            "tls_cert_issue_detected": False,
            "firewall_blocking_suspected": False,
            "time_wait_count": 0,
            "established_count": 0,
            "recent_processes": [],
            "notes": "",
        },
    )
    after = DiagnosticEvidence.from_dict(
        {
            "ping_ok": True,
            "dns_ok": True,
            "tcp_443_ok": True,
            "https_ok": False,
            "winhttp_proxy_summary": "",
            "user_proxy_enabled": False,
            "user_proxy_server": None,
            "tls_cert_issue_detected": False,
            "firewall_blocking_suspected": False,
            "time_wait_count": 0,
            "established_count": 0,
            "recent_processes": [],
            "notes": "",
        },
    )
    result = verify_after_repair(before, lambda: after)
    assert result.passed is False
