# Production-shape upgrade

This document summarizes the portfolio upgrade from “strong prototype” to production-shaped platform.

## New capabilities

| Area | Module / path | CLI / API |
|------|---------------|-----------|
| Case studies | `case_studies/00*` | `incident-review --incident-id` |
| Incident review | `platform_core/incident_review/` | markdown / json output |
| SLO metrics | `platform_core/reliability_metrics.py` | `GET /platform/slo`, Prometheus |
| Fleet simulation | `platform_core/fleet_simulation.py` | `fleet-simulate`, `fleet-report` |
| Policy-as-code | `config/policies/*.yaml` | `policy-validate`, `proxy-policy --policy` |
| Dashboard | `frontend/app/platform/incidents`, `slo` | RBAC headers via PlatformShell |
| Demo | `scripts/demo_production.ps1` | `make demo-production` |

## Safety preserved

- No autonomous destructive remediation
- No default cloud upload
- Append-only JSONL audit unchanged
- Dry-run / typed confirmation gates unchanged

## Tests

```bash
pytest -q tests/test_incident_review_generator.py tests/test_slo_metrics.py \
  tests/test_fleet_simulation.py tests/test_policy_as_code.py tests/test_demo_production_contract.py
```
