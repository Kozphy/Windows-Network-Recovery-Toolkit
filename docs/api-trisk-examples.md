# Technology Risk API — Example Requests

Read-only FastAPI routes mounted at `/trisk` from `backend/technology_risk_routes.py`.

Start API (from repo root):

```powershell
uvicorn backend.main:app --reload --port 8000
```

Default fixture: `tests/fixtures/analytics_pipeline_fixture.json`

---

## GET /trisk/health

```bash
curl -s http://localhost:8000/trisk/health | jq
```

```json
{
  "status": "ok",
  "service": "windows-network-toolkit",
  "version": "…",
  "api": "technology-risk-analytics",
  "positioning": "Technology Risk & Control Analytics — not antivirus, EDR, or autonomous remediation."
}
```

---

## GET /trisk/incidents

```bash
curl -s "http://localhost:8000/trisk/incidents?limit=5" | jq '.items[0]'
```

Returns paginated incidents with `incident_class`, `risk_level`, `limitations[]`.

---

## GET /trisk/risks

```bash
curl -s "http://localhost:8000/trisk/risks?limit=5" | jq
```

Returns ordinal `risk_scores[]` with governance limitations.

---

## GET /trisk/controls

```bash
curl -s "http://localhost:8000/trisk/controls" | jq '.control_tests[0]'
```

Optional filter: `?incident_class=DEAD_PROXY_CONFIG`

---

## GET /trisk/reports/executive

```bash
curl -s http://localhost:8000/trisk/reports/executive | jq '.kpis'
```

Executive KPI rollup — management information, not audit opinion.

---

## Custom fixture (allowlisted paths only)

```bash
curl -s "http://localhost:8000/trisk/incidents?fixture=tests/fixtures/analytics_pipeline_fixture.json"
```

Paths must resolve under `tests/fixtures/`, `examples/`, or `windows_network_toolkit/examples/`.

---

## Safety note

No POST/PUT/DELETE on `/trisk/*` for remediation. Mutation remains CLI-gated with typed confirmation.
