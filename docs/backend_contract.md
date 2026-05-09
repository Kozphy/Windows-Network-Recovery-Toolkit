# Backend Contract

The frontend is treated as a product contract. Every visible health, fleet, diagnosis, remediation, rollback, audit, and replay claim must map to a backend API, typed schema, evidence source, policy decision, and append-only audit row.

Core rule: observation is not inference, inference is not proof, and telemetry is not causality.

## Platform Status

`GET /platform/health`

Returns backend version, local JSONL mode, audit store status, safe-mode flag, policy mode, and the default remediation posture.

Safety contract:

- `local_first_mode=true`
- `remediation_default=dry_run`
- policy mode defaults to preview-first behavior

## Endpoint Fleet

`GET /platform/endpoints`

`GET /platform/endpoints/{endpoint_id}`

Each endpoint row uses `EndpointSummary`:

- `endpoint_id`
- `hostname_hash`
- `safe_display_name`
- `os`
- `status`
- `last_seen_at`
- `last_known_good_available`
- `latest_risk_score`
- `latest_diagnosis_id`

The API joins append-only heartbeat rows, stored diagnosis runs, and LKG snapshots. If no heartbeat exists, the backend can synthesize a local endpoint summary without exposing the raw hostname.

## Diagnosis

`POST /platform/diagnosis/run`

`GET /platform/diagnosis/latest`

`GET /platform/diagnosis/{run_id}`

Diagnosis uses `DiagnosisResult`:

- `observations`: typed probe outputs
- `inferred_hypotheses`: bounded explanations derived from observations
- `confidence`
- `evidence_level`: `observation`, `inference`, or `proof`
- `recommended_next_test`
- `policy_result`
- `audit_event_id`

Current minimal probes include DNS, TCP 443, HTTPS, WinINET proxy state, WinHTTP proxy state, localhost listener candidate, Git/npm proxy config, and LKG availability.

Listener correlation is always a candidate signal. It is not registry writer proof.

## Remediation Preview And Execute

`POST /platform/remediation/preview`

`POST /platform/remediation/execute`

Responses preserve legacy preview/execution fields and add:

- `action_id`
- `allowed`
- `decision`: `allow`, `preview_only`, or `blocked`
- `reason`
- `required_confirmation`
- `audit_event_id`
- `dry_run`

Execution defaults to `dry_run=true`. High-risk or forbidden actions are blocked by policy. Live execution remains limited to allowlisted scripts, Windows-only paths, RBAC, typed confirmation, and explicit unsafe-mode environment gates.

## LKG And Rollback

`GET /platform/lkg/{endpoint_id}`

`POST /platform/lkg/snapshot`

`POST /platform/rollback/preview`

Rollback is preview-only in this contract. It only proposes targeted reversible WinINET fields and never resets the firewall, disables adapters, deletes certificates, or performs destructive registry cleanup.

## Audit

`GET /platform/audit`

`GET /platform/audit/tail`

Every diagnosis, remediation preview, blocked action, execute attempt, LKG snapshot, rollback preview, and agent next-step appends JSONL. Product audit rows include:

- `event_id`
- `timestamp`
- `endpoint_id`
- `event_kind`
- `observations`
- `summary`
- `hypothesis`
- `confidence`
- `evidence_level`
- `policy_decision`
- `actor`
- `replay_ref`
- `run_id`
- `previous_hash`
- `hash`

The hash fields support append-only integrity checks. They are not a substitute for OS-level file protection.

## Replay

`GET /platform/replay/{run_id}`

Replay recomputes the diagnosis summary from stored observations only. It does not reprobe the live machine.

`POST /platform/replay/preview` remains available for inline event replay.

## Agentic Next Step

`POST /platform/agent/next-step`

Allowed goals:

- `suggest_next_probe`
- `rank_hypotheses`
- `explain_risk`
- `generate_remediation_preview`
- `summarize_audit`

The agent does not repair. It returns a structured suggestion with evidence used, confidence, and the policy boundary.

