"""Proxy path operational: composite states and guard policy integration."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.models import ParsedProxy
from src.proxy_guard.guard_evaluation import evaluate_proxy_transition
from src.proxy_guard.models import AttributionResult, ProxySnapshot
from src.proxy_guard.operator_language import display_policy_decision
from src.proxy_guard.policy import ProxyGuardPolicy
from src.proxy_guard.proxy_path_operational import (
    ProxyPathOperationalAssessment,
    _run_https_contrast,
    assess_proxy_path_operational,
    classify_composite_state,
    policy_for_composite,
)


def _parsed_localhost(port: int = 54321) -> ParsedProxy:
    return ParsedProxy(
        raw=f"127.0.0.1:{port}",
        proxy_mode="manual_localhost",
        is_missing=False,
        is_malformed=False,
        is_localhost_proxy=True,
        localhost_host="127.0.0.1",
        localhost_port=port,
        http_localhost_port=None,
        https_localhost_port=None,
        socks_port=None,
    )


def _snap(enable: int, server: str | None) -> ProxySnapshot:
    return ProxySnapshot(
        captured_at="2026-05-16T10:00:00Z",
        proxy_enable=enable,
        proxy_server=server,
        proxy_override=None,
        auto_config_url=None,
        auto_detect=0,
        winhttp_proxy="",
        winhttp_direct_access=True,
        winhttp_proxy_server_literal=None,
        git_http_proxy=None,
        git_https_proxy=None,
        npm_proxy=None,
        npm_https_proxy=None,
        user_http_proxy=None,
        user_https_proxy=None,
        user_all_proxy=None,
        user_no_proxy=None,
    )


def test_case_a_broken_loopback_dead_listener() -> None:
    state = classify_composite_state(
        proxy_enable=1,
        proxy_server="127.0.0.1:58644",
        auto_config_url=None,
        parsed=_parsed_localhost(58644),
        listener_up=False,
        proxied_https_ok=False,
        bypass_https_ok=True,
    )
    assert state == "LOOPBACK_BROKEN"
    assert policy_for_composite(state) == "remediation_preview"


def test_case_b_operational_listener_and_https() -> None:
    state = classify_composite_state(
        proxy_enable=1,
        proxy_server="127.0.0.1:54321",
        auto_config_url=None,
        parsed=_parsed_localhost(54321),
        listener_up=True,
        proxied_https_ok=True,
        bypass_https_ok=True,
    )
    assert state == "LOOPBACK_OPERATIONAL"
    assert policy_for_composite(state) == "observe_no_rollback"


def test_latent_misconfig_proxy_server_only() -> None:
    state = classify_composite_state(
        proxy_enable=0,
        proxy_server="127.0.0.1:54321",
        auto_config_url=None,
        parsed=_parsed_localhost(54321),
        listener_up=True,
        proxied_https_ok=None,
        bypass_https_ok=True,
    )
    assert state == "LATENT_MISCONFIG"


def test_enterprise_pac_takes_precedence() -> None:
    state = classify_composite_state(
        proxy_enable=1,
        proxy_server="127.0.0.1:1",
        auto_config_url="http://corp/pac.js",
        parsed=_parsed_localhost(1),
        listener_up=True,
        proxied_https_ok=True,
        bypass_https_ok=True,
    )
    assert state == "ENTERPRISE_PAC"


def test_guard_blocks_non_operational_path() -> None:
    assessment = ProxyPathOperationalAssessment(
        composite_state="LOOPBACK_BROKEN",
        registry_posture={},
        operational={"listener_up": False},
        evidence_tier="TIER_2_CONTRAST_TESTED",
        policy_recommendation="remediation_preview",
        epistemic_chain={},
        human_summary="broken",
    )
    policy = ProxyGuardPolicy(
        source_path=__file__,
        allowed_process_name_substrings=("node.exe",),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        trusted_exe_paths=(),
        allowed_autoconfig_url_substrings=(),
        observe_only_when_unknown_attribution=False,
    )
    gd = evaluate_proxy_transition(
        prior_snap=_snap(0, None),
        curr_snap=_snap(1, "127.0.0.1:54321"),
        parsed_prior=_parsed_localhost(),
        parsed_after=_parsed_localhost(),
        attribution=AttributionResult(mode="unknown", confidence="low", process=None, limitations=()),
        policy=policy,
        port_listen=True,
        path_assessment=assessment,
    )
    assert gd.decision == "blocked"
    assert gd.reason == "loopback_proxy_path_non_operational"
    assert display_policy_decision(gd.decision, reason=gd.reason) == "remediation_preview"


def test_guard_allows_operational_path_despite_unknown_attribution() -> None:
    assessment = ProxyPathOperationalAssessment(
        composite_state="LOOPBACK_OPERATIONAL",
        registry_posture={},
        operational={"listener_up": True, "proxied_https_ok": True},
        evidence_tier="TIER_2_CONTRAST_TESTED",
        policy_recommendation="observe_no_rollback",
        epistemic_chain={},
        human_summary="ok",
    )
    policy = ProxyGuardPolicy(
        source_path=__file__,
        allowed_process_name_substrings=(),
        allowed_process_names_exact=(),
        allow_when_attribution_empty=False,
        trusted_exe_paths=(),
        allowed_autoconfig_url_substrings=(),
        observe_only_when_unknown_attribution=True,
    )
    gd = evaluate_proxy_transition(
        prior_snap=_snap(0, None),
        curr_snap=_snap(1, "127.0.0.1:54321"),
        parsed_prior=_parsed_localhost(),
        parsed_after=_parsed_localhost(),
        attribution=AttributionResult(mode="unknown", confidence="low", process=None, limitations=()),
        policy=policy,
        port_listen=True,
        path_assessment=assessment,
    )
    assert gd.decision == "allowed"
    assert gd.reason == "loopback_path_operational_observe"


def test_assess_with_mocked_curl_contrast() -> None:
    def fake_run(argv, **kwargs):  # noqa: ANN001, ANN003
        proc = MagicMock()
        if "-x" in argv:
            proc.returncode = 1
            proc.stdout = "000"
            proc.stderr = ""
        else:
            proc.returncode = 0
            proc.stdout = "200"
            proc.stderr = ""
        return proc

    proxied, bypass = _run_https_contrast(
        parsed=_parsed_localhost(),
        proxy_enable=1,
        test_url="https://example.test",
        run=fake_run,
        curl_timeout=3.0,
    )
    assert proxied is False
    assert bypass is True

    assessment = assess_proxy_path_operational(
        proxy_enable=1,
        proxy_server="127.0.0.1:54321",
        auto_config_url=None,
        parsed=_parsed_localhost(),
        port_listen=False,
        run=fake_run,
        include_https_contrast=True,
        test_url="https://example.test",
        timeout_seconds=3.0,
    )
    assert assessment.composite_state == "LOOPBACK_BROKEN"
    assert assessment.evidence_tier == "TIER_2_CONTRAST_TESTED"
