# Data Retention Policy

**Status:** Portfolio defaults — not legal/compliance approved.

## Local JSONL audit

| Data | Default retention | Notes |
|------|-------------------|-------|
| `audit.jsonl`, `incidents.jsonl` | Until operator deletes | Append-only; hash chain |
| `human_review.jsonl` | Same as audit dir | Governance decisions |

## Postgres (demo stack)

| Table | Default | Production gap |
|-------|---------|----------------|
| `trisk_evidence_events` | Docker volume lifetime | No automated purge in demo |
| Incidents, controls, audit chain | Co-retained with evidence | Enterprise: tiered retention + legal hold |

## Synthetic fleet output

`fleet-simulate` / `fleet-benchmark` outputs under `reports/benchmarks/` — safe to delete; not production telemetry.

## PII minimization

- Prefer synthetic fixtures in git
- Live collection may include hostnames — redact before export in enterprise deployments
- **Gap:** no field-level redaction at ingest in portfolio

## Not covered

- GDPR erasure workflows
- Legal hold
- Cross-border data residency
