# Decision context — Stakeholder + Timing

Local-first orchestration layers that sit **after** Policy and **before** Remediation Preview.

```text
Evidence → Hypothesis → Proof → Policy → Stakeholder → Timing
  → Remediation Preview → Audit → Replay → Learning
```

## Separation of concerns

| Layer | Answers | Does not |
|-------|---------|----------|
| Evidence / Proof | What was observed; how strong is the claim? | Who must approve |
| Policy | What is technically permitted? | When to act |
| Stakeholder | Who owns / approves / executes / is informed? | Technical truth |
| Timing | Urgency, SLA, windows, evidence freshness | Execution authority |

Principles preserved in code and reports:

- Observation is not proof.
- Correlation is not causation.
- Confidence is not certainty.
- Classification is not accusation.
- Policy permission is not a safety guarantee.
- Stakeholder assignment is not approval.
- A valid maintenance window is not execution authorization.
- Remediation remains preview-only by default.

## CLI

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m windows_network_toolkit diagnose --proof --decision-context --fixture <fixture.json>
python -m windows_network_toolkit stakeholder-resolve --case-id <id> --classification DEAD_PROXY_CONFIG
python -m windows_network_toolkit timing-evaluate --case-id <id> --timezone Asia/Taipei
python -m windows_network_toolkit decision-explain --case-id <id> --format text
```

Timezone defaults to **UTC**. Pass `Asia/Taipei` (or any IANA zone) explicitly when needed — it is never silently hard-coded in platform core.

## API

```text
POST /platform/stakeholders/resolve
POST /platform/timing/evaluate
POST /platform/decision-context/evaluate
GET  /platform/decision-context/latest
```

Evaluate endpoints are preview-only; they do not execute remediation.

## Schema

`decision_context.v1` envelopes store policy and coordination separately:

```json
{
  "policy_decision": "PREVIEW_ONLY",
  "coordination_status": "NEEDS_APPROVAL"
}
```

## Modules

- `src/platform_core/stakeholder/`
- `src/platform_core/timing/`
- `src/platform_core/decision_context/`
