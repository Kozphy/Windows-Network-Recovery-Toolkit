# ADR-006: Endpoint Reliability Platform Pipeline

## Status

Accepted

## Context

The toolkit began as a Windows proxy troubleshooting utility. Operators need a production-grade reliability platform that separates **observation** from **proof**, supports fleet-scale audit, and enables time-travel debugging without re-probing hosts.

## Decision

Implement a unified pipeline under `platform_core/reliability/`:

```
Observation → Event Normalization → State Transition → Hypothesis Ranking
→ Evidence Graph → Optional Proof Collection → Policy Evaluation → Decision
→ Signed Audit → Replay
```

### Core principles (non-negotiable)

1. **Observation ≠ Proof** — tier-0 signals never authorize destructive action.
2. **Correlation ≠ Causation** — evidence graph edges are weighted support, not causal certainty.
3. **Confidence ≠ Certainty** — hypothesis scores are ordinal ranks, not calibrated probabilities.

### Storage

- **Default:** append-only JSONL (`platform_events.jsonl`, `platform_decisions.jsonl`).
- **Optional:** PostgreSQL schema in `platform_core/db/schema.sql` when `PLATFORM_DATABASE_URL` is set.

### API

- **v1** (`/platform/*`): fleet, incidents, legacy correlation, remediation preview.
- **v2** (`/platform/v2/*`): versioned reliability pipeline (events, decisions, replay, policies).

### Policy

- Default outcome: **PREVIEW** in `safe_mode`.
- **ALLOW** requires proof-tier evidence + explicit confirmation.
- **BLOCK** for destructive actions (firewall reset, adapter disable, arbitrary kill).

## Consequences

- Two API surfaces coexist during migration; v2 is the canonical reasoning path for new integrations.
- JSONL remains the local-first default; Postgres is opt-in for multi-node deployments.
- Frontend adds dedicated pages: Events, States, Evidence, Policies, Replay, Timeline.

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Single monolithic `decision_engine.py` in `src/` | Duplicates platform_core contracts; harder to test/replay |
| Immediate auto-remediation on high confidence | Violates observation≠proof; unsafe for malware hypotheses |
| MongoDB event store | Team standard is append-only SQL + JSONL for audit immutability |
