"""Concurrency tests — synthetic local ingest, spool, audit chain, replay."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from platform_core.fleet.ingestion import FleetIngestGateway
from platform_core.storage import iter_jsonl
from src.logging.audit import append_jsonl
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain
from src.platform_core.io.locked_jsonl import read_jsonl_locked
from src.platform_core.scale.replay import verify_deterministic_replay
from src.platform_core.scale.synthetic import synthetic_fleet_envelope, synthetic_spool_event
from windows_network_toolkit.agent.spool import append_spool_event, read_spool_lines, spool_status


def _ingest_many(gateway: FleetIngestGateway, start: int, count: int, seed: int) -> int:
    accepted = 0
    for index in range(start, start + count):
        result = gateway.ingest_one(synthetic_fleet_envelope(index=index, seed=seed))
        if result.dedup.outcome == "accepted":
            accepted += 1
    return accepted


def test_concurrent_evidence_ingestion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent fleet ingest accepts all unique synthetic events."""
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setenv("FLEET_MODE", "local")
    gateway = FleetIngestGateway()
    workers = 8
    per_worker = 50
    seed = 4242

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_ingest_many, gateway, i * per_worker, per_worker, seed)
            for i in range(workers)
        ]
        accepted = sum(f.result() for f in as_completed(futures))

    assert accepted == workers * per_worker
    wal = tmp_path / "fleet_ingest_wal.jsonl"
    rows = list(iter_jsonl(wal))
    assert len(rows) == workers * per_worker
    event_ids = {row["event_id"] for row in rows}
    assert len(event_ids) == workers * per_worker


def test_concurrent_spool_append_and_read(tmp_path: Path) -> None:
    """Concurrent spool writers produce parseable rows; readers see consistent depth."""
    spool = tmp_path / "concurrent-spool.jsonl"
    workers = 10
    per_worker = 20
    seed = 99

    def _append_batch(start: int) -> None:
        for index in range(start, start + per_worker):
            append_spool_event(spool, synthetic_spool_event(index=index, seed=seed))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_append_batch, i * per_worker) for i in range(workers)]
        for future in as_completed(futures):
            future.result()

    rows = read_spool_lines(spool)
    assert len(rows) == workers * per_worker
    for row in rows:
        assert row["read_only"] is True
        assert row["synthetic"] is True
    status = spool_status(spool)
    assert status["event_count"] == workers * per_worker


def test_audit_hash_chain_integrity_under_concurrent_writes(tmp_path: Path) -> None:
    """Hash chain verifies after concurrent append_audit calls."""
    reset_chain_for_tests()
    audit_path = tmp_path / "concurrent-chain.jsonl"
    workers = 12
    per_worker = 10

    def _append_batch(worker_id: int) -> None:
        for seq in range(per_worker):
            append_audit(
                "event_received",
                incident_id=f"inc-{worker_id}-{seq}",
                trace_id=f"trace-{worker_id}",
                path=audit_path,
            )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_append_batch, i) for i in range(workers)]
        for future in as_completed(futures):
            future.result()

    records = read_jsonl_locked(audit_path)
    assert len(records) == workers * per_worker
    ok, message = verify_chain(records)
    assert ok is True, message


def test_deterministic_replay_after_concurrent_ingestion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replay digest is stable after concurrent ingest into local WAL."""
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setenv("FLEET_MODE", "local")
    gateway = FleetIngestGateway()
    workers = 16
    per_worker = 40
    seed = 2026

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_ingest_many, gateway, i * per_worker, per_worker, seed)
            for i in range(workers)
        ]
        assert sum(f.result() for f in as_completed(futures)) == workers * per_worker

    wal = tmp_path / "fleet_ingest_wal.jsonl"
    ok, digest = verify_deterministic_replay(wal)
    assert ok is True, digest

    # Re-ingest duplicates must not change replay digest for accepted unique set.
    first_digest = digest
    for index in range(workers * per_worker):
        gateway.ingest_one(synthetic_fleet_envelope(index=index, seed=seed))
    ok, digest_after_dup = verify_deterministic_replay(wal)
    assert ok is True
    assert digest_after_dup == first_digest


def test_concurrent_plain_jsonl_append_locked(tmp_path: Path) -> None:
    """Locked append_jsonl produces one JSON object per line under contention."""
    target = tmp_path / "plain.jsonl"
    workers = 8
    per_worker = 25

    def _writer(start: int) -> None:
        for index in range(start, start + per_worker):
            append_jsonl(target, {"index": index, "synthetic": True})

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_writer, i * per_worker) for i in range(workers)]
        for future in as_completed(futures):
            future.result()

    rows = read_jsonl_locked(target)
    assert len(rows) == workers * per_worker
    indices = {row["index"] for row in rows}
    assert len(indices) == workers * per_worker
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            json.loads(line)
