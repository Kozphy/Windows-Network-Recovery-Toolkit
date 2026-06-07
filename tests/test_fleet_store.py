"""Tests for JSONL fleet store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from platform_core.fleet_store import (
    append_heartbeat,
    apply_stale_policy,
    get_endpoint,
    list_endpoints,
)


def test_heartbeat_creates_endpoint(tmp_path: Path, monkeypatch) -> None:
    store = tmp_path / "fleet_endpoints.jsonl"
    monkeypatch.setattr("platform_core.fleet_store._path", lambda name: store)
    record = append_heartbeat(
        {"endpoint_id": "demo-endpoint-001", "last_seen": "2026-01-15T12:00:00+00:00"},
        store_path=store,
    )
    assert record.endpoint_id == "demo-endpoint-001"
    assert get_endpoint("demo-endpoint-001", store_path=store) is not None


def test_newer_heartbeat_updates_latest_state(tmp_path: Path) -> None:
    store = tmp_path / "fleet_endpoints.jsonl"
    append_heartbeat(
        {"endpoint_id": "demo-endpoint-001", "last_seen": "2026-01-15T12:00:00+00:00", "risk_state": "healthy"},
        store_path=store,
    )
    append_heartbeat(
        {
            "endpoint_id": "demo-endpoint-001",
            "last_seen": "2026-01-15T13:00:00+00:00",
            "risk_state": "degraded",
            "latest_diagnosis_id": "diag-002",
        },
        store_path=store,
    )
    record = get_endpoint("demo-endpoint-001", store_path=store)
    assert record is not None
    assert record.last_seen.startswith("2026-01-15T13:00")
    assert record.risk_state == "degraded"
    assert record.latest_diagnosis_id == "diag-002"
    assert len(list_endpoints(store_path=store)) == 1


def test_stale_endpoint_becomes_unknown(tmp_path: Path) -> None:
    store = tmp_path / "fleet_endpoints.jsonl"
    old = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    append_heartbeat(
        {"endpoint_id": "demo-endpoint-001", "last_seen": old, "risk_state": "healthy"},
        store_path=store,
    )
    records = apply_stale_policy(list_endpoints(store_path=store), stale_after_seconds=3600)
    assert records[0].risk_state == "unknown"
