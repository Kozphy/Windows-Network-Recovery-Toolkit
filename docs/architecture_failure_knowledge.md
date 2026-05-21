# Architecture: Failure Knowledge System

This document describes the **Failure Knowledge System** (FKS) path. For the **endpoint reliability / event-state platform** layer, see [architecture.md](architecture.md).

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

Repairs are **not** on the same automatic edge as collection or scoring.

## Layer reference

| Layer | Responsibility | Primary locations |
| --- | --- | --- |
| **Signal** | Raw Windows evidence | `src/diagnostics/`, `failure_system/collector.py`, `scripts/` |
| **Feature** | Normalized booleans | `src/diagnostics/features.py`, `failure_system/models.py` |
| **Decision** | Deterministic rules + scores | `src/hypothesis/`, `failure_system/rules.py` |
| **Knowledge** | FailureBlock + JSONL | `failure_system/generator.py`, `failure_system/storage.py` |
| **Control** | Safety boundary | `failure_system/safety.py`, `src/repair/` |

## Related documents

- [`failure_block_contract.md`](failure_block_contract.md)
- [`decision_engine_v2.md`](decision_engine_v2.md)
- [`architecture.md`](architecture.md) — platform + trading-infra simulator
