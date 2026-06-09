# Outcome Learning

Deterministic outcome tracking — **not** autonomous AI.

## Classifications

| Value | Meaning |
|-------|---------|
| `SUCCESSFUL_REMEDIATION` | Operator confirmed recovery |
| `PARTIAL_RECOVERY` | Some paths restored |
| `NO_IMPACT` | Blocked by policy or no action taken |
| `REGRESSION` | False positive or rollback required |
| `INCONCLUSIVE` | Insufficient follow-up data |

## Tracked fields

- decision_id, evidence_tier, policy_gate
- remediation_preview, actual_result, rollback_required

Store: `src/platform_core/outcome/store.py` → `logs/canonical_outcomes.jsonl`

API: `POST /v1/outcomes`, `GET /v1/metrics`

See also: [metrics/outcome_learning.md](metrics/outcome_learning.md)
