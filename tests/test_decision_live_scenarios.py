"""Deterministic live hypothesis scoring from frozen snapshots (no I/O).

Scenarios mirror ``tests/scenarios/live_snapshot_fixtures.py`` catalog.
"""

from __future__ import annotations

import pytest

from src.decision_engine.live_scoring import score_live_snapshot
from tests.scenarios.live_snapshot_fixtures import (
    scenario_conflicting_signals,
    scenario_dns_failure,
    scenario_https_tls_failure,
    scenario_localhost_proxy_benign,
    scenario_tcp443_blocked,
)


def _table(scores: tuple[object, ...]) -> dict[str, float]:
    return {str(s.hypothesis): float(s.confidence) for s in scores}


def test_live_dns_failure_scores_dns_resolution_issue_on_top_deterministic() -> None:
    """live.dns_failure — resolver failure despite IP-layer ping."""
    snap = scenario_dns_failure()
    ranked = score_live_snapshot(snap)
    table = _table(ranked)

    assert ranked[0].hypothesis == "dns_resolution_issue"
    assert table["dns_resolution_issue"] == pytest.approx(0.78, abs=1e-6)
    bullet = ranked[0].evidence[-1]
    assert "ICMP" in bullet or "DNS" in bullet or "resolver" in bullet.lower()


def test_live_tcp443_blocked_prioritizes_winsock_or_stack_family() -> None:
    """live.tcp443_blocked — TCP/HTTPS probes fail while ICMP+DNS nominally OK."""
    snap = scenario_tcp443_blocked()
    ranked = score_live_snapshot(snap)

    table = _table(ranked)
    assert table["winsock_corruption_possible"] == pytest.approx(0.4, abs=1e-2)
    assert ranked[0].hypothesis == "winsock_corruption_possible"


def test_live_https_tls_failure_prioritizes_tls_path_issue() -> None:
    """live.https_tls_failure — TLS heuristic + HTTPS fail with TCP reaching 443."""
    snap = scenario_https_tls_failure()
    ranked = score_live_snapshot(snap)
    tls_conf = _table(ranked)["tls_path_issue"]
    assert tls_conf >= 0.54
    assert ranked[0].hypothesis == "tls_path_issue"


def test_live_conflicting_signals_yield_multiple_hot_hypotheses() -> None:
    """live.conflicting_stack — overlapping symptoms; deterministic multi-way ranking."""
    snap = scenario_conflicting_signals()
    ranked = score_live_snapshot(snap)
    table = _table(ranked)

    assert ranked[0].hypothesis == "dns_resolution_issue"
    assert table["dns_resolution_issue"] >= 0.7
    assert table["winhttp_proxy_issue"] >= 0.42
    high = sum(1 for s in ranked if s.confidence >= 0.45)
    assert high >= 3


@pytest.mark.parametrize("iteration", range(3))
def test_live_scenarios_are_stable_across_repeat_scoring(iteration: int) -> None:
    del iteration
    snaps = (
        scenario_dns_failure(),
        scenario_tcp443_blocked(),
        scenario_localhost_proxy_benign(),
    )
    tables = [_table(score_live_snapshot(s)) for s in snaps]
    for _ in range(2):
        again = [_table(score_live_snapshot(s)) for s in snaps]
        assert tables == again


def test_live_localhost_proxy_benign_dominates_unexpected_user_proxy() -> None:
    """Healthy transport with HKCU localhost proxy enabled — scorer pins unexpected_user_proxy."""
    snap = scenario_localhost_proxy_benign()
    ranked = score_live_snapshot(snap)
    table = _table(ranked)

    assert ranked[0].hypothesis == "unexpected_user_proxy"
    assert table["unexpected_user_proxy"] >= 0.88
    assert table["local_proxy_hijack"] >= 0.6
