# Endpoint Reliability Platform architecture

This diagram frames the **optional** platform layer: local-first telemetry, append-only JSONL, policy gates, and a localhost dashboard. It **does not** replace beginner `.bat` scripts or the core **`python -m src`** CLI.

```mermaid
flowchart LR
  subgraph Endpoint["Windows endpoints"]
    A[Batch scripts untouched]
    B[python -m src CLI]
    C[endpoint_agent --service]
  end
  subgraph Collect["Observe & record"]
    D[Snapshots / signals]
    E[Failure events JSONL]
    F[Drift / evidence context]
  end
  subgraph Core["platform_core"]
    G[Schemas & models]
    H[policy_engine + rbac]
    I[remediation_registry allowlist]
    J[audit + metrics]
    FS[fleet_store + incident_engine]
    RM[reliability_metrics / SLO]
  end
  subgraph Telemetry["telemetry/"]
    TW[registry_writer_fusion]
  end
  subgraph API["backend /platform/*"]
    K[POST /platform/ingest/*]
    L[Remediation preview execute]
    M[GET metrics incidents attribution]
  end
  subgraph UI["Next.js /platform"]
    N[Timeline + KPIs]
  end
  A --> Collect
  B --> Collect
  C --> Collect
  Collect --> Core
  Core --> API
  API --> UI
```

## Pipeline (mental model)

1. **Collect** — diagnostics snapshots, proxy drift rows, heartbeat.  
2. **Snapshot / normalize** — privacy redaction (`platform_core.privacy`).  
3. **Detect drift** — compare baselines (`network-state`, proxy guard streams, or FailureBlocks).  
4. **Attribute** — `telemetry/` fuses registry writer telemetry with listener observations; `evidence/` provides Procmon/Sysmon tiers (**honest labeling**).  
5. **Decide policy** — `platform_core.policy` + **`policy_engine.evaluate_route_decision`**.  
6. **Preview remediation** — `POST /platform/remediation/preview` (always before execute).  
7. **Audit** — append-only `audit.jsonl` (including **`execute_live_pending`** before subprocess).  
8. **Metrics** — Prometheus `/metrics` (labeled pipeline counters; [observability_architecture.md](observability_architecture.md)).  
9. **Dashboard** — Grafana + `GET /platform/metrics`, `/incidents`, `/events`, attribution drill-down.

## Data plane

All platform rows target files under **`PLATFORM_DATA_DIR`** (`platform_data/` by default):

| Shard | Purpose |
| --- | --- |
| `endpoints.jsonl` | Heartbeats / identity |
| `snapshots.jsonl` | Latest diagnostic captures |
| `failure_events.jsonl` | Ingested failures |
| `remediation_previews.jsonl` | Typed previews |
| `remediation_executions.jsonl` | dry_run / blocked / outcomes |
| `audit.jsonl` | Operator-facing audit |
| `platform_signals.jsonl` | KPI source for metrics merger |
| `fleet_endpoints.jsonl` | Fleet heartbeats (`fleet_store`) |
| `incidents.jsonl` | Incident lifecycle rows |
| `attribution_context.jsonl` | Optional offline attribution fixtures |

Typed envelope models for interviews live in **`platform_core/platform_event_contract.py`**.

## RBAC shortcuts (portfolio)

| Role | Capability |
| --- | --- |
| `viewer` | Read KPIs/events/incidents |
| `operator` | Ingest + preview + dry-run execute |
| `admin` | Low/medium allowlisted live repair + typed confirmation |
| `security_auditor` | Audit + attribution reads; **no** ingest/previews |

See [`platform_api_contract.md`](platform_api_contract.md) and [`rbac_and_remediation.md`](rbac_and_remediation.md).

## Reliability pipeline (v2)

Production-grade reasoning lives in `platform_core/reliability/` and exposes versioned HTTP at `/platform/v2/*`:

```
Observation → Event Normalization → State Machine → Hypothesis Ranking
→ Evidence Graph → Policy → Signed Decision → Replay
```

| Component | Path |
| --- | --- |
| Append-only events | `platform_events.jsonl` (+ optional PostgreSQL `platform_core/db/schema.sql`) |
| State machine | `platform_core/reliability/platform_states.py` |
| Evidence graph | `platform_core/reliability/evidence_graph.py` |
| Policy YAML | `config/platform_policy.yaml` |
| API v2 | `backend/platform_v2_routes.py` |
| Next.js pages | `frontend/app/platform/{events,states,evidence,policies,replay,timeline}/` |

Design artifacts: [`adr/ADR-006-reliability-platform.md`](adr/ADR-006-reliability-platform.md), [`adr/ADR-007-sre-event-sourcing.md`](adr/ADR-007-sre-event-sourcing.md), [`diagrams/reliability_platform.md`](diagrams/reliability_platform.md), [`threat_model_reliability_platform.md`](threat_model_reliability_platform.md).

## SRE operations layer

Google SRE-style incident handling in `platform_core/sre/`:

| Capability | Store / API |
| --- | --- |
| Canonical event log | `sre_domain_events.jsonl` |
| Incident lifecycle | `POST /platform/v2/sre/incidents` |
| Investigation + RCA | `POST .../investigate`, `GET .../rca` |
| Timeline reconstruction | `GET .../timeline` |
| Lifecycle MTTR | `GET /platform/v2/sre/metrics/mttr` → `platform_sre_mttr_seconds` |
| Postmortem | `POST .../postmortem` → `platform_data/postmortems/*.md` |
| Failure domains | `GET /platform/v2/sre/health` |

## Fleet scale (100k endpoints)

Target architecture for **100,000 endpoints** with distributed ingest, event streaming, partitioning, deduplication, multi-tenant RBAC, and partition-scoped replay.

| Document | Purpose |
| --- | --- |
| [`architecture/fleet_scale_100k.md`](architecture/fleet_scale_100k.md) | System diagrams, topic topology, SLOs |
| [`migration/fleet_scale_migration_plan.md`](migration/fleet_scale_migration_plan.md) | Phased migration JSONL → stream |
| [`adr/ADR-008-fleet-scale-100k-endpoints.md`](adr/ADR-008-fleet-scale-100k-endpoints.md) | Architecture decision record |
| `platform_core/fleet/` | Wire contracts (envelope, dedup, partitioning) |
| `POST /platform/v3/fleet/ingest/batch` | Ingest gateway API |
| `docker-compose.scale.yml` | Redpanda + Redis + Postgres dev stack |
