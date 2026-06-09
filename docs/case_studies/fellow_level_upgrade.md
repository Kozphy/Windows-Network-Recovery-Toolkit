# Fellow-Level Platform Upgrade

## Problem

Windows endpoints fail browser paths while ping/DNS succeed — operators reset network stacks without evidence.

## Prior state

Fragmented modules: `platform_core/`, `src/platform/`, `windows_network_toolkit/`, multiple policy vocabularies.

## Architecture doctrine

`src/platform_core/` — Event → Evidence → Hypothesis → Decision → Policy → Outcome → Audit → Replay → Learning

## Safety model

Proof-grade tier state machine; correlation cannot unlock destructive remediation.

## Governance model

Hash-chained audit JSONL, policy compiler, control mapping (informational).

## Replay certification

`python -m toolkit replay-certify proxy_drift_incident.jsonl`

## Outcome metrics

`GET /v1/metrics` — see `docs/metrics/outcome_learning.md`

## Example walkthrough

POST `/v1/events` with `proxy_drift_incident.jsonl` → decision + policy PREVIEW_ONLY/BLOCK → audit chain.

## What is real

- 1000+ pytest, safety contracts, Windows collectors (when run on Windows)

## What is synthetic

- Fleet simulation, golden JSONL fixtures, in-memory API session store

## Known limitations

- Ordinal confidence, not calibrated probability
- Live execute blocked in safe mode
- MDP multi-domain fixtures separate from Windows live path

## Next steps

- Wire live Windows collectors → NormalizedEvent
- Merge `backend/decision_intelligence` onto canonical pipeline
- Optional signed audit reports
