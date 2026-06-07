# ADR-003: Append-Only Audit and Deterministic Replay

## Status

Accepted

## Context

Incident review requires knowing **what was observed**, **what was inferred**, and **what policy decided** at decision time. Mutable logs and re-probing the host during replay destroy reproducibility.

## Decision

- Persist operator and platform actions as **append-only JSONL** (`logs/*.jsonl`, `platform_data/*.jsonl`).
- Replay recomputes policy and reasoning from **stored observations** without subprocess repair, registry mutation, or live network probes.
- Schema fields include `schema_version`, timestamps, and embedded `policy_decision` blobs for drift detection.

## Consequences

- Disk usage grows monotonically; cleanup is operator-controlled (`tools/cleanup_generated.py`).
- Replay can detect when embedded policy decisions no longer match current registry rules (`changed_decisions` counters).
- Dashboard and API read tails; they do not rewrite history.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| SQLite mutable audit table | Harder to treat as event stream; merge conflicts in demos |
| Re-run live probes on replay | Non-deterministic; unsafe on contested hosts |
| No audit for previews | Loses accountability for near-miss execute attempts |

## Risks

- Multiple JSONL filenames (`decision_audit.jsonl`, `audit.jsonl`, etc.) — documented in `docs/production_readiness.md`; consolidation is future work.
