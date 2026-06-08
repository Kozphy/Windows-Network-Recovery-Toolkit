# ADR-008: Fleet Scale Architecture (100,000 Endpoints)

## Status

Proposed

## Context

The platform currently operates **local-first** with append-only JSONL, a single FastAPI instance, and demo RBAC headers. Target scale:

- **100,000 endpoints**
- **~10–50 events/endpoint/day** → 1–5M events/day (~12–60 events/sec average; 10× burst headroom)
- **Multi-tenant** enterprise customers (1k–50k endpoints each)
- **SRE requirements**: idempotent ingestion, deduplication, partition-scoped replay, lifecycle MTTR at fleet scope

JSONL on a single host **cannot** be the system of record at this scale.

## Decision

Adopt a **log-oriented, event-streaming control plane** with strict contracts already defined in `platform_core/fleet/`:

| Concern | Technology (reference) | Contract module |
|---------|------------------------|-----------------|
| Distributed ingestion | Regional ingest gateways + agent local WAL | `fleet/ingestion.py` |
| Message queue (buffer) | Kafka / Redpanda (or NATS JetStream) | `fleet/streaming.py` |
| Event store (source of truth) | Kafka compacted topics + ClickHouse/Postgres cold store | `fleet/event_store.py` |
| Partitioning | `tenant_id + murmur3(endpoint_id) % N` | `fleet/partitioning.py` |
| Deduplication | Idempotency key `(tenant_id, producer_id, idempotency_key)` TTL 72h | `fleet/deduplication.py` |
| Idempotency | HTTP `Idempotency-Key` + event `event_id` UUIDv7 | `fleet/models.py` |
| Multi-tenant | Row-level `tenant_id`; topic prefix per tenant tier | `fleet/tenancy.py` |
| RBAC | Entra ID / OIDC JWT with `tenant_id`, `roles[]` claims | `fleet/rbac.py` |
| Observability | OTel → Tempo; Prometheus federation; tenant labels | existing + `fleet/observability.py` |
| Replay at scale | Partition workers + deterministic projector snapshots | `fleet/replay.py` |

### Non-negotiable invariants (unchanged at scale)

1. Observation ≠ Proof  
2. Correlation ≠ Causation  
3. Confidence ≠ Certainty  
4. Append-only audit — no UPDATE/DELETE on domain events  
5. Policy PREVIEW default; ALLOW requires proof + confirmation  

## Consequences

- **Dual-write migration period**: agents write local WAL + async stream; ingest gateways dedupe before append.
- **Read path splits**: hot queries (last 24h) from stream consumer state; cold analytics from object store.
- **Replay becomes a batch job** per `(tenant_id, partition_id, time_range)` — not single-machine JSONL scan.
- **Demo mode preserved**: `FLEET_MODE=local` keeps JSONL for dev/CI.

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Scale JSONL with sharding | No consumer groups, no backpressure, replay O(n) per host |
| Single Postgres primary | Write ceiling ~10–20k TPS with JSONB; hotspot on incident aggregates |
| Push all events to SaaS SQLite | Already rejected in ADR-003; breaks audit/replay |

## References

- `docs/architecture/fleet_scale_100k.md`
- `docs/migration/fleet_scale_migration_plan.md`
- `platform_core/fleet/`
