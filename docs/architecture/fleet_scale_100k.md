# Fleet Scale Architecture — 100,000 Endpoints

Target: **100,000 Windows endpoints**, multi-tenant enterprise fleet, SRE-grade audit/replay, **correctness over convenience**.

Contracts: `platform_core/fleet/` · ADR: [`ADR-008`](../adr/ADR-008-fleet-scale-100k-endpoints.md) · Migration: [`fleet_scale_migration_plan.md`](../migration/fleet_scale_migration_plan.md)

---

## 1. Capacity model

| Assumption | Value |
|------------|-------|
| Endpoints | 100,000 |
| Events / endpoint / day | 20 (telemetry + state + audit) |
| Daily volume | **2M events/day** |
| Average ingest | **~23 events/sec** |
| Peak (×10 burst) | **~230 events/sec** |
| Tenants | 50–200 (largest: 50k endpoints) |
| Retention (hot stream) | 30 days |
| Retention (cold store) | 7 years (compliance) |

**Design headroom:** 2,000 events/sec sustained (≈100× average) via partitioned streaming.

---

## 2. System context

```mermaid
flowchart TB
  subgraph endpoints["100k Windows Endpoints"]
    AG1[Endpoint Agent]
    WAL[(Local WAL)]
    AG1 --> WAL
  end

  subgraph edge["Regional Ingest Tier"]
    IG1[Ingest Gateway AZ-1]
    IG2[Ingest Gateway AZ-2]
    DEDUP[(Idempotency Store Redis/Postgres)]
    IG1 --> DEDUP
    IG2 --> DEDUP
  end

  subgraph stream["Event Streaming Layer"]
    K1[Redpanda/Kafka Cluster]
    T1[erp.telemetry.shared]
    T2[erp.sre.domain.shared]
    T3[erp.replay.jobs]
    K1 --> T1
    K1 --> T2
    K1 --> T3
  end

  subgraph process["Stream Processing"]
    C1[Normalizer Consumers]
    C2[State Projector Workers]
    C3[SRE Incident Projector]
    C4[Replay Workers]
  end

  subgraph store["Durable Stores"]
    PG[(Postgres — metadata + idempotency)]
    CH[(ClickHouse — analytics)]
    S3[(Object Store — cold audit)]
  end

  subgraph control["Control Plane"]
    API[FastAPI Fleet API]
    AUTH[Entra ID / OIDC]
    API --> AUTH
  end

  subgraph obs["Observability"]
    PROM[Prometheus Federation]
    TEMPO[Tempo Traces]
    GRAF[Grafana]
    LOKI[Loki Logs]
  end

  AG1 -->|HTTPS batch + Idempotency-Key| IG1
  AG1 -->|failover| IG2
  IG1 --> K1
  IG2 --> K1
  K1 --> C1 --> PG
  K1 --> C2 --> PG
  K1 --> C3 --> PG
  T3 --> C4 --> S3
  C1 --> CH
  API --> PG
  API --> CH
  process --> PROM
  API --> PROM
  PROM --> GRAF
```

---

## 3. Distributed ingestion

### Agent responsibilities (data plane)

1. **Collect** — registry, Sysmon, ETW, Event Log, network telemetry (unchanged semantics).
2. **Normalize** — `FleetEventEnvelope` (`fleet.envelope.v1`).
3. **Write local WAL** — `agent_wal.jsonl` (survives network partition).
4. **Batch upload** — HTTPS POST to regional gateway with:
   - `Idempotency-Key: {batch_uuid}`
   - `Authorization: Bearer {agent_jwt}`
   - `X-Tenant-Id: {tenant_id}`

### Gateway responsibilities (ingest tier)

```
POST /platform/v3/ingest/batch
```

| Step | Action | Failure mode |
|------|--------|--------------|
| 1 | JWT + tenant RBAC | 401/403 |
| 2 | Schema validate envelope | 400 |
| 3 | `IdempotencyStore.check_and_record` | 409 on conflict |
| 4 | `assign_partition(tenant_id, endpoint_id_hash)` | — |
| 5 | Publish to stream topic | 503 if circuit open; agent retains WAL |
| 6 | Return per-event `IngestResult` | Agent acks WAL offset |

```mermaid
sequenceDiagram
  participant Agent
  participant WAL as Local WAL
  participant GW as Ingest Gateway
  participant Dedup as Idempotency Store
  participant Bus as Event Stream

  Agent->>WAL: append envelope
  Agent->>GW: POST batch (Idempotency-Key)
  GW->>Dedup: check_and_record (atomic)
  alt duplicate retry
    Dedup-->>GW: duplicate (same event_id)
    GW-->>Agent: 200 accepted (no republish)
  else new event
    Dedup-->>GW: accepted
    GW->>Bus: publish(partition_key, payload)
    Bus-->>GW: ack
    GW-->>Agent: 200 + partition_id
    Agent->>WAL: commit offset
  end
```

---

## 4. Event streaming topology

### Topics (reference naming)

| Topic | Partitions | Retention | Key |
|-------|------------|-----------|-----|
| `erp.telemetry.shared` | 256 | 30d | `tenant_id:endpoint_id_hash` |
| `erp.sre.domain.shared` | 256 | 90d | `tenant_id:incident_id` |
| `erp.audit.signed` | 128 | 7y (tiered) | `tenant_id:decision_id` |
| `erp.replay.jobs` | 64 | 7d | `tenant_id:partition_id` |
| `erp.replay.results` | 64 | 30d | `job_id` |
| `erp.dlq.ingest` | 16 | 30d | — |

**Enterprise tier:** dedicated topics `erp.*.enterprise.{tenant_id}` for noisy-neighbor isolation.

### Consumer groups

| Group | Purpose | Scale |
|-------|---------|-------|
| `normalizer-v1` | Raw → `NormalizedPlatformEvent` | 32 workers |
| `state-projector-v1` | Deterministic FSM projections | 32 workers |
| `sre-incident-projector` | Incident read models | 16 workers |
| `audit-archiver` | Cold store + HMAC verify | 8 workers |
| `replay-worker` | Partition-scoped replay jobs | 16 workers (burst) |

---

## 5. Partitioning strategy

```python
partition_id = blake2b(f"{tenant_id}:{endpoint_id_hash}") % FLEET_PARTITION_COUNT
# default FLEET_PARTITION_COUNT=256
```

| Property | Guarantee |
|----------|-----------|
| Per-endpoint ordering | Same `partition_key` → same partition |
| Tenant fairness | Large tenants spread across all partitions |
| Replay parallelism | One worker per `(tenant_id, partition_id, time_range)` |
| Rebalance | Double `FLEET_PARTITION_COUNT` with consumer pause (planned) |

```mermaid
flowchart LR
  subgraph hash["Partition function"]
    T[tenant_id]
    E[endpoint_id_hash]
    T --> H[blake2b]
    E --> H
    H --> M["% 256"]
  end
  M --> P0[Partition 0]
  M --> P1[Partition 1]
  M --> PN[Partition 255]
```

---

## 6. Deduplication & idempotency

### Three layers

| Layer | Key | Store | TTL |
|-------|-----|-------|-----|
| HTTP | `Idempotency-Key` header | Gateway memory → Redis | 72h |
| Envelope | `(tenant_id, producer_id, idempotency_key)` | Redis/Postgres | 72h |
| Event | `event_id` (globally unique) | Stream log compaction | 90d |

### Outcomes

| `DedupDecision` | HTTP | Agent action |
|-----------------|------|--------------|
| `accepted` | 200 | Commit WAL |
| `duplicate` | 200 | Commit WAL (retry OK) |
| `conflict` | 409 | Alert + quarantine batch |

**Rule:** Same idempotency key + different `payload_hash` → **conflict** (never silent overwrite).

---

## 7. Multi-tenant model

```mermaid
flowchart TB
  subgraph tenantA["Tenant A (50k endpoints)"]
    EA[Endpoints]
  end
  subgraph tenantB["Tenant B (2k endpoints)"]
    EB[Endpoints]
  end
  subgraph plane["Shared Control Plane"]
  API[Fleet API]
  end
  EA -->|JWT tenant_id=A| API
  EB -->|JWT tenant_id=B| API
  API -->|RLS filter| DB[(Postgres RLS)]
```

| Isolation | Mechanism |
|-----------|-----------|
| Data plane | `tenant_id` on every envelope + stream headers |
| Database | Postgres RLS: `tenant_id = current_setting('app.tenant_id')` |
| Cache | Redis key prefix `t:{tenant_id}:` |
| Observability | `tenant_id` label (low cardinality — tens of tenants, not 100k) |
| Replay | Jobs scoped to `tenant_id` + `partition_id` |
| Blast radius | Per-tenant ingest rate limit; circuit breaker per tenant |

---

## 8. RBAC (production)

Demo headers (`X-Operator-Role`) are **replaced** by JWT claims:

```json
{
  "sub": "operator@contoso.com",
  "tenant_id": "tenant-contoso",
  "roles": ["tenant_operator"],
  "org_id": "org-uuid"
}
```

| Role | Ingest | Read metrics | Investigate | Replay | Postmortem | Cross-tenant |
|------|--------|--------------|-------------|--------|------------|--------------|
| `tenant_viewer` | — | ✓ | — | — | read | — |
| `tenant_operator` | — | ✓ | ✓ | — | read | — |
| `tenant_admin` | — | ✓ | ✓ | ✓ | ✓ | — |
| `tenant_security_auditor` | — | ✓ | read | ✓ | ✓ | — |
| `platform_admin` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (break-glass) |

**Agent auth:** separate machine identity (mTLS or client-credentials JWT), scoped to single `tenant_id`.

---

## 9. Observability at scale

```mermaid
flowchart LR
  subgraph signals["Signals"]
    IG[Ingest Gateway]
    CW[Consumer Workers]
    API[Fleet API]
  end
  subgraph pipeline["Telemetry Pipeline"]
    OTEL[OTel Collector]
    PROM[Prometheus]
    TEMPO[Tempo]
    LOKI[Loki]
  end
  subgraph alert["Alerting"]
    AM[Alertmanager]
    PD[PagerDuty]
  end
  IG --> OTEL
  CW --> OTEL
  API --> OTEL
  OTEL --> PROM
  OTEL --> TEMPO
  OTEL --> LOKI
  PROM --> AM --> PD
```

### SLOs (100k fleet)

| SLO | Target | Burn alert |
|-----|--------|------------|
| Ingest availability | 99.9% | 5xx > 0.1% 15m |
| Ingest p99 latency | < 500ms | > 1s 10m |
| Partition lag | < 60s p99 | > 300s 5m |
| Replay parity | 99.99% | any mismatch on decision_run |
| MTTR data freshness | < 5m | projector lag |

### Key metrics

See `platform_core/fleet/observability.py` — all counters carry `tenant_id` + `partition` labels where cardinality allows.

---

## 10. Replay at scale

**Problem:** Replaying 2M events/day × 30 days = 60M events — cannot scan JSONL on one host.

**Solution:** Partition-scoped replay jobs.

```mermaid
sequenceDiagram
  participant Op as Operator
  participant API as Fleet API
  participant Q as erp.replay.jobs
  participant W as Replay Worker
  participant S as Stream + Cold Store
  participant R as erp.replay.results

  Op->>API: POST /replay/jobs {incident_id, time_range}
  API->>API: resolve partitions for incident
  API->>Q: enqueue ReplayJobSpec per partition
  Q->>W: consume job
  W->>S: read events [time_start, time_end] partition=N
  W->>W: deterministic Projector.fold()
  W->>W: parity check vs stored decision
  W->>R: ReplayJobResult
  Op->>API: GET /replay/jobs/{id}
```

| Scope | Worker input | Output |
|-------|--------------|--------|
| `incident` | `sre.domain` events for `incident_id` | parity + postmortem input |
| `decision_run` | telemetry + decision snapshot | policy/state/hypothesis parity |
| `tenant_partition` | full partition time slice | projector rebuild benchmark |

Local dev: `ReplayCoordinator.run_local()` delegates to existing `TimeTravelReplay`.

---

## 11. Data store roles

| Store | Role | Not source of truth for |
|-------|------|-------------------------|
| **Kafka/Redpanda** | Hot event log, ordering, replay input | Long-term compliance (tiered) |
| **Postgres** | Idempotency, incident metadata, RBAC, API queries | Raw telemetry firehose |
| **ClickHouse** | Fleet analytics, MTTR rollups, dashboards | Strong consistency writes |
| **S3/Azure Blob** | Cold audit, postmortem artifacts | Real-time ingest |
| **Redis** | Idempotency hot path, rate limits | Durable event history |

---

## 12. Failure domain isolation (fleet extensions)

Existing `platform_core/sre/failure_domains.py` bulkheads extend to fleet tier:

| Domain | Isolation at scale |
|--------|-------------------|
| `telemetry_ingest` | Per-tenant rate limit + gateway circuit |
| `stream_publish` | Separate cluster for enterprise tier |
| `replay` | Dedicated worker pool; no shared CPU with ingest |
| `audit` | Async archiver — never blocks ingest path |

---

## 13. Local vs fleet mode

| `FLEET_MODE` | Behavior |
|--------------|----------|
| `local` (default) | WAL → `fleet_ingest_wal.jsonl`; existing JSONL pipelines |
| `stream` | Gateway publishes to configured `EventPublisher` adapter |

CI and laptop dev stay on `local`. Staging/prod use `stream`.

---

## 14. Related documents

- [`../migration/fleet_scale_migration_plan.md`](../migration/fleet_scale_migration_plan.md)
- [`../adr/ADR-008-fleet-scale-100k-endpoints.md`](../adr/ADR-008-fleet-scale-100k-endpoints.md)
- [`../fleet_architecture.md`](../fleet_architecture.md) (agent/control plane v1)
- [`../extension_points_multi_host_saas.md`](../extension_points_multi_host_saas.md)
- [`../observability_architecture.md`](../observability_architecture.md)
