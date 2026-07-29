# Outcome Intelligence Foundation

## Purpose

The platform already answers:

- What was observed?
- How was the incident classified?
- What proof tier supports the claim?
- Which controls passed or failed?
- What did policy allow?

This foundation adds the missing operational question:

> What happened afterward, and how strongly was that result verified?

It does **not** change remediation authorization. Outcome records are append-oriented management information and must not be interpreted as proof that an action caused recovery.

## Lifecycle

```text
EvidenceEvent
  -> IncidentRecord
  -> ControlTestResult
  -> RiskDecisionRecord
  -> RemediationPreview / approved external action
  -> OutcomeEvent
  -> OutcomeMetrics
```

An `OutcomeEvent` may exist without `decision_id` or `action_id`. This is intentional: an endpoint can recover naturally, through an external support workflow, or through an action outside this repository. Missing action lineage must not be silently invented.

## Schema

`windows_network_toolkit/outcome_schema.py` defines:

- `OutcomeStatus`: OPEN, RESTORED, PARTIALLY_RESTORED, NOT_RESTORED, ROLLED_BACK, UNKNOWN
- `OutcomeVerification`: NOT_VERIFIED, OPERATOR_REPORTED, PATH_PROBE_VERIFIED, REPLAY_VERIFIED
- deterministic `outcome_id` for retry-safe ingestion
- incident, endpoint, decision, action, and evidence lineage
- recovery time, recurrence, and rollback fields
- explicit limitations
- `schema_version=outcome_event.v1`

## Metrics

`windows_network_toolkit/outcome_analytics.py` produces descriptive metrics:

- restoration rate
- verified restoration rate
- unresolved outcomes
- median time to recovery
- recurrence rate
- rollback rate
- status and verification distributions

These are not calibrated probabilities and are not formal control-effectiveness attestations.

## Governance invariants

1. Outcome timing does not prove causation.
2. Operator-reported recovery remains separate from path-probe or replay verification.
3. Recurrence requires a defined observation window.
4. An outcome cannot authorize remediation retroactively.
5. Partial restoration remains distinguishable in status counts.
6. Retry-safe identifiers do not replace append-only audit integrity.

## Suggested next integration

1. Add an append-only outcome JSONL writer with hash-chain support.
2. Add `fact_outcome` to the Power BI semantic model.
3. Add incident-to-outcome lineage to governance reports.
4. Add CLI commands for recording and summarizing outcomes.
5. Add controlled-fault fixtures with before/after path probes.
6. Define SLI/SLO targets only after collecting enough representative data.

## Interview value

Before this upgrade, the platform primarily proved evidence collection, classification, policy gating, and auditability. This layer adds measurable operational learning:

> The system can distinguish detection from recovery, reported recovery from verified recovery, and one-time recovery from recurring failure—without claiming causal certainty.
