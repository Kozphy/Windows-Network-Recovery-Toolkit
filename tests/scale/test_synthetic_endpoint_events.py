"""Synthetic local scale tests — 100 / 1k / 10k endpoint events (not production benchmarks)."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.fleet.ingestion import FleetIngestGateway
from src.platform_core.scale.replay import verify_deterministic_replay
from src.platform_core.scale.synthetic import (
    SYNTHETIC_LIMITATIONS,
    ingest_synthetic_batch,
    synthetic_fleet_envelope,
)

SCALE_COUNTS = (100, 1_000, 10_000)


@pytest.mark.scale
@pytest.mark.parametrize("endpoint_count", SCALE_COUNTS)
def test_synthetic_endpoint_ingest_scale(
    endpoint_count: int,
    fleet_gateway: FleetIngestGateway,
    tmp_path: Path,
) -> None:
    """Ingest N unique synthetic endpoint events into local WAL."""
    summary = ingest_synthetic_batch(fleet_gateway, count=endpoint_count, seed=endpoint_count)
    assert summary["accepted"] == endpoint_count
    assert summary["conflicts"] == 0
    assert summary["synthetic"] is True
    assert SYNTHETIC_LIMITATIONS[0] in summary["limitations"][0]

    wal = tmp_path / "fleet_ingest_wal.jsonl"
    assert wal.is_file()
    lines = [line for line in wal.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == endpoint_count

    ok, digest = verify_deterministic_replay(wal)
    assert ok is True, digest
    assert digest


@pytest.mark.scale
@pytest.mark.parametrize("endpoint_count", SCALE_COUNTS)
def test_synthetic_envelopes_are_deterministic(endpoint_count: int) -> None:
    """Same seed/index yields identical fleet envelopes."""
    a = synthetic_fleet_envelope(index=0, seed=endpoint_count)
    b = synthetic_fleet_envelope(index=0, seed=endpoint_count)
    assert a.model_dump(mode="json") == b.model_dump(mode="json")
    assert a.event_id != synthetic_fleet_envelope(index=1, seed=endpoint_count).event_id
