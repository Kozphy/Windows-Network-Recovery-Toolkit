# ADR-0001: Evidence-to-Action Pipeline

## Status

Accepted

## Context

Endpoint proxy incidents produce heterogeneous observations: registry reads, listener correlation, path probes, watch timelines, and operator commands. Without a normalized pipeline, teams conflate raw logs with proof, skip control testing, and remediate without audit records. Big 4 and platform stakeholders require a repeatable path from observation to governed action.

## Decision

Implement a linear **evidence-to-action pipeline**:

1. Normalize raw inputs to `EvidenceEvent` (`evidence_schema.py`) with tier labels and `limitations[]`
2. Classify to `IncidentRecord` or transition events (`incident_classifier`, `proxy_state_machine`)
3. Run control tests (`control_tests.py`)
4. Score risk ordinally (`risk_scoring_engine.py`)
5. Evaluate policy (`evidence_to_action.py`) — preview / human review / block
6. Append hash-chained audit records
7. Export governance report and Power BI star schema

Every stage preserves `raw_snapshot` for replay. No stage auto-upgrades proof tier.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Single monolithic "fix" command | Hides governance stages; fails audit walkthrough |
| Direct SIEM-only pipeline | Breaks local-first, air-gapped operator requirements |
| LLM-first classification | Non-deterministic; violates CI fixture contracts |

## Consequences

- More CLI steps before apply — acceptable for audit safety
- Fixture-driven CI can test full pipeline without Windows
- Documentation must keep tier language consistent across modules

## Security considerations

- Normalization must not strip security-relevant fields from `raw_snapshot`
- Pipeline outputs must not emit secrets; Power BI export includes `SECRET_PATTERN` redaction
- Failed controls must not trigger destructive side effects

## Audit considerations

- Deterministic `event_id` and `incident_id` support reperformance
- Each artifact includes limitations for workpaper cross-reference
- Governance report aggregates pipeline outputs — not a formal opinion

## What this prevents

- Silent upgrade from observation to proof in dashboards
- Remediation without prior classification and control context
- Non-replayable "black box" triage narratives

## What this does not prove

- Population-wide control operating effectiveness
- Correctness of every observation in the chain
- That exported KPIs represent live fleet state without scope disclaimer

## Interview defense

"I can draw the pipeline on a whiteboard: normalize → classify → control test → policy → audit → export. Each box adds limitations, not authority. That's how we keep Big 4 language honest while still shipping developer tooling."
