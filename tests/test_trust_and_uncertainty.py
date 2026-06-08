"""Trust layer, failure-mode tagging, degraded cap on ALLOW, adversarial hints, numeric risk."""

from __future__ import annotations

import pytest

from src.core.models import LiveNetworkSnapshot, ProxyRegistrySnapshot
from src.decision_engine.adversarial_hints import adversarial_hints
from src.decision_engine.hypothesis_decision import PolicyDecision, build_hypothesis_decisions
from src.decision_engine.risk_numeric import hypothesis_impact, hypothesis_risk_score
from src.decision_engine.trust_layer import assess_trust
from src.diagnostics.features import FeatureVector
from src.proof.contracts import ProofResult, ProofStatus
from src.proxy_guard.parser import parse_proxy_server


def _snap(
    fv: FeatureVector,
    *,
    proxy_enable: int = 0,
    proxy_server: str | None = None,
    listen_ports: tuple[int, ...] = (),
    permission_notes: tuple[str, ...] = (),
) -> LiveNetworkSnapshot:
    reg = ProxyRegistrySnapshot(
        proxy_enable=proxy_enable,
        proxy_server=proxy_server,
        auto_config_url=None,
        auto_detect=0,
    )
    parsed = parse_proxy_server(reg.proxy_server)
    return LiveNetworkSnapshot(
        generated_at_utc="2026-05-05T12:00:00Z",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=(),
        localhost_listen_ports=listen_ports,
        interesting_processes=(),
        tcp_top_ports=(),
        commands_executed=(),
        permission_notes=permission_notes,
    )


def test_trust_detects_listen_mismatch_conflict() -> None:
    fv = FeatureVector(
        ping_ip_ok=True,
        ping_domain_ok=True,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
        proxy_enabled=True,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=True,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    snap = _snap(
        fv,
        proxy_enable=1,
        proxy_server="127.0.0.1:7777",
        listen_ports=(9999,),
    )
    ta = assess_trust(snap, proof_result=None, proofs_requested=False)
    codes = [c.code for c in ta.conflicts]
    assert "HKCU_PROXY_PORT_NOT_LISTENING" in codes


def test_failure_mode_partial_transport_patterns() -> None:
    fv = FeatureVector(
        ping_ip_ok=True,
        ping_domain_ok=False,
        nslookup_ok=True,
        tcp_443_ok=False,
        browser_http_ok=False,
        proxy_enabled=False,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=True,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    snap = _snap(fv)
    ta = assess_trust(snap, proof_result=None, proofs_requested=False)
    assert "FN_PARTIAL_TRANSPORT_ICMP_DNS_OK_TCP_FAIL" in ta.failure_modes


def test_failure_mode_fp_icmp_filtered() -> None:
    fv = FeatureVector(
        ping_ip_ok=False,
        ping_domain_ok=False,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
        proxy_enabled=False,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=True,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    ta = assess_trust(_snap(fv), proof_result=None, proofs_requested=False)
    assert "FP_HEALTHY_SURFACE_ICMP_FILTERED_TRANSPORT_OK" in ta.failure_modes


def test_dual_conflict_sets_degraded_mode() -> None:
    """Gateway vs ping conflict + HKCU/listen mismatch → degraded_mode for decision cap."""
    fv = FeatureVector(
        ping_ip_ok=True,
        ping_domain_ok=True,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
        proxy_enabled=False,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=False,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    snap = _snap(
        fv,
        proxy_enable=1,
        proxy_server="127.0.0.1:7700",
        listen_ports=(1111,),  # 7700 not listed
    )
    ta = assess_trust(snap, proof_result=None, proofs_requested=False)
    assert len(ta.conflicts) >= 2
    assert ta.degraded_mode is True
    assert "MULTI_SIGNAL_CONFLICT" in ta.degraded_reasons


def test_degraded_mode_caps_allow_to_preview() -> None:
    proof = ProofResult(
        proof_id="localhost_proxy_https_contrast",
        status=ProofStatus.CONFIRMED,
        hypothesis="fixture",
        summary="CONFIRMED",
    )
    fv = FeatureVector(
        ping_ip_ok=True,
        ping_domain_ok=True,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
        proxy_enabled=False,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=False,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    snap = _snap(
        fv,
        proxy_enable=1,
        proxy_server="127.0.0.1:7700",
        listen_ports=(1111,),
    )
    ta = assess_trust(snap, proof_result=proof, proofs_requested=False)
    rows = build_hypothesis_decisions(
        ranked=[("unexpected_user_proxy", 0.9, ("fixture",))],
        localhost_proxy_proof=proof,
        proofs_enabled=True,
        trust_assessment=ta,
    )
    assert rows[0]["decision"] == PolicyDecision.PREVIEW.value
    assert "capped to PREVIEW" in "\n".join(rows[0]["why"])


def test_adversarial_hints_credential_embedding() -> None:
    fv = FeatureVector(
        ping_ip_ok=True,
        ping_domain_ok=True,
        nslookup_ok=True,
        tcp_443_ok=True,
        browser_http_ok=True,
        proxy_enabled=True,
        winhttp_proxy_enabled=False,
        dns_servers_detected=2,
        adapter_connected=True,
        gateway_reachable=True,
        tls_cert_issue_detected=False,
        firewall_path_suspected=False,
        time_wait_count=10,
        established_count=10,
    )
    reg = ProxyRegistrySnapshot(1, "http://user:pass@127.0.0.1:8080", None, 0)
    parsed = parse_proxy_server(reg.proxy_server)
    snap = LiveNetworkSnapshot(
        generated_at_utc="2026-05-05T12:00:00Z",
        feature_vector=fv,
        proxy_registry=reg,
        parsed_proxy=parsed,
        port_owners=(),
        localhost_listen_ports=(),
        interesting_processes=(),
        tcp_top_ports=(),
        commands_executed=(),
        permission_notes=(),
    )
    assert "ADV_PROXY_URL_CREDENTIAL_PATTERN" in adversarial_hints(snap)


def test_risk_is_confidence_times_impact() -> None:
    assert hypothesis_risk_score(0.5, "dns_resolution_issue") == pytest.approx(
        0.5 * hypothesis_impact("dns_resolution_issue"),
        abs=1e-4,
    )


def test_proof_engine_exception_marks_degraded_with_none_result() -> None:
    snap = _snap(
        FeatureVector(
            ping_ip_ok=True,
            ping_domain_ok=True,
            nslookup_ok=True,
            tcp_443_ok=True,
            browser_http_ok=True,
            proxy_enabled=False,
            winhttp_proxy_enabled=False,
            dns_servers_detected=2,
            adapter_connected=True,
            gateway_reachable=True,
            tls_cert_issue_detected=False,
            firewall_path_suspected=False,
            time_wait_count=10,
            established_count=10,
        ),
    )
    ta = assess_trust(
        snap,
        proof_result=None,
        proofs_requested=True,
        proof_engine_error="RuntimeError:mock",
    )
    assert ta.degraded_mode is True
    assert any("PROOF_ENGINE" in r for r in ta.degraded_reasons)
