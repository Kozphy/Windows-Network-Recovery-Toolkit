# Interview script (5 minutes)

## 30-second recruiter pitch

"I built a local-first Windows endpoint reliability platform that explains browser and proxy failures, separates observation from proof, gates fixes through policy, and logs every decision in replayable audit files. Nothing repairs itself by default."

## 2-minute SRE pitch

"The system is event-sourced over append-only JSONL. Read-only probes feed a reasoning engine that ranks failure scenarios with explicit evidence levels. Remediation is preview-first with dry-run execute defaults. Fleet heartbeats, incident lifecycle, and reliability metrics come from the same JSONL store—no database required for the demo. Replay reproduces policy decisions from stored observations without re-probing the host."

## 5-minute system design walkthrough

1. **Observation layer** — CLI probes, proxy guard collectors, optional Sysmon fixtures.
2. **Reasoning** — Event → state → hypotheses → evidence tree → impact score.
3. **Proof boundaries** — Listener correlation is candidate evidence; registry writer fusion requires telemetry.
4. **Policy** — ALLOW / PREVIEW / BLOCK with typed confirmation.
5. **Audit + replay** — Append-only JSONL; deterministic replay tests.
6. **Fleet** — `fleet_store` heartbeats; stale endpoints become `unknown`.
7. **Incidents** — Rule-based creation; lifecycle transitions with validation.
8. **Metrics** — Browser path success, proxy drift, MTTD/MTTR, stickiness, false-positive rate.

## Security reviewer explanation

"Not AV/EDR. Destructive actions are registry-blocked at the API. RBAC headers are unsigned demo simulation. Threat model covers malicious local processes, abused API callers, and stale telemetry. See `docs/threat_model.md`."

## Limitations and future work

- Live Sysmon/EventLog ingestion is optional; fixtures drive CI.
- Unsigned RBAC — would need real auth for production.
- Single-node JSONL — fleet scale would move to object storage + stream processing.
- Heuristic attribution remains ordinal confidence, not calibrated probability.

Full diagram: [system_design_review.md](system_design_review.md)
