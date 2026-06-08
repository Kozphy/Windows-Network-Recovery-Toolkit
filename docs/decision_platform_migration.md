# Migration Plan — Multi-Domain Decision Intelligence Platform

## Phase 0 — Baseline (complete)

- [x] Unified models: `platform_core/decision_platform/models.py`
- [x] Shared engine bridge: `platform_core/decision_platform/reasoning.py` → `src.decision_engine`
- [x] Five domain adapters + registry
- [x] Decision Intelligence API (`/decision-intelligence/*`)
- [x] Outcome learning + Prometheus metrics

## Phase 1 — Adapter wiring (next)

1. **Windows** — Route `python -m src proxy-policy` fixture output through `WindowsAdapter` (read-only shim; no CLI rename).
2. **Market** — Map `src.market_events` calendar rows to API `POST /events` via `MarketAdapter`.
3. **Security** — Ingest SIEM-style JSON fixtures into `SecurityAdapter` observations.

Deliverable: `platform_core/decision_platform/ingest.py` helpers that call existing CLIs/fixtures without breaking them.

## Phase 2 — API domain routes

Add optional query param `domain=windows|security|...` on:

- `POST /decision-intelligence/evaluate` — runs adapter + shared engine
- `GET /decision-intelligence/domains` — lists registry

Map API persistence columns to `PlatformDomain` enum (extend `di_events.domain` values).

## Phase 3 — Knowledge layer integration

- Load `src/knowledge/` YAML common causes into adapter `derive_evidence()` for Windows + Security.
- Bump `knowledge_version` in audit rows when evidence drivers change.

## Phase 4 — Legacy alias deprecation

| Legacy | Target |
|--------|--------|
| `platform_core.decision_domain.DecisionDomain.ENDPOINT_RELIABILITY` | `PlatformDomain.WINDOWS` |
| `decision_domain.DecisionOutcome` (expected) | `decision_platform.Decision` |
| `outcome_learning.DecisionOutcome` (recorded) | `decision_platform.Outcome` |

Keep aliases for one release; document in OpenAPI.

## Phase 5 — PostgreSQL views + Grafana

- Materialized view `di_domain_metrics` for per-domain accuracy.
- Grafana row per domain on **Decision Intelligence** dashboard.

## Risk controls

- No automatic remediation from adapter output — policy gates unchanged.
- Replay digests must match before promoting scoring constant changes.
- Each phase ships with pytest + fixture replay; zero skip on Windows CI preserved.

## Success criteria

- All five domains produce `DomainPipelineResult` via `get_adapter(domain).evaluate()`.
- Same `engine_digest` algorithm across domains for identical evidence/candidate inputs.
- Outcome learning `decision_accuracy` visible in Grafana per domain.
