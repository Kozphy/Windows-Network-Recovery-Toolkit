# Platform Consolidation Inventory (Phase 1)

**Goal:** One Multi-Domain Decision Platform — multiple domains, one pipeline.

## KEEP / MERGE / DEPRECATE

| Component | Action | Canonical target | Legacy location(s) |
|-----------|--------|------------------|-------------------|
| **NormalizedEvent** | **MERGE → KEEP** | `src/platform/models.py` | `src/core/event.py`, `backend/decision_intelligence/models.EventCreate`, `platform_core/decision_platform/models.Observation` (map via shim) |
| **EvidenceItem** | **MERGE → KEEP** | `src/platform/models.py` | `src/core/evidence.py`, `platform_core/decision_platform/models.Evidence`, `platform_core/evidence_model` (Windows tiers — **KEEP** separate for endpoint reliability) |
| **Hypothesis** | **MERGE → KEEP** | `src/platform/models.py` | `src/core/decision.py`, `platform_core/reliability/models.RankedHypothesis`, `proxy_reasoning/models.ProxyHypothesis` |
| **DecisionOption** | **MERGE → KEEP** | `src/platform/models.py` | `src/core/decision.py`, `platform_core/decision_platform/models.Decision`, `src/decision_engine/scoring.py` |
| **DecisionOutcome** | **MERGE → KEEP** | `src/platform/models.py` | `src/core/outcome.py`, `platform_core/outcome_learning/models`, `backend/decision_intelligence` outcome records |
| **PolicyDecision** | **KEEP (new canonical)** | `src/platform/models.py` | `platform_core/policy_model.py`, `platform_core/policy/engine.StructuredPolicyDecision` (endpoint — **KEEP** for remediation) |
| **Evidence engine** | **MERGE** | `src/platform/evidence_engine.py` | `src/core/evidence_engine.py` |
| **Decision engine** | **MERGE** | `src/platform/decision_engine.py` | `src/core/decision_engine.py`, `platform_core/decision_platform/reasoning.py`, `src/decision_engine/scoring.py` (Windows live — **KEEP** shim) |
| **Policy engine (MDP)** | **MERGE** | `src/platform/policy_engine.py` | `src/core/policy_engine.py`, `platform_core/policy_model.evaluate_endpoint_policy` |
| **Outcome engine** | **MERGE** | `src/platform/outcome_engine.py` | `src/core/outcome_engine.py`, `platform_core/outcome_learning/learning.py` |
| **Audit (MDP)** | **MERGE** | `src/platform/audit.py` | `src/core/audit.py`, `backend/decision_intelligence` store audit |
| **Replay (MDP)** | **MERGE** | `src/platform/replay.py` | `src/core/replay.py`, `platform_core/replay/runner.py` (remediation — **KEEP**), `platform_core/reasoning_audit.py` (endpoint — **KEEP**) |
| **Pipeline** | **KEEP** | `src/platform/pipeline.py` | `src/core/replay.run_pipeline`, `platform_core/decision_platform/adapter.evaluate` |
| **Domain adapters** | **MERGE** | `src/platform/domains/` | `src/domains/`, `platform_core/decision_platform/adapters/` |
| **CLI handlers** | **MERGE** | `src/platform_handlers.py` → imports `src.platform` | unchanged entrypoint |
| **FastAPI MDP routes** | **KEEP (new)** | `backend/platform_mdp_routes.py` | `backend/decision_intelligence/routes.py` (**DEPRECATE** delegate to pipeline) |
| **Endpoint reasoning** | **KEEP** | `platform_core/reasoning_engine.py` | Windows proxy/final-causation — not replaced |
| **Remediation policy** | **KEEP** | `platform_core/policy/engine.py` | Executes preview/dry-run gates |
| **Windows evidence tiers** | **KEEP** | `platform_core/evidence_model.py` | OBSERVED_ONLY … FINAL_CAUSATION |

## Duplicate systems summary

| Duplicate | Count | Resolution |
|-----------|-------|------------|
| Event models | 4+ | Canonical `NormalizedEvent`; shims + migration table |
| Evidence models | 3+ MDP + 1 Windows tier model | MDP unified; Windows tiers retained |
| Hypothesis models | 5+ | Canonical `Hypothesis` for MDP |
| Decision models | 4+ | Canonical `DecisionOption` |
| Replay engines | 4 | MDP: one replay; endpoint/remediation replay unchanged |
| Policy engines | 3 | MDP: `src/platform/policy_engine`; remediation: `platform_core/policy` |

## Migration table (old → canonical)

| Legacy type | Canonical type | Shim module |
|-------------|----------------|-------------|
| `src.core.event.NormalizedEvent` | `src.platform.models.NormalizedEvent` | `src/core/event.py` |
| `src.core.evidence.EvidenceItem` | `src.platform.models.EvidenceItem` | `src/core/evidence.py` |
| `platform_core.decision_platform.models.Observation` | Map fields → `NormalizedEvent.observations[]` | `src/platform/compat/decision_platform_shim.py` |
| `platform_core.decision_platform.models.Evidence` | `EvidenceItem` | shim `evidence_from_legacy` |
| `platform_core.decision_platform.models.Decision` | `DecisionOption` | shim `decision_from_legacy` |
| `platform_core.decision_platform.models.Outcome` | `DecisionOutcome` | shim `outcome_from_legacy` |
| `platform_core.outcome_learning.models.OutcomeEvaluation` | metrics via `outcome_engine` | `platform_core/outcome_learning/learning.py` re-export |
