# Control Testing (CT)

Control Testing evaluates whether an explicit control procedure is supported by the evidence currently available for an incident.

## Position in the pipeline

```text
Observation
  -> normalized evidence
  -> incident classification
  -> control testing
  -> policy decision
  -> preview / human approval
  -> outcome
  -> audit and replay
```

Control Testing does **not** authorize remediation. A PASS means only that all requirements in the versioned control definition were satisfied by referenced evidence.

## Core contracts

- `ControlDefinition`: versioned objective, owner, frequency, requirements, and limitations.
- `EvidenceRequirement`: required evidence type, fields, and minimum proof tier.
- `ControlTestResult`: immutable conclusion, evidence lineage, missing requirements, rationale, and limitations.
- `evaluate_control`: deterministic evaluator over a supplied evidence snapshot.

## Conclusions

| Conclusion | Meaning |
|---|---|
| `PASS` | Every explicit evidence requirement was satisfied. |
| `PARTIAL` | At least one requirement was satisfied and at least one remains missing. |
| `FAIL` | Evidence exists, but none of the requirements were satisfied. |
| `NOT_TESTED` | No evidence was supplied. |

These are test conclusions, not probabilities, security verdicts, or audit opinions.

## Example

```python
from src.platform_core.control_testing import (
    ControlDefinition,
    EvidenceRequirement,
    evaluate_control,
)

control = ControlDefinition(
    control_id="CTRL-001",
    version="1.0",
    name="Dead WinINET Proxy Detection",
    objective="Detect a configured localhost proxy without runtime corroboration.",
    requirements=(
        EvidenceRequirement(
            evidence_type="proxy_state",
            required_fields=("wininet_proxy_enabled", "wininet_proxy_server"),
            minimum_tier=1,
        ),
        EvidenceRequirement(
            evidence_type="listener_state",
            required_fields=("listener_found", "localhost_port"),
            minimum_tier=2,
        ),
    ),
)

result = evaluate_control(
    control,
    evidence_rows,
    incident_id="incident-123",
    tested_at_utc="2026-07-30T00:00:00Z",
)
```

## Governance invariants

1. Missing evidence remains missing; the evaluator does not infer probe results.
2. Proof tiers are minimum evidence gates, not confidence probabilities.
3. Deterministic IDs support retry-safe ingestion and replay.
4. A PASS never creates execution authority.
5. Each result preserves evidence references and explicit limitations.

## Recommended next integration

1. Add a versioned control catalog for `CTRL-001` through `CTRL-010`.
2. Persist results in append-only, hash-chained JSONL.
3. Export `fact_control_tests.csv` from these native results.
4. Add CLI commands: `control-test run`, `control-test show`, and `control-test summary`.
5. Link control results to `OutcomeEvent` without claiming that a passing control caused recovery.
