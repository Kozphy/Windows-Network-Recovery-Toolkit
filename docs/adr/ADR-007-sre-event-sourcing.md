# ADR-007: Google SRE-Style Event Sourcing and Incident Operations

## Status

Accepted

## Context

The v2 reliability pipeline provides deterministic reasoning but lacked:
- A **single canonical event log** for incident operations
- **Lifecycle-derived MTTR** (not fixture timestamp hacks)
- **Failure domain isolation** with auditable circuit breaking
- **Postmortem generation** linked to replayable timelines

Google SRE practice: optimize for **correctness and operational reliability**, not developer convenience.

## Decision

Introduce `platform_core/sre/` as the operational layer:

| Capability | Implementation |
|------------|----------------|
| Event sourcing | `sre_domain_events.jsonl` — `DomainEvent` envelope with per-aggregate sequence |
| Deterministic projections | `Projector.fold()` rebuilds `IncidentProjection` |
| Failure domain isolation | `FailureDomain` bulkheads + circuit breakers + `domain.circuit_*` audit events |
| Investigation | `run_investigation()` wraps v2 decision pipeline inside domains |
| RCA | `build_rca_report()` — evidence-driven, explicit limitations |
| Timeline | `reconstruct_timeline()` from canonical log |
| MTTR | `compute_incident_mttr_metrics()` from detected→ack→identify→resolve events |
| Postmortem | `generate_postmortem()` — blameless markdown + `postmortem.generated` event |

### API

`/platform/v2/sre/*` — incidents, investigate, timeline, RCA, resolve, postmortem, MTTR metrics.

### Epistemic invariants (unchanged)

- Observation ≠ Proof
- Correlation ≠ Causation  
- Confidence ≠ Certainty
- Malware-class RCA without proof tier → investigative language only

## Consequences

- **Two event logs coexist**: telemetry (`platform_events.jsonl`) + operations (`sre_domain_events.jsonl`). Unification is a future migration; SRE log is authoritative for incidents.
- **Strict sequence enforcement** rejects out-of-order appends — callers must use `append_domain_event()`.
- **Incident commands fail loudly** on invalid phase transitions (no silent state mutation).
- Postmortems are generated artifacts, not source of truth — source of truth remains domain events.

## Alternatives rejected

| Alternative | Why rejected |
|-------------|--------------|
| Mutable incident rows in SQLite | Breaks replay; violates audit requirements |
| MTTR from `platform_signals.jsonl` | Not tied to incident lifecycle; incorrect for SRE review |
| Auto-resolve on high confidence | Violates proof requirements; unsafe |
