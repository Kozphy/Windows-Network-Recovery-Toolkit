# Endpoint Reliability Platform (vision)

## Single-machine toolkit vs enterprise-style platform

| Mode | Focus |
| --- | --- |
| **Toolkit** (default) | Operator on one Windows PC: `.bat` scripts, `python -m src`, Failure Knowledge System CLI—**local JSONL**, **human-confirmed** repair. |
| **Platform** (this layer) | Same signals and safety rules, **structured** as an **endpoint agent → policy → optional local API → dashboard** flow for **observability, preview-first remediation, and audit**—still **local-first** and **portfolio-safe**. |

## Local-first safety model

- **No automatic destructive repair** from API, agent loop, or dashboard.
- **Diagnose → normalize → decide → FailureBlock** stays **deterministic** where used.
- **Remediation** is always **preview → policy check → typed confirmation** for anything beyond read-only.
- **Logs and platform JSONL** remain **on disk** under this repo unless **you** copy them—**no external upload** in the prototype.

## Endpoint agent

A thin Python module (`endpoint_agent/`) runs **read-only** collection (reusing `failure_system` collectors where possible), builds **sanitized** `EndpointSnapshot` rows, optional **heartbeat**, and optional **POST** to **localhost** FastAPI only.

## Telemetry normalization

Raw subprocess output is **not** shipped verbatim by default: **privacy helpers** hash identifiers, mask IPs, and strip paths containing usernames before persistence or API response.

## FailureBlock knowledge model

Existing **FailureBlocks** (`failure_system/`) remain the knowledge unit: **signals → causes → confidence → recommended_fix → risk → safety_boundary → rollback_plan**. The platform **links** `FailureEvent` records to **failure_block_id** for traceability.

## Policy-controlled remediation

`platform_core/policy.py` classifies actions into **read_only**, **low**, **medium**, **high**, **forbidden**. **High-risk** and **forbidden** actions are **blocked from API execution**; they may appear only as **manual instructions** in previews.

## Audit trail

Append-only **JSONL** under `platform_data/` plus **PlatformAuditRecord** rows for operator actions (preview requested, execute attempted, policy denied).

## Operator workflow

1. Agent or CLI produces **diagnosis** and optional **FailureBlock**.
2. Operator opens **dashboard** or API: sees **events**, **risk**, **policy decision**.
3. Operator requests **remediation preview** → receives **commands preview** + **typed phrase**.
4. Operator enters phrase → **execute** runs **allowlisted** scripts only (or **dry-run**).

## Future fleet-level extension

See **`docs/fleet_architecture.md`**: optional central ingestion—**out of scope** for default prototype; agent remains authoritative for enforcement.
