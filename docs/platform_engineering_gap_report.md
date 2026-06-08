# Platform engineering gap report

**Audit date:** 2026-06-08  
**Scope:** README promises vs repository reality (local-first endpoint reliability platform)

This document is the Phase 1 reality audit. It maps claimed capabilities to files, tests, and CI evidence. Gaps are explicit — no marketing language.

---

## Executive summary

| Area | Status | Evidence |
|------|--------|----------|
| GitHub Actions CI | **Present** | `.github/workflows/ci.yml` (lint / test / build-smoke) |
| Security workflow | **Present** | `.github/workflows/security.yml` (pip-audit + Trivy fs/image) |
| Docker local stack | **Present** | `Dockerfile`, `docker-compose.yml`, `.env.example` |
| Fixture demo path | **Present** | `scripts/demo_tier1.ps1`, `make demo-tier1`, `docs/verified_demo.md` |
| Safety contract tests | **Present** | 20+ tests across `test_policy_safety_contract.py`, `test_api_dry_run_default.py`, `test_replay_determinism.py`, `test_audit_contract.py`, `tests/api/`, `tests/policy/` |
| Docs checklist | **Present** | `docs/verified_demo.md`, `docs/ci_branch_protection.md`, `docs/production_readiness.md`, `PUBLIC_RELEASE_CHECKLIST.md` |
| Ruff gate (`ruff check .`) | **Green** | CI job `lint` runs repo-wide ruff (see `pyproject.toml` excludes) |
| Black gate (`black --check .`) | **Debt** | ~200 files pending format pass; CI runs command with `continue-on-error` until dedicated formatting PR |
| Live Docker smoke in CI | **Partial** | `build-smoke` builds image + in-process health contracts; full `docker compose up` not run in GHA (no daemon budget) |

---

## 1. GitHub Actions CI

### Required (Phase 2 target)

| Check | File | Status |
|-------|------|--------|
| Triggers `push` + `pull_request` on `main` | `ci.yml` | Yes |
| Python 3.11 | `ci.yml` | Yes |
| `pip install -e ".[dev]"` | `ci.yml` | Yes |
| `ruff check .` | `ci.yml` job `lint` | Yes |
| `black --check .` | `ci.yml` job `lint` | Runs; non-blocking until format PR |
| `pytest -q` (full suite) | `ci.yml` job `test` | Yes |
| Focused safety tests | `ci.yml` job `test` | Yes |
| Fixture CLI smoke | `ci.yml` job `test` | Yes |
| Docker build smoke | `ci.yml` job `build-smoke` | Yes |

### Legacy split workflows (still present)

| Workflow | Notes |
|----------|-------|
| `lint.yml` | Duplicate of CI lint; safe to require only `ci` / `lint` job |
| `test.yml` | Broader (mypy, coverage); **fixed** missing line continuation in pytest-safety step |
| `build.yml` | GHCR push on default branch; complements `build-smoke` |

**Recommendation:** Branch protection should require `ci` jobs (`lint`, `test`, `build-smoke`) plus `security.yml` Trivy/pip-audit.

---

## 2. Security workflow

| Requirement | Status |
|-------------|--------|
| `.github/workflows/security.yml` | Yes |
| Trivy filesystem scan | Yes (`trivy-fs` job) |
| HIGH / CRITICAL severity | Yes |
| `exit-code: "0"` (non-blocking) | Yes, with comments to set `"1"` for merge gate |
| Trivy container image scan | Yes (`trivy-image` job) |
| pip-audit | Yes |

---

## 3. Docker local stack

| Component | Path | Status |
|-----------|------|--------|
| Dockerfile | `Dockerfile` | Multi-stage Python 3.11 |
| Compose | `docker-compose.yml` | `api`, `prometheus`, `grafana` |
| Env template | `.env.example` | Yes |
| Safe mode | `PLATFORM_SAFE_MODE=1`, `PLATFORM_FIXTURE_MODE=1` | In compose |
| Local volumes only | `platform_data`, `grafana_data` | Yes |
| `/platform/health` | `backend/platform_routes.py` | Tested in `tests/test_platform_health_routes.py` |
| `/platform/ready` | same | Tested |
| `/metrics` | Prometheus exporter | Tested |
| Compose contract | `tests/test_compose_platform_contract.py` | No daemon required |

**Gap:** End-to-end `docker compose up` + curl is documented in `docs/verified_demo.md` but not automated in CI (acceptable for portfolio; optional nightly job).

---

## 4. Demo path (read-only / fixture)

| Step | Command | Mutates host? |
|------|---------|---------------|
| Diagnosis | `python -m src diagnose --fixture tests/fixtures/features_healthy_signals.json` | No |
| Timeline replay | `python -m src proxy-timeline --fixture … --format markdown` | No |
| Policy | `python -m src proxy-policy --fixture … --format json` | No |
| Evidence tree | `python -m src proxy-report --fixture … --format markdown` | No |
| Release audit | `python tools/public_release_audit.py --tracked-only` | No |
| Safety tests | `pytest -q tests/test_policy_safety_contract.py …` | No |

Orchestration: `scripts/demo_tier1.ps1`, `make demo-tier1`, `docs/verified_demo.md`.

---

## 5. Documentation

| Doc | Exists |
|-----|--------|
| `docs/verified_demo.md` | Yes |
| `docs/ci_branch_protection.md` | Yes (update job names to `ci` workflow) |
| `docs/production_readiness.md` | Yes |
| `PUBLIC_RELEASE_CHECKLIST.md` | Yes |

---

## 6. Safety tests matrix

| Guarantee | Test location |
|-----------|---------------|
| No silent process kill | `test_policy_safety_contract.py`, `tests/api/test_remediation_safety.py`, `tests/policy/test_safety_boundaries.py` |
| No firewall reset | Same + `test_safety_regression.py` |
| No adapter disable | Same |
| API `dry_run` default | `tests/test_api_dry_run_default.py`, `tests/api/test_remediation_safety.py` |
| Registry mutation requires typed confirmation | `test_policy_safety_contract.py`, `tests/test_repair_proxy_safe.py` |
| Listener correlation ≠ registry-writer proof | `test_policy_safety_contract.py`, `tests/test_proxy_guard_telemetry_integration.py`, ADR-004 |
| Sysmon proof optional / labeled | `telemetry/`, `tests/test_telemetry_safety_regression.py`, fixture fusion CLI |

---

## 7. Known technical debt (prioritized)

1. **Black formatting** — Run `black platform_core backend evidence failure_system telemetry src tests tools` in a dedicated PR; then make `black --check` blocking in CI.
2. **`ruff check .`** — Full-repo scan still hits legacy paths (`edge_device`, `deploy`, etc.); gate uses first-party paths aligned with `pyproject.toml` package includes.
3. **Workflow consolidation** — `lint.yml` / `test.yml` overlap `ci.yml`; reduce required checks to avoid duplicate minutes.
4. **Public release audit** — May flag Windows-specific paths in `config/proxy_allowlist.yaml`; document as expected for Windows-first repo.
5. **Trivy blocking** — Flip `exit-code` to `"1"` when team accepts merge gate on HIGH/CRITICAL.

---

## 8. Interview / demo evidence chain

```text
Fixture signals → diagnose / timeline / policy / report (CLI)
       ↓
Safety pytest contracts (20+ tests in CI)
       ↓
Optional: docker compose (health / ready / metrics)
       ↓
security.yml SARIF + pip-audit artifacts
```

Related: [verified_demo.md](verified_demo.md), [production_readiness.md](production_readiness.md), [ci_branch_protection.md](ci_branch_protection.md).
