# ADR-005: Local-First, No Default Telemetry Upload

## Status

Accepted

## Context

Endpoint reliability tooling often drifts into silent agent phone-home behavior. This repository targets operators who need **on-machine evidence** for troubleshooting and portfolio demos without mandating cloud services.

## Decision

- Default storage: local `logs/`, `reports/`, optional `platform_data/` JSONL.
- FastAPI `/platform/*` ingest and dashboard are **optional**; `endpoint_agent` upload is opt-in only.
- No default Stripe/SaaS/Supabase dependency for core diagnose → audit → replay flow.
- Privacy helpers hash endpoint identifiers; raw hostnames are not required in platform payloads.

## Consequences

- Multi-host fleet demos use explicit heartbeat/snapshot POSTs, not background exfiltration.
- CI runs fully on Ubuntu with fixtures — no Windows admin, no cloud keys.
- Portfolio reviewers can clone and run offline.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Managed SaaS as primary story | Misaligns with stated local-first positioning |
| Always-on agent upload | Violates “no silent telemetry” principle |
| Centralized log store required | Blocks air-gapped use cases |

## Risks

- Optional JWT/Stripe demo routes in `backend/main.py` may confuse readers — README de-emphasizes SaaS paths; platform contract doc focuses on `/platform/*`.
