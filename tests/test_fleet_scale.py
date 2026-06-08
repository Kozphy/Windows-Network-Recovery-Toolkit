"""Fleet-scale contract tests — partitioning, dedup, ingest, replay specs."""

from __future__ import annotations

from platform_core.fleet.deduplication import InMemoryIdempotencyStore
from platform_core.fleet.ingestion import FleetIngestGateway
from platform_core.fleet.models import FleetEventEnvelope, TenantContext
from platform_core.fleet.partitioning import assign_partition, partition_count
from platform_core.fleet.replay import ReplayCoordinator, ReplayJobSpec


def _envelope(
    *,
    tenant_id: str = "tenant-a",
    endpoint_hash: str = "a" * 32,
    idempotency_key: str = "batch-001",
    event_id: str = "evt-test-001",
) -> FleetEventEnvelope:
    return FleetEventEnvelope(
        event_id=event_id,
        idempotency_key=idempotency_key,
        tenant=TenantContext(tenant_id=tenant_id),
        producer_id="agent-test-1",
        endpoint_id_hash=endpoint_hash,
        payload={"signal_name": "wininet_proxy_enabled"},
    ).finalize()


def test_partition_deterministic() -> None:
    p1 = assign_partition("tenant-x", "b" * 32)
    p2 = assign_partition("tenant-x", "b" * 32)
    assert p1.partition_id == p2.partition_id
    assert 0 <= p1.partition_id < partition_count()


def test_partition_spreads_endpoints() -> None:
    parts = {assign_partition("t", f"{i:032x}").partition_id for i in range(500)}
    assert len(parts) > 10


def test_dedup_accept_and_duplicate() -> None:
    store = InMemoryIdempotencyStore()
    gw = FleetIngestGateway(dedup_store=store)
    env = _envelope()
    r1 = gw.ingest_one(env)
    assert r1.dedup.outcome == "accepted"
    r2 = gw.ingest_one(env)
    assert r2.dedup.outcome == "duplicate"
    assert r2.accepted is True


def test_dedup_conflict_on_key_reuse() -> None:
    store = InMemoryIdempotencyStore()
    gw = FleetIngestGateway(dedup_store=store)
    e1 = _envelope(event_id="evt-1", idempotency_key="same-key")
    e2 = _envelope(event_id="evt-2", idempotency_key="same-key")
    e2.payload["different"] = True
    e2_final = e2.model_copy(update={"payload_hash": e2.compute_payload_hash()})
    gw.ingest_one(e1)
    r = gw.ingest_one(e2_final)
    assert r.dedup.outcome == "conflict"
    assert r.accepted is False


def test_ingest_writes_local_wal(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setenv("FLEET_MODE", "local")
    gw = FleetIngestGateway()
    gw.ingest_one(_envelope())
    wal = tmp_path / "fleet_ingest_wal.jsonl"
    assert wal.is_file()
    assert wal.read_text(encoding="utf-8").count("evt-test") >= 1


def test_replay_job_spec_seed() -> None:
    spec = ReplayJobSpec.for_incident(
        job_id="job-1",
        tenant_id="tenant-a",
        incident_id="inc-abc",
        partition_id=12,
        time_start_utc="2026-06-01T00:00:00+00:00",
        time_end_utc="2026-06-01T01:00:00+00:00",
    )
    assert spec.deterministic_seed
    assert spec.scope == "incident"


def test_replay_coordinator_local_missing_incident() -> None:
    coord = ReplayCoordinator()
    spec = ReplayJobSpec.for_incident(
        job_id="job-missing",
        tenant_id="t",
        incident_id="inc-none",
        partition_id=0,
        time_start_utc="2026-01-01T00:00:00+00:00",
        time_end_utc="2026-01-01T01:00:00+00:00",
    )
    result = coord.run_local(spec)
    assert result.parity.get("found") is False
