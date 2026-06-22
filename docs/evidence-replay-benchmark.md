# Evidence replay benchmark

Deterministic replay benchmark for the endpoint evidence analytics pipeline.

## Why deterministic replay matters

| Audience | Value |
|----------|-------|
| Platform engineering | Regression tests catch classifier drift before deploy |
| Auditability | Reviewers reproduce the same decision from stored evidence |
| Incident review | Stable outputs support committee-ready narratives |
| False escalation prevention | Nondeterministic labels erode trust in triage |

## Metrics

| Metric | Meaning |
|--------|---------|
| `replay_count` | Pipeline runs per case |
| `deterministic_match_rate` | Cases with identical canonical output hashes |
| `nondeterministic_case_count` | Cases with hash mismatch across runs |
| `audit_verification_pass_rate` | `verify_chain` pass rate when audit path provided |
| `replay_duration_ms` | Wall-clock duration (informational only) |

## Run

```powershell
python -m windows_network_toolkit replay-benchmark \
  --cases tests/fixtures/evaluation/replay_cases.jsonl \
  --format markdown
```

## Scope

Fixture-only — no live registry mutation. Hash chain verification is integrity of append order, not truth of observations.
