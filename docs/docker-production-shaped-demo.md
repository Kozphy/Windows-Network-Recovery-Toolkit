# Docker production-shaped demo

Full local stack for senior portfolio review: **Postgres + Redis + API + RQ worker + Prometheus + Grafana**.

## Quick start

```powershell
make prod-demo-up
make prod-demo-health
```

## Services

| Service | Port | Role |
|---------|------|------|
| postgres | 5432 | Platform + decision intelligence + `trisk` schema (`03_trisk_schema.sql`) |
| redis | 6379 | RQ job queue |
| api | 8000 | FastAPI — `/platform/*`, `/trisk/*`, `/v1/*` |
| worker | — | `rq worker trisk` — async classification |
| prometheus | 9090 | Scrapes `GET /metrics` |
| grafana | 3001 | Dashboards (admin / env password) |

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRISK_DATABASE_URL` | postgres DSN | SQLModel persistence |
| `REDIS_URL` | `redis://redis:6379/0` | Queue |
| `QUEUE_BACKEND` | `rq` | Use RQ (CI uses `memory`) |
| `TRISK_SYNC_CLASSIFY` | `0` | Async via worker in compose |
| `TRISK_API_TOKEN` | `dev-trisk-token` | `/v1` demo auth |

## Ingest example

```powershell
curl -X POST http://127.0.0.1:8000/v1/evidence `
  -H "X-Api-Token: dev-trisk-token" `
  -H "X-Api-Role: operator" `
  -H "Content-Type: application/json" `
  -d '{"endpoint_id":"ep-1","source_event_id":"s1","evidence_type":"proxy_state","timestamp_utc":"2026-06-12T10:00:00Z","raw_snapshot":{"wininet_proxy_enabled":true,"wininet_proxy_server":"127.0.0.1:59081","winhttp_direct_access":true,"localhost_port":59081},"normalized_fields":{},"evidence_tier":"T1_STATE_EVIDENCE","limitations":["Triage only"]}'
```

## Lightweight alternative

`docker-compose.demo.yml` + `make demo-up` — API only, `DEMO_MODE`, no Postgres/Redis.

**Gaps:** not HA, not attested SLOs, demo tokens only — see [production-readiness-scorecard.md](production-readiness-scorecard.md).
