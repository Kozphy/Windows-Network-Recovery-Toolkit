# Agent Workflow Specification

Six agent roles as **JSON contracts** — Phase 1 uses deterministic pipeline output, not autonomous LLM loops.

## Agents

| Agent | Input | Output contract | Human checkpoint |
|-------|-------|-----------------|------------------|
| Evidence | Collector snapshot | `EvidenceAgentOutput` | None (read-only ingest) |
| Classification | Evidence event | `ClassificationAgentOutput` | Review queue for accusatory-adjacent classes |
| Root Cause | Incident + limitations | `RootCauseAgentOutput` | Hypotheses are ordinal, not proof |
| Risk Assessment | Incident | `RiskAssessmentAgentOutput` | Score is triage, not probability |
| Control Validation | Incident | `ControlValidationAgentOutput` | FAIL → committee visibility |
| Reporting | Audit + incidents | `ReportingAgentOutput` | Management information only |

## Task decomposition

1. Evidence Agent validates and normalizes ingest payload
2. Classification Agent runs `run_endpoint_analytics_pipeline` (deterministic)
3. Root Cause Agent emits hypotheses with `limitations[]`
4. Risk Agent maps confidence to ordinal band
5. Control Agent runs `INCIDENT_CONTROL_MAP` tests
6. Reporting Agent calls `build_executive_report`

Each step appends a domain event. See [domain-event-catalog.md](domain-event-catalog.md).

## Retry policy

Orchestrator stub: no retries in Phase 1. Worker retries via `backend/queue/retry_policy.py`.

## Hard safety

- No agent may call remediation execute
- AI actor prefixes blocked from `approve_remediation_preview` ([human_review.py](../src/platform_core/governance/human_review.py))
