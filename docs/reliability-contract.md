# Decision Pipeline Reliability Contract

Status: portfolio platform contract

This document defines the minimum behavioral guarantees for evidence-backed technology-risk decisions. It does not claim enterprise production deployment.

## Guarantees

1. **Version-pinned decisions** — every `RiskDecisionRecord` identifies the evidence schema, classifier, policy, and control-set versions used to produce it.
2. **Deterministic replay key** — the same normalized decision input and the same component versions produce the same `decision_key`.
3. **Version-sensitive replay** — changing a classifier, policy, evidence schema, or control-set version changes the decision identity even when the incident ID is unchanged.
4. **Human authorization boundary** — deterministic identity does not grant execution authority. Remediation remains preview-only unless existing policy and confirmation controls permit execution.
5. **Explicit compatibility boundary** — schema changes require a new `RiskDecisionRecord.schema_version`; consumers must not infer compatibility from field presence alone.

## Delivery semantics

The current portfolio implementation is process-local and fixture-first. It demonstrates deterministic decision construction, not distributed exactly-once processing.

| Stage | Current semantic | Future production target |
| --- | --- | --- |
| Evidence collection | best effort, fixture or local collector | at-least-once ingestion with signed envelopes |
| Classification | deterministic function for a fixed input/version | idempotent worker execution |
| Policy evaluation | version-pinned decision input | versioned control plane with shadow evaluation |
| Audit persistence | append-oriented local artifacts | durable append-only store with outbox/reconciliation |
| Reporting | derived projection | eventually consistent projection with freshness SLO |

## Failure behavior

- Duplicate evidence must be detectable through stable evidence identity before any future distributed ingestion path acknowledges processing.
- A policy-version change must not silently rewrite historical decisions.
- A replay using an unavailable component version must return `NOT_REPLAYABLE`, not substitute the latest version.
- Audit-write failure must never be represented as a successful audited decision.
- Human approval must remain distinct from technical classification and policy eligibility.

## Non-claims

This contract does not claim calibrated probability, autonomous remediation, malware attribution, formal audit assurance, exactly-once distributed delivery, or deployed fleet-scale performance.
