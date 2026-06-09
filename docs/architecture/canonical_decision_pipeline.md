# Canonical Decision Pipeline

## Doctrine

- Observation != Proof
- Correlation != Causation
- Confidence != Certainty
- Policy Permission != Safety Guarantee

## Pipeline

```text
Event → Evidence → Hypothesis → Decision → Policy → Outcome → Audit → Replay → Learning
```

## Canonical package

`src/platform_core/` is the **single decision engine** for endpoint reliability.

| Stage | Module |
|-------|--------|
| Event | `src/platform_core/contracts.py` (`NormalizedEvent`) |
| Evidence | `src/platform_core/evidence/` |
| Hypothesis | `src/platform_core/hypothesis/` |
| Decision | `src/platform_core/decision/` |
| Policy | `src/platform_core/policy/` |
| Outcome | `src/platform_core/outcome/` |
| Audit | `src/platform_core/audit/` |
| Replay | `src/platform_core/replay/` |
| Learning | `src/platform_core/learning/` |
| Governance | `src/platform_core/governance/` |

## Windows collectors (separate)

`windows_network_toolkit/collectors/` and `src/proxy_guard/` feed events into the pipeline. They do **not** own policy or remediation logic.

## Entry point

```python
from src.platform_core.pipeline import run_decision_pipeline
```
