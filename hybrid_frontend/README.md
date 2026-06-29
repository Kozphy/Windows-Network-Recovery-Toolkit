# Hybrid Frontend (static demo UI)

Simple, beginner-friendly **static HTML/JS** UI for the Hybrid AI Network Diagnostic Agent (`network_agent/`). Distinct from the Next.js `frontend/` SaaS demo.

**Does not** replace `python -m windows_network_toolkit` CLI or platform `/platform/*` API.

---

## Features

- Run diagnosis (`POST /diagnose`)
- View top diagnosis issue, confidence, evidence, and recommended action
- Preview repair commands (`POST /repair/preview`)
- Execute repair only after explicit user confirmation (`POST /repair/execute`)
- View saved report JSON by `report_id` (`GET /reports/{report_id}`)

---

## Run UI

From repository root:

```powershell
python -m http.server 5501 --directory hybrid_frontend
```

Open **http://localhost:5501**

---

## Backend

Run the Hybrid Agent API first:

```powershell
uvicorn network_agent.api:app --reload --host 0.0.0.0 --port 8010
```

In the UI, set **FastAPI Base URL** to `http://localhost:8010`.

---

## Safety boundaries

| Operation | Risk | Gate |
|-----------|------|------|
| `POST /diagnose` | Read-only probes | None beyond API reachability |
| `POST /repair/preview` | Shows commands only | No execution |
| `POST /repair/execute` | **May run host shell commands** | Requires `confirm: true` in JSON body |

Repair execute is the only mutating path — treat this stack as **local lab only**.

---

## Audit notes

Inspect `reports/` JSON and API response payloads after execute. Compare with `logs/repair_audit.jsonl` when using the main `python -m src` repair flows in parallel experiments.
