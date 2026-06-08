# Feature inventory

Maps platform capabilities to repository files and records gaps for **full Linux runtime** and **full cloud deploy**.

| Feature | Status | Primary entry points |
|---------|--------|----------------------|
| Linux | Partial | `platform_core/network_diagnostics/linux.py`, `src/proxy_guard/linux_proxy_snapshot.py` |
| Docker | Yes | `docker-compose.yml`, `Dockerfile`, `frontend/Dockerfile` |
| GitHub Actions | Yes | `.github/workflows/*.yml` |
| CI/CD | CI + GHCR image publish | `ci.yml`, `build.yml`, `Makefile` |
| Prometheus | Yes | `deploy/prometheus/`, `backend/prometheus_exporter.py`, `GET /metrics` |
| Grafana | Yes | `deploy/grafana/`, `docker-compose.yml` |
| Cloud | Design + local scale stack | `platform_core/fleet/`, `deploy/helm/`, `docker-compose.scale.yml` |

---

## Linux — partial

### What exists

| Area | Files |
|------|--------|
| OS detection & WSL | `platform_core/os_probe.py`, `platform_core/network_diagnostics/base.py` |
| Linux diagnostics (observe-only) | `platform_core/network_diagnostics/linux.py`, `platform_core/network_diagnostics/__init__.py` |
| Linux proxy snapshot collector (scaffold) | `src/proxy_guard/linux_proxy_snapshot.py`, `src/proxy_guard/linux_proxy_commands.py` |
| Generic fallback | `platform_core/network_diagnostics/generic.py` |
| Platform observations in correlation | `platform_core/correlation_engine.py` |
| Tests | `tests/test_os_probe.py`, `tests/test_network_diagnostics.py`, `tests/test_linux_proxy_snapshot.py` |
| Docs | `docs/production_deployment.md`, `docs/architecture_service.md` |
| CI on Linux | All workflows use `runs-on: ubuntu-latest` |

### Windows-only (not Linux runtime)

| Area | Files |
|------|--------|
| Sysmon / registry causation | `src/telemetry/sysmon_reader.py`, `src/correlation/proxy_causation.py`, `src/proxy_guard/proxy_watch.py` |
| Proxy guard / remediation | `src/proxy_guard/*` (except Linux snapshot scaffold) |
| Network recovery CLI | `src/network_recovery/cli_handlers.py`, `src/network_state/cli_handlers.py` |
| One-click launcher | `docs/one_click_run.md`, `scripts/start_everything_safe.ps1` |

### Missing for full Linux runtime

1. **Parity collectors** — gsettings/NM/apt probes exist as read-only scaffold; no live drift watcher equivalent to `proxy-watch`.
2. **Linux agent packaging** — No `.deb`/`.rpm`, systemd unit, or field-agent install path for bare-metal Linux.
3. **Proxy pipeline on live Linux** — Classification/policy/timeline work from fixtures; Sysmon causation remains Windows-only.
4. **Integration tests on real Linux hosts** — CI uses fixtures; optional `linux-smoke` job not yet wired.
5. **WSL bridge** — WSL is detected; no unified collector that merges Windows WinINET + Linux env in one view.
6. **Linux remediation** — Observe-only by design today; no policy-gated repair (e.g. `gsettings`, NetworkManager).

### Commands

```bash
python -m src proxy-linux-snapshot          # text summary
python -m src proxy-linux-snapshot --json   # structured JSON
```

---

## Docker — yes

| File | Role |
|------|------|
| `docker-compose.yml` | API + Prometheus + Grafana (`PLATFORM_FIXTURE_MODE=1`) |
| `docker-compose.full.yml` | Frontend dashboard, Loki, Promtail |
| `docker-compose.scale.yml` | Postgres, Redis, Redpanda for fleet ingest dev |
| `Dockerfile` | Multi-stage Python 3.11 API image |
| `frontend/Dockerfile` | Next.js dashboard image |
| `.env.example` | Compose env template |

### Optional hardening (not yet in repo)

- Production compose overrides (secrets, TLS, resource limits)
- Multi-arch builds (`linux/arm64`) in CI
- Linux **endpoint** container (today’s image is the platform API, not a field agent)

---

## GitHub Actions — yes

| Workflow | File | Purpose |
|----------|------|---------|
| Unified CI | `.github/workflows/ci.yml` | Lint, proxy pipeline tests, full pytest, frontend build |
| Tests | `.github/workflows/test.yml` | Ruff, pytest, coverage artifacts |
| Lint | `.github/workflows/lint.yml` | Ruff-focused |
| Build | `.github/workflows/build.yml` | Docker build + GHCR push |
| Security | `.github/workflows/security.yml` | `pip-audit`, scheduled scans |
| Templates | `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/*` | PR/issue hygiene |

---

## CI/CD — yes (CI + image publish; not full CD)

| Layer | Files |
|-------|--------|
| Local CI parity | `Makefile` (`test`, `lint`, `demo`, `replay-fixtures`) |
| Python packaging | `pyproject.toml` |
| Container registry CD | `.github/workflows/build.yml` → `ghcr.io/${{ github.repository }}` |
| JUnit artifacts | `ci.yml` → `reports/junit.xml` upload |
| Helm scaffold | `deploy/helm/erp-platform/` |

### Missing for full CD

- No `deploy.yml` (staging/prod rollout)
- No Terraform/Bicep/Pulumi in repo
- No environment promotion (dev → staging → prod)
- No post-deploy smoke tests against a live URL
- No release tagging / changelog automation

---

## Prometheus — yes

| File | Role |
|------|------|
| `docker-compose.yml` | `prometheus` service |
| `deploy/prometheus/prometheus.yml` | Scrape `api:8000/metrics` |
| `deploy/prometheus/alerts.yml` | Alert rules |
| `backend/prometheus_exporter.py` | Text exposition, labeled counters |
| `backend/main.py` | `GET /metrics` |
| `backend/platform_routes.py` | `GET /platform/metrics` |
| `backend/platform_fleet_routes.py` | Ingest metrics via `inc_labeled` |
| `backend/observability_metrics.py` | Pipeline metrics helpers |
| `platform_core/metrics.py` | Platform metric computation |
| `platform_core/sre/mttr.py` | `mttr_metrics_for_prometheus()` |
| `endpoint_agent/service_runner.py` | Agent-side metrics hooks |
| Tests | `tests/test_prometheus_exporter.py`, `tests/test_observability_metrics.py` |

### Missing (production observability)

- Prometheus remote write / federation
- Kubernetes ServiceMonitor
- OTel metrics pipeline (traces config exists at `deploy/otel/otel-collector-config.yaml`)

---

## Grafana — yes

| File | Role |
|------|------|
| `docker-compose.yml` | `grafana` service (port `3001`) |
| `deploy/grafana/provisioning/datasources/datasources.yml` | Prometheus datasource |
| `deploy/grafana/provisioning/dashboards/dashboards.yml` | Dashboard provisioning |
| `deploy/grafana/provisioning/dashboards/json/*.json` | Platform dashboards |
| `docker-compose.full.yml` | Loki + Promtail |
| `deploy/loki/loki-config.yml`, `deploy/promtail/promtail-config.yml` | Log stack |

### Missing

- Grafana Cloud / managed provisioning
- SSO beyond default `admin/admin`
- Fleet ingest dashboards (lag, dedup, partition skew)

---

## Cloud — partial / design only

### What exists

| Area | Files |
|------|--------|
| Local-first philosophy | `docs/adr/ADR-005-local-first-no-default-telemetry-upload.md` |
| SaaS extension contracts | `docs/extension_points_multi_host_saas.md` |
| Fleet scale architecture | `docs/architecture/fleet_scale_100k.md`, `docs/adr/ADR-008-fleet-scale-100k-endpoints.md` |
| Fleet ingest code | `platform_core/fleet/` |
| Fleet API | `backend/platform_fleet_routes.py` |
| Scale dev stack | `docker-compose.scale.yml` |
| OTel (dev) | `deploy/otel/otel-collector-config.yaml`, `backend/tracing.py` |
| DB schema | `platform_core/db/schema.sql`, `backend/schema.sql` |
| Container publish | `.github/workflows/build.yml` → GHCR |
| Endpoint agent (opt-in ingest) | `endpoint_agent/` |
| **Helm scaffold** | `deploy/helm/erp-platform/` |

### Explicitly not in repo

- No Terraform / Bicep / raw Kubernetes manifests outside Helm scaffold
- No AWS/Azure/GCP SDK modules (`docs/extension_points_multi_host_saas.md` non-goal)

### Missing for full cloud deploy

| Layer | What to add |
|-------|-------------|
| **IaC** | Terraform/Bicep for VPC, managed Postgres, Redis, Kafka, secrets |
| **K8s production** | HPA, ingress + TLS, PodDisruptionBudgets, network policies |
| **CD pipeline** | `deploy.yml`: build → push → `helm upgrade` per environment |
| **Secrets & identity** | Workload identity, vault-backed API keys |
| **Multi-tenant production** | OIDC/Entra, tenant isolation, regional ingest gateways |
| **Stream + store** | Managed Kafka/Redpanda, Postgres HA, S3/Blob cold audit |
| **Observability cloud** | Remote write, log shipping, distributed tracing |
| **Agent distribution** | Windows MSI + Linux package + auto-update channel |

---

## Quick verify

```bash
# Local stack (Docker)
docker compose up

# Linux proxy snapshot (works on Linux, macOS env reads, CI)
python -m src proxy-linux-snapshot --json

# Helm (requires cluster + kubectl)
helm upgrade --install erp deploy/helm/erp-platform -n erp --create-namespace

# CI parity
make test
```

---

## Suggested next steps

**Full Linux runtime (smallest wins):**

1. Extend `linux_proxy_snapshot.py` with drift detection and JSONL audit sink.
2. Install `endpoint_agent` via `deploy/linux/erp-endpoint-agent.service.example`.
3. Add `linux-smoke` CI job running `proxy-linux-snapshot` on Ubuntu.

**Full cloud deploy (smallest path):**

1. Harden `deploy/helm/erp-platform` (ingress, secrets, managed DB URLs).
2. Add `.github/workflows/deploy.yml` → GHCR → `helm upgrade`.
3. Wire `platform_core/fleet/ingestion.py` to a real Kafka/Redpanda publisher adapter.
4. Layer `docker-compose.scale.yml` services as managed cloud resources.
