# Enterprise Decision Platform — Migration Plan

## Phase 0 — Baseline (complete)

Existing assets reused without rebuild:

| Asset | Path | Role |
|-------|------|------|
| Evidence ingest | `backend/v1_routes.py` | Legacy `/v1/evidence` |
| Classifier worker | `backend/workers/classifier_worker.py` | Async RQ classification |
| Policy engine | `src/platform_core/policy/engine.py` | Canonical gates |
| Governance | `src/platform_core/governance/*` | Human review, audit reports |
| Domain events | `src/platform_core/events/` | Event sourcing |

## Phase 1 — Schema (this release)

1. Apply `backend/db/enterprise_schema.sql` (Docker init `04_enterprise_schema.sql`)
2. SQLModel `create_all` creates tables for SQLite dev/tests
3. Seed tenant `default`

**Tables added:** `trisk_tenants`, `trisk_observations`, `trisk_hypotheses`, `trisk_platform_decisions`, `trisk_policy_packs`, `trisk_audit_logs`

**Columns added:** `tenant_id` on `trisk_evidence_events`, `trisk_incidents`

## Phase 2 — Service layer (this release)

Package: `backend/services/`

Wire `POST /v1/enterprise/pipeline/run` as the canonical decision loop entry point.

## Phase 3 — Client migration

| From | To | Notes |
|------|-----|-------|
| `POST /v1/evidence` only | `POST /v1/enterprise/pipeline/run` | Full loop + audit |
| `/trisk/*` fixture reads | `/v1/enterprise/reports/*` | Tenant-scoped |
| JSONL human review only | `POST /v1/enterprise/reviews/{id}/approve` | DB + audit log |
| Static YAML in repo | `POST /v1/enterprise/policy/packs` | Per-tenant packs |

Keep `/v1/*` and `/trisk/*` during transition — no breaking changes.

## Phase 4 — Multi-tenant hardening (next)

- [ ] Row-level security policies in PostgreSQL
- [ ] Bind `tenant_id` in classifier worker from ingest metadata
- [ ] Per-tenant `PLATFORM_DATA_DIR` partition
- [ ] OAuth/Entra ID replacing static `X-Api-Token`

## Phase 5 — Operations (next)

- [ ] Scheduled governance report generation
- [ ] Prometheus counters per service (`enterprise_pipeline_runs_total`)
- [ ] Audit log archival to WORM object store
- [ ] OpenAPI client SDK generation in CI

## Rollback

1. Remove `enterprise_router` include from `backend/main.py`
2. Enterprise tables are additive — no drops required
3. `/v1` and `/trisk` routes unaffected

## Validation

```powershell
ruff check backend/services backend/decision_platform_routes.py
pytest -q tests/backend/test_enterprise_api.py tests/backend/test_policy_yaml.py
```

Full regression: `pytest -q` (all existing tests must pass).
