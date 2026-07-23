# SRE Reliability Profile

## Service objectives

| Capability | SLI | Initial SLO |
|---|---|---|
| Evidence ingestion | successful accepted records / total valid submissions | 99.5% over 30 days |
| Classification API | non-5xx responses | 99.9% over 30 days |
| Governance report | successful reports / requested reports | 99.5% over 30 days |
| Evidence freshness | age of latest endpoint observation | 95% under 15 minutes |
| Replay determinism | identical output for identical fixture/config/version | 100% in CI |

SLOs are portfolio targets, not claims about a deployed service. Production targets must be derived from measured traffic and stakeholder impact.

## Error-budget policy

- Burn below 50%: normal delivery.
- Burn from 50% to 80%: prioritize reliability defects and instrumentation.
- Burn above 80%: freeze nonessential feature releases.
- Exhausted budget: incident review and explicit risk acceptance before release.

## Golden signals

- Latency: API and report-generation duration.
- Traffic: submissions, classifications, reports, and replay jobs.
- Errors: validation failures, 5xx responses, policy denials, and export failures.
- Saturation: worker utilization, queue depth, database connections, memory, and disk.

## Required telemetry fields

`service.name`, `service.version`, `deployment.environment`, `trace_id`, `request_id`, `case_id`, `evidence_tier`, `policy_decision`, `model_version`, `human_review_required`, and `limitations_count`.

Never place credentials, full registry values containing secrets, personal data, or raw confidential prompts in telemetry.

## Reliability tests

1. Dependency timeout and retry behavior.
2. Database unavailable and recovery.
3. Duplicate submission idempotency.
4. Malformed evidence rejection.
5. Partial exporter failure.
6. Clock skew and stale evidence.
7. Replay after version upgrade.
8. Graceful termination during report generation.

## Incident severity

- SEV-1: unsafe execution path, integrity failure, or widespread inability to classify.
- SEV-2: major report/API degradation with workaround.
- SEV-3: localized defect or delayed evidence.
- SEV-4: cosmetic or documentation issue.

Each incident review should record impact, detection, timeline, contributing controls, evidence, corrective actions, owners, and due dates.
