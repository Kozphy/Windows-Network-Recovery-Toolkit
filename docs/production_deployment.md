# Production deployment (Docker)

See also [architecture_service.md](architecture_service.md) for diagrams and module map.

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Copy `.env.example` → `.env` and set `PLATFORM_API_KEY` before any non-local exposure

## Core stack (api + Prometheus + Grafana)

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL | Notes |
|---------|-----|-------|
| API + OpenAPI | http://localhost:8000/docs | Bearer or `X-Operator-*` headers |
| Liveness | http://localhost:8000/platform/health | Docker HEALTHCHECK target |
| Readiness | http://localhost:8000/platform/ready | Fails 503 until startup checks pass |
| Prometheus | http://localhost:9090 | Scrapes `GET /metrics` |
| Grafana | http://localhost:3001 | Default `admin` / `$GRAFANA_ADMIN_PASSWORD` |

## Optional full stack

Dashboard, Loki, and Promtail:

```bash
docker compose -f docker-compose.yml -f docker-compose.full.yml up --build
```

## Configuration

Validated via `platform_core.settings.PlatformSettings`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `PLATFORM_SAFE_MODE` | `1` | Safety-first defaults |
| `PLATFORM_DATA_DIR` | `./platform_data` | Append-only JSONL root |
| `PLATFORM_API_KEY` | unset | Optional Bearer auth |
| `FAIL_FAST_ON_STARTUP` | `0` ( `1` in Docker ) | Exit if startup checks fail |
| `REQUIRE_PING_BINARY` | `0` ( `1` in Docker ) | Hard-fail without `ping` |
| `CORS_ALLOW_ORIGINS` | `*` | Tighten before production |

Loads from repo-root `.env` and/or `backend/.env`.

## Linux vs Windows agents

| Host | Diagnostics | Remediation |
|------|-------------|-------------|
| Linux / Debian / Ubuntu / WSL | `LinuxNetworkDiagnostics` (observe-only) | Not in Linux container |
| Windows endpoint | `WindowsNetworkDiagnostics` (WinINET/WinHTTP reads) | Policy-gated on agent; never automatic in API |

**Observation != proof** — Windows proxy reads remain heuristic until Sysmon/Procmon proof tiers are attached.

## Safety invariants

- No auto-repair containers or cron remediation jobs
- Execute routes default to `dry_run=True`
- Append-only audit under `PLATFORM_DATA_DIR`
- Policy `ALLOW` does not bypass typed confirmation for destructive actions
