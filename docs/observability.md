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

## Dashboard (`frontend/app/platform/`)

- Fleet health overview
- Incidents by severity (`/platform/incidents`)
- Evidence + policy (`/platform/evidence`, `/platform/policy`)
- SLO + evidence/policy distribution (`/platform/slo`)
- Replay (`/platform/replay`)

Docker: `docker compose up` → Grafana `:3001`, Prometheus scrapes API `:8000/metrics`.
