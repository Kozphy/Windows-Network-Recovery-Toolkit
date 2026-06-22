# Observability

## Endpoints

| URL | Purpose |
|-----|---------|
| `GET /platform/health` | Liveness |
| `GET /platform/ready` | Readiness checks |
| `GET /platform/metrics` | JSON aggregates |
| `GET /platform/slo` | SLO snapshot |
| `GET /metrics` | Prometheus text |

## Prometheus gauges (JSONL-derived)

- `endpoint_events_total`
- `proxy_drift_incidents_total`
- `policy_decisions_total_{decision}`
- `evidence_level_total_{level}`
- `remediation_preview_total`
- `fleet_endpoints_total`
- `incidents_by_severity_total_{severity}`
- `audit_replay_success_total`
- `diagnosis_duration_seconds` (mean `detected_at − occurred_at` from signals)

Source: `platform_core/endpoint_observability.py`, merged in `backend/main.py` `/metrics`.

## Technology-risk pipeline metrics (Postgres + worker path)

Implemented in `backend/trisk_metrics.py`, merged into `GET /metrics`:

| Metric | Type | Purpose |
|--------|------|---------|
| `evidence_events_ingested_total` | counter | Ingest volume |
| `incidents_classified_total{classification}` | counter | Class histogram |
| `classification_latency_seconds` | histogram (sum/count) | Worker duration |
| `policy_decisions_total` | counter | Policy outcomes |
| `audit_chain_append_total` | counter | Dual-write appends |
| `audit_chain_verification_failures_total` | counter | Tamper detection |
| `human_review_queue_depth` | gauge | Review backlog |
| `unknown_classification_ratio` | gauge | Quality signal |
| `worker_jobs_total` / `worker_job_failures_total` | counter | Queue health |

**Production-shaped assets (portfolio):**

- `observability/prometheus/prometheus.yml` — scrape API `:8000/metrics`
- `observability/grafana/technology-risk-dashboard.json` — starter dashboard

**Gap:** No separate worker metrics port in compose; worker events flow through API counters in sync-test mode. Full OTel traces not implemented.

## Dashboard (`frontend/app/platform/`)

- Fleet health overview
- Incidents by severity (`/platform/incidents`)
- Evidence + policy (`/platform/evidence`, `/platform/policy`)
- SLO + evidence/policy distribution (`/platform/slo`)
- Replay (`/platform/replay`)

Docker: `docker compose up` → Grafana `:3001`, Prometheus scrapes API `:8000/metrics`.
