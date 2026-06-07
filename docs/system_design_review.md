# System design review

Tier-1 Endpoint Reliability Platform — architecture for reviewers.

## Architecture diagram

```mermaid
flowchart LR
  subgraph endpoint [Windows Endpoint]
    CLI[python -m src]
    PG[proxy_guard]
    Agent[endpoint_agent]
  end
  subgraph core [platform_core]
    Reason[reasoning_engine]
    Policy[policy engine]
    Fleet[fleet_store]
    Inc[incident_engine]
    SLO[reliability_metrics]
  end
  subgraph telemetry [telemetry]
    Sysmon[sysmon_parser]
    Fusion[registry_writer_fusion]
  end
  subgraph store [Append-only JSONL]
    Audit[audit.jsonl]
    FleetLog[fleet_endpoints.jsonl]
    IncLog[incidents.jsonl]
  end
  subgraph api [backend FastAPI]
    Routes[/platform/*]
  end
  subgraph ui [frontend]
    Dash[Next.js dashboard]
  end
  CLI --> Reason
  PG --> Fusion
  Sysmon --> Fusion
  Agent --> Fleet
  Reason --> Policy
  Policy --> Audit
  Fleet --> FleetLog
  Inc --> IncLog
  Routes --> core
  Dash --> Routes
  SLO --> Routes
```

## Data flow

1. **Observe** — probes, registry snapshots, optional Sysmon fixtures.
2. **Reason** — rank hypotheses; attach evidence levels.
3. **Fuse** — correlate registry writers with listener observations.
4. **Policy** — ALLOW / PREVIEW / BLOCK; dry-run default.
5. **Audit** — append JSONL row with replay correlation IDs.
6. **Fleet/incidents/metrics** — derived from same JSONL streams.

## Failure modes

| Failure | Symptom | Mitigation |
|---------|---------|------------|
| Stale heartbeat | Endpoint `unknown` | `apply_stale_policy` |
| Missing writer telemetry | `LISTENER_OBSERVED` only | Import Sysmon EID 13 |
| Writer/listener mismatch | `WRITER_LISTENER_MISMATCH` | Manual investigation |
| Policy BLOCK | Execute rejected | Preview + confirmation |
| JSONL parse error | Skipped row in metrics | Contract tests |

## Policy gates

- Registry allowlist for mutation fields
- Typed confirmation strings
- RBAC roles (demo headers)
- `SAFE_MODE` and dry-run defaults
- Shell injection rejection

## Threat model summary

See [threat_model.md](threat_model.md). Key point: **listener ≠ registry writer proof**.

## Scaling path

| Stage | Storage | Notes |
|-------|---------|-------|
| Single endpoint | Local JSONL | Current default |
| Small fleet | Agent heartbeats → `fleet_endpoints.jsonl` | Implemented |
| Multi-site | Object storage + indexer | Future |
| SaaS control plane | Signed agent auth + streaming ingest | Out of repo scope |

## Module map

| Module | Responsibility |
|--------|----------------|
| `telemetry/` | Writer/listener fusion |
| `platform_core/fleet_store.py` | Endpoint heartbeats |
| `platform_core/incident_engine.py` | Incident rules + transitions |
| `platform_core/reliability_metrics.py` | SLO KPIs from JSONL |
| `backend/platform_routes.py` | HTTP contract |

Demo: [tier1_demo_walkthrough.md](tier1_demo_walkthrough.md)
