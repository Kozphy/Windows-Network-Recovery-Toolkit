# Tier-1 platform upgrade changelog

## Phase 1 — Real Telemetry Proof Layer

- Tier-1 evidence ladder: `NO_WRITER_EVIDENCE`, `LISTENER_OBSERVED`, `REGISTRY_WRITER_OBSERVED`, `WRITER_AND_LISTENER_MATCH`, `WRITER_LISTENER_MISMATCH`, `INCONCLUSIVE`
- New models: `ProcessIdentity`, `ListenerObservation`
- Module aliases: `sysmon_parser.py`, `windows_eventlog.py`, `etw_adapter.py`
- Fusion never treats listener alone as registry-writer proof

## Phase 2 — Fleet / Endpoint Model

- `platform_core/endpoint_model.py`, `fleet_store.py`, `agent_identity.py`
- JSONL heartbeats with stale → `unknown` policy
- `/platform/endpoints` reads fleet store when populated

## Phase 3 — Incident Lifecycle

- `platform_core/incident_model.py`, `incident_engine.py`, `incident_store.py`
- States: OPEN → ACKNOWLEDGED / MITIGATED / RESOLVED / FALSE_POSITIVE
- Routes: GET/POST `/platform/incidents/{id}/ack|resolve|false-positive`
- Weak evidence cannot create critical severity

## Phase 4 — Threat Model Docs

- `docs/threat_model.md`, `security_boundaries.md`, `operator_safety.md`, `abuse_cases.md`

## Phase 5 — SLO / Reliability Metrics

- `platform_core/slo_model.py`, `slo_engine.py`, `reliability_metrics.py`
- `GET /platform/metrics` includes `reliability_metrics` block

## Phase 6 — Tier-1 Demo Path

- `docs/tier1_demo_walkthrough.md`, `interview_script_5_min.md`, `system_design_review.md`

Safety unchanged: no silent kill, firewall reset, adapter disable, or registry mutation without typed confirmation.
