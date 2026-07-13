# Portfolio cleanup inventory (refactor/portfolio-cleanup)

**Base tip:** `Multi_Domain_Decision_Platform` @ `3cd0d46d` (pre-cleanup tag: `portfolio-pre-cleanup-v1`)  
**Scope:** Full portfolio — keep CLI, `src/platform_core`, FastAPI, Power BI, NiceGUI dashboard, audit, tests, portfolio docs. Simplify by archiving experiments.

**Pre-cleanup pytest:** 1744 passed, 5 skipped, **7 failed** (pre-existing `/v1` API contract gaps — not introduced by cleanup).

Legend: **tests** = imported under `tests/`; **kept** = used by `windows_network_toolkit/`, `src/`, `backend/`, or root `platform_core/` still on the main path.

---

## KEEP (mainline)

| Path | Why |
|------|-----|
| `windows_network_toolkit/` | Primary CLI, collectors, dashboard, storage |
| `src/platform_core/` | Canonical decision / governance / audit engine |
| `src/proxy_guard/`, `src/proxy_drift/` | Live Windows proxy path |
| `src/telemetry/`, `src/classification/`, `src/correlation/` | Proof / causation inputs |
| `src/cli.py` (+ mainline handlers) | Extended operator CLI |
| `backend/` | FastAPI (`wnrt-api`) |
| `analytics/`, `schemas/` | Power BI / warehouse |
| `tests/` | Safety + portfolio proof (minus archived suites) |
| `docs/` spine | START_HERE, PORTFOLIO, safety/epistemic, case studies, monitoring-dashboard |
| `case_studies/`, `real_evidence/`, `PORTFOLIO.md` | Interview artifacts |
| `config/`, `shared/`, `knowledge/`, `examples/`, `fixtures/` (non-market) | Policies + deterministic inputs |
| `toolkit/` | Thin CLI alias |
| `observability/` | Grafana/Prometheus story |
| `tools/`, `.github/`, `Makefile`, `pyproject.toml` | Build/CI |
| `evidence/` | Still imported by `backend/` / safety handlers |
| `platform_core/` (root) | Still imported by `backend/` — legacy but live |
| `proxy_reasoning/`, root `proxy_guard/` | Still on WNT / product_contract paths |
| `endpoint_agent/` | Imported by WNT read-only agent |
| `telemetry/` (root) | Used by root `proxy_guard` |
| `scripts/` | Operator wrappers (trim later) |
| `reports/`, `logs/` skeletons | `.gitignore` + samples |

---

## ARCHIVE (move under `archive/` — not deleted)

| Path | Why | Test impact |
|------|-----|-------------|
| `network_agent/` | Alternate FastAPI demo; not required for `python -m src` / WNT | No `from network_agent` in tests |
| `hybrid_frontend/` | UI for `network_agent` only | None |
| `labs/` | Index README only | None |
| `agent/` | Legacy classify/plan/execute | Own tests only → move with suite |
| `order_flow_simulator/` | Fintech FSM demo | Own tests + metrics path |
| `edge_device/` | Edge simulation lab | Own tests; strip `src/cli` edge cmds |
| `src/market_events/` | Market research signals | `tests/market_events/` + market adapter |
| `mcp_server/` | Optional MCP extras | `tests/mcp` if present |
| `proxy_attribution/` | Standalone attribution CLI | Own test module |

---

## DELETE (generated / empty only)

| Path | Why |
|------|-----|
| `demo-output/*` (generated), `*.egg-info`, local `mlflow.db` | Artifacts — already gitignored where configured |
| Empty leftover caches | `.pytest_tmp`, `.venv` stay local/ignored |

**Do not delete** root `platform_core/`, `evidence/`, `frontend/` in this pass without a follow-up migration PR (`frontend/` remains optional SaaS demo; NiceGUI dashboard is the monitoring keep).

---

## UNSURE (leave in place this pass)

| Path | Blocker |
|------|---------|
| Root `platform_core/` vs `src/platform_core/` | Backend still depends on root package |
| `failure_system/` | Fleet linkage lazy-import; portfolio narrative unclear |
| `frontend/` (Next.js) | Optional docker full-stack; not NiceGUI |
| `deploy/` | Heavy ops overlays |
| Parallel `src/platform`, `src/core`, … | Consolidation target — document, don’t mass-delete |

---

## Import / test verification (pre-move)

| Target | Imported by KEEP packages? | Mainline tests that import it |
|--------|----------------------------|-------------------------------|
| `network_agent/` | No (docstring only) | None |
| `hybrid_frontend/` | No | None |
| `labs/` | No | None |
| `agent/` | No | `test_classifier/planner/executor/verifier.py` → move with package |
| `order_flow_simulator/` | No (metrics read JSONL only) | `test_order_flow_simulator.py`; `test_toolkit_metrics` rewritten |
| `edge_device/` | Was `src/cli.py` only — **stripped** | `test_edge_reasoning.py` → move with package |
| `src/market_events/` | Was `MarketAdapter` — **rewritten** to load fixture JSON | `tests/market_events/` → move with package |
| `mcp_server/` | No | `tests/mcp/` → move with package |
| `proxy_attribution/` | No (distinct from `proxy_guard.attribution`) | `test_proxy_attribution.py` → move with package |

**Not archived this pass:** root `platform_core/`, `evidence/`, `proxy_reasoning/`, root `proxy_guard/`, `endpoint_agent/`, `frontend/`, `failure_system/`, dual `telemetry/`.

## Cleanup rules applied

1. Archive experiments under `archive/` with a README; exclude `archive/` from pytest collection.
2. Strip archived CLI entry points from `src/cli.py` when moving `edge_device`.
3. Soft-disable market adapter if `src.market_events` is archived.
4. No force-push to `main`; work only on `refactor/portfolio-cleanup`.
5. History preserved via tag `portfolio-pre-cleanup-v1` + commits.

## Status (2026-07-13)

- Branch: `refactor/portfolio-cleanup`
- Tag: `portfolio-pre-cleanup-v1`
- Pre-cleanup pytest: **1744 passed / 7 failed** (known `/v1` API gaps)
- **ARCHIVE packages moved** under `archive/` with dedicated tests; KEEP imports verified clean.
- Docs spine (`START_HERE`, `threat_model`, `docs/README`) point at `archive/`.
- Post-cleanup pytest: **1686 passed / 7 failed** (same `/v1` gaps); ~58 archived-suite tests excluded — parity with baseline.
