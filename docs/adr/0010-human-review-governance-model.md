# ADR-0010: Human Review Governance Model

## Status

Accepted

## Context

Accusatory-adjacent classifications (`UNKNOWN_LOCAL_PROXY`, `REVERTER_SUSPECTED`, `POSSIBLE_MITM_RISK`) and HIGH ordinal risk scores require human judgment before remediation narratives reach committees or operators. Fully automated workflows fail technology risk governance expectations.

## Decision

Implement human review governance via:

1. **`human_review_queue`** in `audit_report.py` for accusatory-adjacent classes
2. **Policy mapping:** HIGH/CRITICAL risk → `REQUIRE_HUMAN_REVIEW`
3. **`human_review_recommended`** flag in risk scoring for HIGH scores or control FAIL aggregates
4. **Execution authority:** `human_required` until typed confirmation produces `human_confirmed` audit record
5. **Forum mapping:** `map_business_impact` suggests stakeholder (Cyber Risk Triage, Internal Audit, etc.)
6. **CTRL-006** narrative control for unknown proxy triage

Automation stops at preview and alert — humans authorize apply and external escalation.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Fully automated SOAR playbooks | Out of scope; safety and audit liability |
| No queue — rely on operator discipline | Not demoable to Big 4 |
| Human review only via email | Not structured in audit JSONL |

## Consequences

- Governance report always includes queue section (may be empty)
- Power BI can filter incidents requiring review via classification keys
- Latency added to remediation — acceptable tradeoff

## Security considerations

- Prevents knee-jerk process kill on reverter correlation
- MITM class requires path proof context before escalation language

## Audit considerations

- Demonstrates control environment for sensitive classifications
- Queue is not a ticketing system — integration is roadmap

## What this prevents

- Autonomous escalation to "compromised endpoint" messaging
- Silent apply on HIGH risk without confirmation audit

## What this does not prove

- That humans actually performed quality review (procedure compliance)
- Ticket closure or SLA metrics

## Interview defense

"The platform queues accusatory-adjacent labels for humans — automation gives preview and evidence, not execution authority. That's the governance model Big 4 cares about for technology risk."
