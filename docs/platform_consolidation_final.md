# Platform Consolidation — Final Report (Phase 12)

## 1. Files created

| Path | Role |
|------|------|
| `src/platform/models.py` | Canonical models |
| `src/platform/pipeline.py` | Public pipeline entry |
| `src/platform/replay.py` | Unified replay + `run_pipeline` |
| `src/platform/evidence_engine.py` | Shared evidence fusion |
| `src/platform/decision_engine.py` | Shared decision scoring |
| `src/platform/policy_engine.py` | Shared policy guardrails |
| `src/platform/outcome_engine.py` | Shared outcome metrics |
| `src/platform/audit.py` | Single JSONL audit format |
| `src/platform/serialization.py` | Deterministic JSON hashes |
| `src/platform/registry.py` | Domain registry |
| `src/platform/domains/*` | Five domain adapters (collect + evidence only) |
| `src/platform/compat/decision_platform_shim.py` | Legacy model mapping |
| `backend/platform_mdp_routes.py` | FastAPI `/platform/decision/*` |
| `docs/platform_consolidation_inventory.md` | Phase 1 inventory |
| `tests/test_platform_*.py` | Consolidation tests |

## 2. Files deprecated (shims, not deleted)

| Path | Shim target |
|------|-------------|
| `src/core/event.py`, `evidence.py`, `decision.py`, … | `src.platform.*` |
| `src/domains/*` | `src.platform.domains.*` |
| `platform_core/decision_platform/` | Docstring deprecation; use `src.platform` |
| `platform_core/outcome_learning/` | Docstring deprecation; use `src.platform.outcome_engine` |
| `backend/decision_intelligence/` | Retained; migrate callers to `/platform/decision/*` |

**Unchanged (endpoint reliability):** `platform_core/reasoning_engine.py`, `platform_core/evidence_model.py`, `platform_core/policy/engine.py`, `src/proxy_guard/`, beginner scripts.

## 3. Architecture before

```text
Parallel stacks:
  platform_core/decision_platform  +  src/core  +  decision_intelligence API
  platform_core/outcome_learning
  platform_core/reasoning_engine (Windows endpoint)
```

## 4. Architecture after

```text
                    ┌─────────────────────────────────────┐
                    │         src/platform/ (canonical)    │
                    │  models → pipeline → engines → audit │
                    └──────────────────┬──────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              v                        v                        v
    src/platform/domains/     python -m src platform    /platform/decision/*
    (windows…market)            CLI handlers              FastAPI routes
              │
              v
    tests/fixtures/domains/*.json

    [legacy shims] src/core, src/domains, platform_core/decision_platform

    [unchanged] platform_core/reasoning_engine → Windows endpoint reliability
```

**Pipeline:** Event → Evidence → Hypothesis → Decision → Policy → Outcome → Audit → Replay → Learning

## 5. Migration risks

| Risk | Mitigation |
|------|------------|
| Duplicate `/platform/events` semantics | MDP API at `/platform/decision/events` |
| Audit path change | `logs/platform_decision_audit.jsonl` (old `multi_domain_audit` via shim) |
| Import paths | `src/core/*` re-exports with `DeprecationWarning` |
| `decision_intelligence` API drift | Keep module; document migration to MDP routes |
| Tests importing old paths | Shims preserve behavior |

## 6. Test results

Run: `python -m pytest -q tests/test_platform_pipeline.py tests/test_platform_policy.py tests/test_platform_outcome.py tests/test_platform_replay.py tests/test_multi_domain_platform.py`

Full suite: `python -m pytest -q`

## 7. Remaining technical debt

- Merge `backend/decision_intelligence` service layer onto `src.platform.replay.run_pipeline`
- Add `test_multi_domain_platform` + `test_platform_*` to CI explicitly
- Optional: redirect `/decision-intelligence/*` to `/platform/decision/*`
- Windows live collectors should feed `NormalizedEvent` (today: fixtures for MDP domains)
- Single audit path migration tool for old JSONL files
