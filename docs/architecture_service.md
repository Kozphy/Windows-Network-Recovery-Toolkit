# Production service architecture

This document describes the **containerized Endpoint Reliability Platform service**: typed configuration, startup validation, cross-platform read-only diagnostics, and observability. It complements [architecture_platform.md](architecture_platform.md) (product mental model).

## Epistemic boundaries (non-negotiable)

| Principle | Meaning in this service |
|-----------|-------------------------|
| **Observation != Proof** | DNS, proxy registry reads, and listener hints are labeled `observation` — not writer proof. |
| **Correlation != Causation** | The correlation engine ranks hypotheses; it does not assert root cause. |
| **Policy ALLOW != Safety Guarantee** | `ALLOW` means the policy registry permits a *human-gated* preview/execute path — not autonomous repair. |

---

## Architecture diagram

```mermaid
flowchart TB
  subgraph Clients
    OP[Operator / SRE]
    AG[endpoint_agent optional]
    PROM[Prometheus]
  end

  subgraph Service["API container (FastAPI)"]
    CFG[platform_core.settings]
    SU[startup_checks]
    ND[network_diagnostics abstraction]
    WIN[WindowsNetworkDiagnostics]
    LIN[LinuxNetworkDiagnostics]
    CE[correlation_engine]
    PE[policy_engine + rbac]
    ST[JSONL storage]
    AU[append-only audit]
  end

  subgraph Observability
    PR[Prometheus scrape /metrics]
    GF[Grafana dashboards]
  end

  OP -->|REST /platform/*| Service
  AG -->|ingest optional| Service
  CFG --> SU
  SU -->|/platform/ready| OP
  ND --> WIN
  ND --> LIN
  CE --> PE
  PE --> AU
  ST --> AU
  Service --> ST
  PROM --> PR
  PR --> Service
  GF --> PR
```

### Request path (correlation + remediation preview)

```mermaid
sequenceDiagram
  participant U as Operator
  participant API as FastAPI
  participant D as network_diagnostics
  participant C as correlation_engine
  participant P as policy
  participant A as audit JSONL

  U->>API: POST /platform/correlation/run
  API->>D: collect_observations (read-only)
  D-->>API: observations
  API->>C: correlate(signals)
  C->>P: evaluate (deterministic)
  P-->>C: PREVIEW / BLOCK / ALLOW
  C-->>API: evidence_tree + dry_run_only
  API->>A: append correlation_run
  API-->>U: JSON (no host mutation)
```

---

## Deployment diagram

```mermaid
flowchart LR
  subgraph Host["Docker host"]
    subgraph Compose["docker-compose.yml"]
      API[api :8000]
      PROM[prometheus :9090]
      GRAF[grafana :3001]
    end
    VOL[(platform_data volume)]
  end

  DEV[Developer browser] --> API
  DEV --> GRAF
  PROM -->|GET /metrics| API
  GRAF --> PROM
  API --> VOL
```

Optional extensions (dashboard, Loki, Promtail): `docker-compose.full.yml`.

---

## Module map

| Module | Responsibility |
|--------|----------------|
| `platform_core/settings.py` | Typed env + `.env` validation |
| `platform_core/startup_checks.py` | Dependency / filesystem / config checks |
| `platform_core/network_diagnostics/` | OS abstraction (Windows vs Linux) |
| `backend/main.py` | Lifespan, Prometheus `/metrics`, OpenAPI |
| `backend/platform_routes.py` | `/platform/health`, `/platform/ready`, correlation |
| `deploy/prometheus/` | Scrape config |
| `deploy/grafana/` | Dashboard provisioning |

---

## Health vs readiness

| Endpoint | Purpose | HTTP when unhealthy |
|----------|---------|---------------------|
| `GET /platform/health` | **Liveness** — process up, safety flags | Always 200 if reachable |
| `GET /platform/ready` | **Readiness** — startup checks passed | 503 with check details |
| `GET /metrics` | Prometheus scrape | 200 |

Docker `HEALTHCHECK` uses **liveness** (`/platform/health`). Orchestrators may gate traffic on **readiness** (`/platform/ready`).

---

## Related docs

- [production_deployment.md](production_deployment.md) — commands and env vars  
- [production_readiness.md](production_readiness.md) — safety checklist  
- [operator_safety.md](operator_safety.md) — human approval model  
