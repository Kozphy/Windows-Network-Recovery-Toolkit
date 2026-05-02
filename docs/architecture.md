# Architecture: Failure Knowledge System

This document describes how the **Windows Network Recovery Toolkit** implements a **knowledge plane** on top of imperative Windows repair scripts. It complements the script-oriented `docs/system_architecture.md` with the end-to-end **Failure Knowledge System** data path.

## End-to-end flow

```text
Windows Signals
    → Read-only Collectors
    → FeatureVector  (python -m src)  /  DiagnosticSnapshot  (failure_system)
    → RuleEngine  +  hypothesis scoring
    → Hypothesis Ranking
    → FailureBlock
    → JSONL Knowledge Store  (data/failure_blocks/ + logs/*.jsonl)
    → CLI / FastAPI / Search / Recommend
    → Human-confirmed Repair  (batch, repair-safe, hybrid API with confirm)
```

Repairs are **not** on the same automatic edge as collection or scoring. The final step is always a **control layer**: operator runs a script, types a confirmation phrase, or sends an API flag—per the component’s design.

## Layer reference

| Layer | Responsibility | Primary locations |
| --- | --- | --- |
| **Signal** | Raw Windows evidence: subprocess output, registry/proxy views, routing, ports. | `src/diagnostics/`, `network_agent/collectors/`, `failure_system/collector.py`, `scripts/*.bat` |
| **Feature** | Normalized booleans and counts (e.g. `FeatureVector`, `DiagnosticSnapshot`) for deterministic logic. | `src/diagnostics/features.py`, `failure_system/models.py` |
| **Decision** | Deterministic rules + confidence-like scores; ranked hypotheses with explanations. | `src/decision_engine/`, `failure_system/rules.py`, `network_agent/engine/` |
| **Knowledge** | Typed **FailureBlock** records and append-only JSONL for audit and search. | `failure_system/generator.py`, `failure_system/storage.py`, `data/failure_blocks/` |
| **Interface** | Operator access: `python -m src`, `python -m failure_system`, FastAPI apps, batch wrappers, optional UIs. | `src/cli.py`, `failure_system/api.py`, `scripts/`, `network_agent/api.py`, `backend/`, `frontend/` |
| **Control** | Safety boundary: no auto-repair from FKS, typed confirmations, policy-gated repair preview/execute. | `failure_system/safety.py`, `src/repair/`, `network_agent/safety/`, batch prompts |

## Why deterministic rules (not opaque ML) for local recommendations

- **Auditability** — Operators and reviewers can answer *why* a hypothesis ranked high (explicit evidence strings and rule ids).
- **Predictability** — Same inputs yield the same ranking; useful for reproducing incidents and writing tests (`tests/fixtures/`).
- **Safety alignment** — Opaque models can recommend destructive steps without a clear rollback story; this project keeps stack resets and firewall changes **out of automatic paths** and labels narrative risk tiers for **human** action.

Machine learning is **not** claimed for core diagnosis paths in this repository; scoring is **deterministic** unless you add separate tooling yourself.

## Related documents

- [`failure_block_contract.md`](failure_block_contract.md) — FailureBlock field contract.
- [`safety_model.md`](safety_model.md) — Diagnose-first / repair-after-confirmation rules.
- [`system_architecture.md`](system_architecture.md) — Script-centric layered network model.
- [`decision_engine_v2.md`](decision_engine_v2.md) — Live hypothesis scoring contract.
