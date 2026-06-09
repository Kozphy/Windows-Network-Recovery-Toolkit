# 5-minute production demo

Read-only, fixture-based path that showcases the full platform story without registry mutation or process kill.

## Run

```powershell
.\scripts\demo_production.ps1
```

```bash
make demo-production   # Windows PowerShell
```

Optional API + dashboard:

```powershell
$env:START_API = "1"
.\scripts\demo_production.ps1
# In another terminal: cd frontend && npm run dev
# Set NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000
```

## Pipeline

1. **Fleet simulate** — 25 synthetic endpoints → `platform_data_fleet_demo/`
2. **Proxy timeline** — incident fixture replay
3. **Final causation** — registry writer + port owner proof (fixture)
4. **Policy-as-code** — `config/policies/default.yaml` + `proxy-policy`
5. **Evidence tree** — markdown report
6. **Incident review** — case study `001_proxy_drift_cursor_node`
7. **SLO tests** — JSONL-derived metrics contract

## Dashboard routes

| Page | Path |
|------|------|
| Incidents | `/platform/incidents` |
| Incident detail | `/platform/incidents/[id]` |
| Evidence | `/platform/evidence` |
| Policy | `/platform/policy` |
| Replay | `/platform/replay` |
| SLO | `/platform/slo` |

API: `GET /platform/slo`, `GET /platform/incidents`, `GET /metrics`

## Epistemic boundaries

Observation ≠ proof · Correlation ≠ causation · Policy PREVIEW ≠ execute approval.
