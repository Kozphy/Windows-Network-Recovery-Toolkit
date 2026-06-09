# Platform engineering walkthrough

## Architecture layers

```text
CLI (python -m src) → handlers → domain modules → JSONL / optional Postgres
FastAPI /platform/* → platform_core/storage.py → dashboard
```

## Extension points

| Hook | Use |
|------|-----|
| `DomainAdapter` | Multi-domain decision platform |
| `config/policies/*.yaml` | Org policy profiles |
| `case_studies/` | Portfolio incident narratives |
| `fixtures/fleet/` | Fleet simulation scenarios |

## CI contract

- `pytest -q` full suite
- `make demo-production` — portfolio demo without destructive actions
- `tools/public_release_audit.py --tracked-only` before public push

## Dashboard contract

Pages under `frontend/app/platform/`:

- `/platform/incidents` — lifecycle + clusters
- `/platform/incidents/[id]` — status, evidence level, policy gate, limitations
- `/platform/slo` — SLO snapshot

Headers: `X-Operator-Role`, `X-Operator-Id` (demo RBAC).

## Data boundaries

- `platform_data/` and `platform_data_fleet_demo/` gitignored
- Committed fixtures only under `tests/fixtures/`, `case_studies/`, `fixtures/fleet/`
