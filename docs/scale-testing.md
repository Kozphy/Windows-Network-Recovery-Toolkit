# Synthetic local scale testing (Phase 4)

**Status:** Contract tests for ingest, spool, audit chain, and replay under synthetic load.

**Related:** [enterprise-hardening-roadmap.md](enterprise-hardening-roadmap.md) · [observability.md](observability.md) · [agent-deployment.md](agent-deployment.md)

---

## What this is (and is not)

| Claim | Supported? |
|-------|------------|
| Synthetic 100 / 1k / 10k endpoint events ingest locally | **Yes** — `tests/scale/` |
| Concurrent JSONL append/read contracts hold on one host | **Yes** — `tests/concurrency/` |
| Hash-chained audit verifies after concurrent writers | **Yes** — with advisory file locks |
| Deterministic replay digest stable after concurrent ingest | **Yes** — partition projection replay |
| Proven enterprise production fleet scale (100k+ endpoints) | **No** |
| Multi-tenant Kafka / regional ingest benchmarks | **No** — out of scope |

All results are **synthetic local scale testing** on a developer machine. Do not cite these tests as production capacity proof.

---

## Test layout

| Path | Purpose |
|------|---------|
| `tests/scale/test_synthetic_endpoint_events.py` | 100, 1,000, 10,000 unique synthetic fleet envelopes |
| `tests/concurrency/test_concurrent_io.py` | Concurrent ingest, spool, audit chain, replay, locked JSONL |
| `src/platform_core/scale/synthetic.py` | Deterministic envelope + spool row builders |
| `src/platform_core/scale/replay.py` | WAL → partition projection digest (replay fingerprint) |
| `src/platform_core/io/locked_jsonl.py` | Advisory per-file locks (`fcntl` / `msvcrt`) |

---

## Run commands

```powershell
# Scale tiers (may take ~10–30s for 10k on modest hardware)
pytest -q tests/scale/ -m scale

# Concurrency contracts
pytest -q tests/concurrency/

# Combined Phase 4 slice
pytest -q tests/scale/ tests/concurrency/
```

Optional: exclude slow scale tier in quick CI:

```powershell
pytest -q tests/scale/ -m "scale" -k "not 10000"
```

---

## Synthetic event model

`src/platform_core/scale/synthetic.py` builds:

- **Fleet envelopes** — `FleetEventEnvelope` with stable `event_id`, `idempotency_key`, and `endpoint_id_hash` derived from `(seed, index)`
- **Agent spool rows** — read-only, `synthetic: true`, explicit `limitations[]`

Every payload includes:

```text
Synthetic local scale test — not production telemetry.
Does not prove enterprise fleet scale or malware detection.
```

---

## Concurrency hardening

### Advisory file locks

`append_jsonl` paths used by:

- `platform_core/storage.py`
- `src/logging/audit.py` (agent spool)
- `src/platform_core/audit/writer.py` (hash-chained audit)

…delegate to `append_jsonl_locked()` when `src.platform_core.io.locked_jsonl` is available.

Locks use a sibling `*.lock` file with:

- **POSIX:** `fcntl.flock`
- **Windows:** `msvcrt.locking`

This is **local advisory locking** — not a distributed lock service.

### Hash chain under concurrency

`append_audit()` reads the chain tip and appends under the same file lock, so concurrent writers produce a single verifiable chain (order reflects lock acquisition, not wall-clock).

Verification:

```python
from src.platform_core.governance.chain_of_custody import verify_chain
ok, msg = verify_chain(records)
```

---

## Deterministic replay

After synthetic ingest to `fleet_ingest_wal.jsonl` (`FLEET_MODE=local`):

1. Load WAL rows
2. Sort by `event_id`
3. Recompute `assign_partition(tenant_id, endpoint_id_hash)`
4. Hash canonical projection → `projection_digest`

`verify_deterministic_replay(wal_path)` runs steps twice; digests must match.

This proves **replay idempotency** on stored envelopes — not live host re-probing.

---

## Explicit non-claims

- Not a substitute for load testing against real ingest gateways or stream brokers
- Does not measure p99 latency, memory ceilings, or disk IOPS at fleet scale
- Does not validate multi-host WAL merge or cross-region ordering
- Does not weaken `windows_network_toolkit/safety.py` or policy gates

---

## Verification checklist

- [ ] `pytest -q tests/scale/ tests/concurrency/` passes
- [ ] Docs and test output label results as **synthetic local scale**
- [ ] No new required external services (stdlib locks only)
