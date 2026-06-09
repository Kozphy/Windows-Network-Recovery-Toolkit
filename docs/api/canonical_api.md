# Canonical API (`/v1/*`)

Single decision pipeline entry. See `backend/canonical_routes.py`.

| Route | Method |
|-------|--------|
| `/v1/health` | GET |
| `/v1/version` | GET |
| `/v1/events` | POST |
| `/v1/decisions` | POST |
| `/v1/policy/evaluate` | POST |
| `/v1/remediation/preview` | POST |
| `/v1/remediation/approve` | POST |
| `/v1/remediation/execute` | POST |
| `/v1/replay/certify` | POST |
| `/v1/outcomes` | POST |
| `/v1/metrics` | GET |
| `/v1/audit/{decision_id}` | GET |
| `/v1/governance/controls` | GET |

Legacy `/platform/*` and `/health` (ERP) remain for backward compatibility.
