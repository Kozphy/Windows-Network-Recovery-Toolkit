from __future__ import annotations

from platform_core.correlation_engine import correlate, observations_from_signals


def test_observations_from_signals_maps_names() -> None:
    obs = observations_from_signals(
        [{"signal_name": "proxy_enabled", "value": True, "source": "fixture"}]
    )
    assert len(obs) == 1
    assert obs[0].signal_name == "proxy_enabled"


def test_correlate_returns_evidence_tree_and_dry_run_flag() -> None:
    result = correlate(
        signals=[
            {"signal_name": "proxy_enabled", "value": True, "source": "test"},
            {"signal_name": "ping_ok", "value": True, "source": "test"},
        ],
        requested_action="inspect_proxy",
        endpoint_id="test-endpoint",
    )
    assert result["endpoint_id"] == "test-endpoint"
    assert "evidence_tree" in result
    assert "confidence_score" in result
    assert "state_transitions" in result
    assert result["dry_run_only"] is True
    assert result["replayable"] is True
