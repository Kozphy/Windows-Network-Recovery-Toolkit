# Deployment Topology

## Stacks

| Stack | Compose file | Services | Use case |
|-------|--------------|----------|----------|
| Reviewer demo | `docker-compose.demo.yml` | API only (`DEMO_MODE`) | Hiring panels, read-only |
| Production-shaped | `docker-compose.yml` | API, Postgres, Redis, worker, Prometheus, Grafana | Senior portfolio demo |
| CD overlay | `docker-compose.prod.yml` | Pull immutable API image | Documented only — not required locally |

## Ports (production-shaped)

| Service | Port | Health |
|---------|------|--------|
| API | 8000 | `GET /trisk/health`, `GET /v1/evidence` (auth) |
| Postgres | 5432 | `pg_isready` |
| Redis | 6379 | `redis-cli ping` |
| Prometheus | 9090 | `/-/healthy` |
| Grafana | 3001 | UI login |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `TRISK_DATABASE_URL` | SQLModel engine URL (defaults to Postgres in compose) |
| `REDIS_URL` | RQ broker |
| `QUEUE_BACKEND` | `rq` or `memory` (tests) |
| `PLATFORM_SAFE_MODE` | Blocks destructive API paths |
| `DEMO_MODE` | Fixture-only reviewer stack |

## Volumes

- `pg_data` — Postgres persistence
- `platform_data` — JSONL audit mirror
- Grafana provisioning from `deploy/grafana/` and `observability/grafana/`

## Not in scope

- Multi-region HA
- Kubernetes manifests (Helm stub exists under `deploy/helm/` for ERP platform — separate from trisk tables)
- Enterprise SSO (documented gap in [rbac-model.md](rbac-model.md))
