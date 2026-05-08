from __future__ import annotations

import json
from pathlib import Path

from platform_core.incidents import cluster_failure_events


def _load(name: str) -> list[dict]:
    p = Path(__file__).resolve().parent / "fixtures" / "platform" / name
    blob = json.loads(p.read_text(encoding="utf-8"))
    return blob["events"]


def test_cluster_proxy_multi_endpoint_deterministic() -> None:
    events = _load("multi_endpoint_proxy_outage.json")
    clusters = cluster_failure_events(events, window_seconds=7200)
    assert len(clusters) >= 1
    c0 = clusters[0]
    assert c0.event_count >= 2
    assert c0.affected_endpoint_count >= 2
    assert c0.category == "proxy"


def test_cluster_dns_outage() -> None:
    events = _load("multi_endpoint_dns_outage.json")
    clusters = cluster_failure_events(events, window_seconds=3600)
    assert clusters
    assert all(cl.category == "dns" for cl in clusters)


def test_cluster_empty_input() -> None:
    assert cluster_failure_events([]) == []
