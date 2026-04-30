# Hybrid Frontend (Phase 4)

Simple, beginner-friendly web UI for the Hybrid AI Network Diagnostic Agent.

## Features

- Run diagnosis (`POST /diagnose`)
- View top diagnosis issue, confidence, evidence, and recommended action
- Preview repair commands (`POST /repair/preview`)
- Execute repair only after explicit user confirmation (`POST /repair/execute`)
- View saved report JSON by `report_id` (`GET /reports/{report_id}`)

## Run

From repository root:

```powershell
python -m http.server 5501 --directory hybrid_frontend
```

Open:

- `http://localhost:5501`

## Backend

Run the Hybrid Agent API first:

```powershell
uvicorn network_agent.api:app --reload --host 0.0.0.0 --port 8010
```

In the UI, set **FastAPI Base URL** to:

- `http://localhost:8010`
