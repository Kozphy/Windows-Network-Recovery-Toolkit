# Outcome Learning

## Measured metrics

| Metric | Definition |
|--------|------------|
| `decision_accuracy` | Share of outcomes marked `was_successful=True` |
| `false_positive_rate` | Share marked `was_false_positive=True` |
| `policy_block_rate` | Share blocked by policy |
| `mean_time_to_resolution` | Mean `time_to_resolution_seconds` |
| `median_time_to_resolution` | Median TTL |
| `mttr_delta_baseline` | `baseline_mttr_seconds - mean_mttr` (positive = improvement) |
| `approval_rate` | Operator actions containing "approve" |
| `rollback_rate` | Outcomes mentioning rollback |

## MTTR delta

Synthetic baseline defaults to 3600s. Real deployments should set baseline from historical ticketing data.

## False positives

An outcome is a false positive when remediation or diagnosis targeted the wrong root cause — recorded explicitly by operator review.

## Synthetic vs real

- **Synthetic:** `tests/fixtures/platform_core/golden/` and fleet simulation.
- **Real-world:** Anonymized incident exports with host IDs hashed; not included in repo by default.
