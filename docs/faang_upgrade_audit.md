# FAANG-tier upgrade audit

**Project:** Windows Network Recovery Toolkit / Endpoint Reliability Platform  
**Audit date:** 2026-06-04  
**Scope:** Repository-wide structure, safety model, platform API, replay, tests, tooling  
**Status:** Phase 1 baseline — no deletions performed

---

## Executive summary

The repository is a **mature solo prototype** with unusually strong safety narrative and multiple overlapping subsystems. Core platform pieces (`platform_core/`, `backend/platform_routes.py`, append-only JSONL, policy registry, replay harness) are **portfolio-ready with targeted hardening**. The main gaps are **tooling/CI drift**, **package duplication** (`src/proxy_guard` vs top-level `proxy_guard`), **partial schema unification**, and **missing centralized safety regression suite** (addressed in Phase 3).

---

## Repository map

| Area | Primary paths | Role |
|------|---------------|------|
| CLI (`python -m src`) | `src/cli.py`, `src/command_handlers*.py`, `scripts/*.bat` | Operator diagnostics, proxy guard, live hypothesis, repair previews |
| Policy engine | `platform_core/policy/`, `platform_core/policy_engine.py`, `platform_core/remediation_registry.py`, `src/policy/` | ALLOW/PREVIEW/BLOCK gates, risk tiers, confirmation phrases |
| Proxy diagnosis | `src/proxy_guard/`, `src/proxy_investigation/`, `proxy_guard/` (legacy) | WinINET/WinHTTP probes, watch, investigation bundles |
| Proxy guard / remediation | `src/proxy_guard/remediation.py`, `stop_listener.py`, `stop_reverter.py` | Typed-confirmation registry mutations, soak validation |
| Audit / JSONL | `platform_core/audit.py`, `platform_core/storage.py`, `src/core/jsonl.py`, `logs/*.jsonl` | Append-only audit tails, platform_data JSONL |
| Replay | `platform_core/replay/runner.py`, `src/decision_engine/live_replay.py` | Deterministic policy re-evaluation from stored events |
| Reasoning core | `platform_core/reasoning_models.py`, `platform_core/reasoning_engine.py` | Observation → event → hypothesis → proof separation |
| FastAPI backend | `backend/main.py`, `backend/platform_routes.py`, `backend/live_observability.py` | `/platform/*`, SaaS demo routes, JWT billing surface |
| Next.js frontend | `frontend/` | Dashboard demo (Supabase, charts) |
| Failure knowledge | `failure_system/` | Read-only failure blocks, generator, CLI |
| Evidence / proof | `evidence/`, `src/proof/` | Registry writer proof, Sysmon/Procmon adapters |
| Edge / agent demos | `edge_device/`, `endpoint_agent/`, `network_agent/` | Fleet ingest, heartbeat, optional upload |
| Tests | `tests/` (525+ cases) | Broad coverage; safety not centralized until Phase 3 |

---

## Classification by area

### CLI (`src/cli.py`, handlers, `.bat` scripts)

| Verdict | **Solid** (feature-rich) + **needs refactor** (surface area) |
|---------|------------------------------------------------------------------|
| Strengths | Large command matrix; dry-run defaults on destructive paths; beginner `.bat` wrappers preserved; recent `proxy-investigate`, stop-reverter/listener flows |
| Gaps | `cli.py` is ~2k lines; handler logic split across `command_handlers.py`, `command_handlers_safety.py`, proxy modules; argparse duplication |
| Risk | Live mutation paths exist but gated — regression risk if new commands bypass confirmation helpers |
| Dead-code candidates | Overlapping proxy entrypoints (`proxy_guard/` package vs `src/proxy_guard/`) |

### Policy engine

| Verdict | **Solid** |
|---------|-----------|
| Strengths | `remediation_registry.py` is canonical allowlist; `policy/classic.py` + `policy/engine.py` split preview vs execute; forbidden tiers for kill/firewall/adapter/arbitrary shell; header RBAC in `platform_core/rbac.py` |
| Gaps | Two policy vocabularies (`src/policy/hypothesis_gates.py` vs `platform_core/policy`); `policy_v2.py` / `policy_engine.py` overlap naming |
| Production hardening | Idempotency keys, request-id middleware, unified OpenAPI models (Phase 5) |

### Proxy diagnosis & guard

| Verdict | **Solid** (depth) + **duplicate / dead code candidate** |
|---------|-----------------------------------------------------------|
| Strengths | Structured evidence, causality labels, soak tests, investigation bundle, operator language |
| Gaps | Duplicate trees: `proxy_guard/` (legacy) and `src/proxy_guard/` (active); some attribution modules overlap `evidence/` |
| Unsafe / risky | Process kill and registry writes **exist** but require Admin + typed confirmation — document clearly; never auto-run |
| Production hardening | Single import surface; consolidate attribution under `evidence/` |

### Audit / JSONL logs

| Verdict | **Solid** (local-first) + **needs refactor** (many filenames) |
|---------|----------------------------------------------------------------|
| Strengths | Append-only pattern; `platform_core/audit.write_audit`; privacy redaction module |
| Gaps | Multiple audit files (`safety_audit.jsonl`, `decision_audit.jsonl`, `proxy_guard.jsonl`, platform_data/*); v1→v2 migration script exists but not universal |
| Production hardening | Schema versioning enforced at write boundary; support bundle export (Phase 8) |

### Replay

| Verdict | **Solid** |
|---------|-----------|
| Strengths | `platform_core/replay/runner.py` re-evaluates policy without subprocess; `/platform/replay/preview` API; live replay shims |
| Gaps | Multiple replay entrypoints; not all CLI paths emit replay-compatible envelopes |
| Production hardening | Golden fixture corpus + determinism metric (Phase 11) |

### FastAPI backend

| Verdict | **Solid** (demo) + **missing production hardening** |
|---------|------------------------------------------------------|
| Strengths | `/platform/*` routes; RBAC headers; dry-run default on execute; allowlisted `.bat` only; audit on preview/execute |
| Gaps | Permissive CORS; JWT + Stripe demo mixed with platform; no request-id / idempotency middleware yet; `requirements.txt` at repo root missing (CI broken) |
| Unsafe / risky | Subprocess spawn path exists for allowlisted scripts — correctly gated but must stay behind env + policy |
| Duplicate candidates | `backend/engine.py` heuristic classifier vs platform reasoning engine |

### Next.js frontend

| Verdict | **Needs refactor** + **missing production hardening** |
|---------|--------------------------------------------------------|
| Strengths | Next 14 app; charting; pairs with backend demos |
| Gaps | Not wired to all `/platform/*` contracts; Supabase optional; no CI job |
| Note | Portfolio demo — honest “prototype dashboard” labeling appropriate |

### Tests

| Verdict | **Solid** (breadth) + **missing production hardening** (safety matrix) |
|---------|--------------------------------------------------------------------------|
| Strengths | 525+ tests; API route tests; proxy guard enterprise tests; registry writer proof tests |
| Gaps | No dedicated `tests/policy/`, `tests/api/`, `tests/replay/` safety suites until Phase 3; CI references missing root `requirements.txt` |
| Production hardening | Pre-commit, ruff/black/mypy, safety regression gates (Phase 2–3) |

### Reasoning / event-state core

| Verdict | **Solid** (models exist) + **needs refactor** (wiring) |
|---------|----------------------------------------------------------|
| Strengths | `platform_core/reasoning_models.py` defines Observation, Event, StateTransition, Hypothesis, ProofResult, PolicyDecision fields |
| Gaps | Not all CLI/API outputs use v2 envelope; legacy JSON still emitted alongside |
| Phase 4 | Unify exports with `schema_version`, dual legacy/v2 compatibility |

### Evidence / proof layer

| Verdict | **Solid** |
|---------|-----------|
| Strengths | `evidence/registry_writer_proof.py`, Sysmon/Procmon adapters; tests prove UNAVAILABLE vs proof_candidate; explicit “correlation ≠ proof” language |
| Gaps | User-requested `evidence/sysmon_adapter.py` split vs consolidated `evidence/sysmon_eventlog.py` — thin adapter wrappers recommended |
| Production hardening | Fixture-driven CI only (no live Sysmon) — already mostly true |

### Fleet / multi-host demo

| Verdict | **Solid** (prototype) |
|---------|------------------------|
| Strengths | `platform_core/fleet.py`, ingest routes, metrics, incidents, demo seed patterns |
| Gaps | Opt-in agent upload documented but scattered; dashboard parity incomplete |

### Documentation

| Verdict | **Solid** (volume) + **needs refactor** (Phase 9 consolidation) |
|---------|-------------------------------------------------------------------|
| Strengths | Rich docs: architecture, safety, proxy investigation, CLI reference, case studies |
| Gaps | FAANG system design pack not yet unified; README positioning upgrade pending Phase 10 |

### Tooling / CI

| Verdict | **Missing production hardening** |
|---------|----------------------------------|
| Issues | No `pyproject.toml`; no pre-commit; CI installs nonexistent root `requirements.txt`; triggers only `main`/`master` while active branch is `amd_version` |
| Phase 2 | Add ruff, black, mypy (scoped), pre-commit, fixed CI |

---

## Safety model assessment

| Principle | Implementation status |
|-----------|------------------------|
| Diagnose before repair | **Met** — investigate/diagnose commands default read-only |
| Observation ≠ proof | **Met** — causality labels, registry writer proof statuses |
| No silent process kill | **Met** — `process_kill_forbidden`; CLI kill paths require confirmation + Admin |
| No silent firewall reset | **Met** — `firewall_reset_manual_only`; high/forbidden tiers |
| No silent adapter disable | **Met** — `adapter_disable_forbidden` |
| No registry mutation without confirmation | **Met** — typed phrases in registry + `validate_confirmation_phrase` |
| Remediation dry-run by default | **Met** — API `ExecuteIn.dry_run=True`; CLI `--dry-run` patterns |
| ALLOW / PREVIEW / BLOCK gates | **Met** — structured policy engine + classic registry |
| Beginner `.bat` preserved | **Met** — `scripts/` untouched |

---

## Duplicate / dead code candidates (do not delete yet)

1. **`proxy_guard/` (top-level)** vs **`src/proxy_guard/`** — prefer `src` for CLI; legacy package may still be imported by scripts.
2. **`platform_core/policy_v2.py`** vs **`platform_core/policy/engine.py`** — reconcile naming.
3. **`proxy_attribution/`** vs **`src/proxy_guard/*attribution*`** vs **`evidence/`** — merge toward `evidence/`.
4. **`hybrid_frontend/`** vs **`frontend/`** — static HTML demo vs Next.js.
5. **`network_agent/`** vs **`endpoint_agent/`** — overlapping ingest narratives.

---

## Recommended upgrade sequence

| Phase | Focus | Priority |
|-------|--------|----------|
| 1 | This audit | Done |
| 2 | Quality gates (ruff, black, mypy, pre-commit, CI) | **Now** |
| 3 | Safety regression tests | **Now** |
| 4 | Reasoning core unification | Next |
| 5 | API hardening (request-id, idempotency, RBAC docs) | Next |
| 6 | Telemetry proof adapters | Next |
| 7 | Fleet demo polish | Medium |
| 8 | Support bundle + redaction CLI | Medium |
| 9 | Documentation pack | Medium |
| 10 | README positioning | Medium |
| 11 | Benchmark script | Low |
| 12 | Final deliverables / resume bullets | After above |

---

## Immediate risks

1. **CI false green/red** — missing root requirements file; branch filter may skip PRs on `amd_version`.
2. **Policy drift** — new remediation keys added without registry + safety tests.
3. **Duplicate modules** — engineers may patch the wrong `proxy_guard` tree.
4. **Mixed auth models** — JWT SaaS routes vs header RBAC on `/platform/*` need clear docs to avoid accidental exposure.

---

## Phase 2–3 actions (this PR)

- Add `pyproject.toml`, `.pre-commit-config.yaml`, fix `.github/workflows/ci.yml`
- Add `tests/policy/test_safety_boundaries.py`, `tests/api/test_remediation_safety.py`, `tests/replay/test_replay_determinism.py`
- Expand `requirements-dev.txt` with lint/type tools

No runtime behavior changes intended in Phases 2–3 beyond test-enforced guarantees.
