from __future__ import annotations

from platform_core.failure_scenarios import default_failure_scenarios, detect_endpoint_events
from platform_core.reasoning_engine import observation, run_reasoning
from platform_core.reasoning_models import ProofResult


def _proxy_path_observations():
    return [
        observation("ping_ok"),
        observation("dns_ok"),
        observation("tcp443_ok"),
        observation("browser_https_failed"),
        observation("wininet_proxy_changed"),
        observation("wininet_proxy_enabled"),
        observation("localhost_proxy_detected"),
        observation("proxy_bypass_succeeded"),
        observation("proxied_path_failed"),
    ]


def test_registry_contains_browser_proxy_path_regression() -> None:
    scenarios = default_failure_scenarios()
    scenario = scenarios["browser_proxy_path_regression"]
    assert "proxy_path_failure_confirmed" in scenario.states
    assert "total_network_outage" in scenario.alternative_hypotheses


def test_observations_become_endpoint_events() -> None:
    events = detect_endpoint_events(_proxy_path_observations())
    event_names = {event.event_type for event in events}
    assert "wininet_proxy_changed" in event_names
    assert "proxied_path_failed" in event_names
    assert all(event.observation_ids for event in events)


def test_proxy_path_scenario_ranks_above_alternatives() -> None:
    run = run_reasoning(
        _proxy_path_observations(),
        proof_result=ProofResult(
            hypothesis="browser_proxy_path_regression",
            status="CONFIRMED",
            confidence=0.95,
            checks_run=["proxy_bypass_contrast"],
        ),
        requested_action="restore_proxy",
    )
    assert run.accepted_hypothesis == "browser_proxy_path_regression"
    assert run.hypothesis_ranking[0]["confidence"] > 0.80
    assert run.evidence_tree.state_path == [
        "healthy_browser_path",
        "proxy_drift_detected",
        "browser_path_failure_suspected",
        "proxy_path_failure_confirmed",
    ]
    rejected = {item["hypothesis"] for item in run.evidence_tree.rejected_alternatives}
    assert "total_network_outage" in rejected
    assert "dns_only_failure" in rejected
