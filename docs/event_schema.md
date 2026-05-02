# Unified event schema

Authoritative definitions live in `platform_core/events.py`.

## Core envelopes

### `NormalizedEvent`

| Field | Notes |
| --- | --- |
| `schema_version` | `1` or `2026.01` (see `SUPPORTED_SCHEMA_VERSIONS`) |
| `event_id` | Unique string per append |
| `event_type` | e.g. `signal.snapshot`, `normalized.remediation_candidate` |
| `timestamp` | UTC ISO-8601 |
| `source` | `agent`, `cli`, `replay`, `fixture`, … |
| `severity` | `info` … `critical` |
| `endpoint_id_hash` | **Never** plaintext hostname — hash only |
| `signals` | Redacted telemetry + optional `remediation_action` |
| `actor_attribution` | Optional :class:`ActorAttribution` |
| `policy_decision` | Optional :class:`PolicyDecisionPayload` |
| `remediation_preview` | Optional echo for UI |
| `privacy_classification` | coarse label for redaction tiers |

### `ActorAttribution`

`confidence`: `none` | `low` | `medium` | `high` | **proof**

> **Proof** is reserved for providers that ingest tamper-aware evidence streams (stubbed here).

### Policy payload

Mirrors gate output (`execute_allowed`, `preview_allowed`, `reason_codes`, `required_confirmation`, …).
