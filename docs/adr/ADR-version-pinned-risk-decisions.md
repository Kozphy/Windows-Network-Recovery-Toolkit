# ADR: Version-pinned technology-risk decisions

- Status: Accepted
- Date: 2026-07-24

## Context

Historical replay is only trustworthy when a decision records the exact evidence schema, classifier, policy, and control-set versions used at decision time. Incident IDs and timestamps alone cannot distinguish two decisions produced under different governance logic.

The repository previously stored a `risk_decision_record.v1` artifact with an evidence hash, but the hash did not explicitly bind all decision-producing component versions.

## Decision

`RiskDecisionRecord` is upgraded to `risk_decision_record.v2` and includes:

- `evidence_schema_version`
- `classifier_version`
- `policy_version`
- `control_set_version`
- `decision_key`

The evidence hash includes the normalized classification input and all four component versions. The decision key binds the evidence hash to the decision-producing versions and is deterministic for a fixed incident input.

Version values may be supplied through a fixture `versions` object or legacy top-level `<component>_version` fields. Empty values fall back to explicit defaults.

## Consequences

### Positive

- Historical decisions can be grouped by governance logic.
- Replays can detect policy or classifier drift.
- Consumers can reject unknown schema versions instead of guessing compatibility.
- Future shadow-policy comparisons have a stable identity foundation.

### Negative

- Existing consumers expecting `risk_decision_record.v1` must update their schema assertions.
- Changing a component version intentionally changes evidence and decision identity.
- This does not by itself provide distributed deduplication or durable event delivery.

## Alternatives considered

1. **Use only Git commit SHA** — rejected because deployments may combine configuration and code from different sources, and a commit SHA does not express domain compatibility.
2. **Use timestamps as identity** — rejected because timestamps are not deterministic and cannot support replay equivalence.
3. **Hash the entire fixture** — rejected because irrelevant metadata could invalidate decision identity and obscure the governed inputs.

## Revisit trigger

Revisit when a centralized ingestion service is introduced. At that point, add signed evidence envelopes, canonical normalization, an idempotency store, and replay availability checks for historical component versions.
