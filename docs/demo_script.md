# Safe local demo script (5–8 minutes)

This path exercises the **Endpoint Reliability Platform** without running Windows repair scripts or uploading logs.

## Prereqs

```powershell
cd <repo-root>
pip install -r failure_system\requirements.txt
pip install -r requirements-platform.txt
```

## 1 — Seed synthetic fleet JSONL (optional wow factor)

```powershell
python -m platform_core.demo_fleet --data-dir platform_data_fleet_demo --reset
$env:PLATFORM_DATA_DIR = "$(Get-Location)\platform_data_fleet_demo"
```

## 2 — Start API

```powershell
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Smoke (new tab):

```text
GET http://127.0.0.1:8000/platform/health
```

Try canonical ingest aliases:

```text
POST /platform/ingest/heartbeat   (operator header)
POST /platform/ingest/snapshot
POST /platform/ingest/failure-event
```

## 3 — Next.js dashboard

```powershell
cd frontend
copy .env.local.example .env.local   # if present
# set NEXT_PUBLIC_PLATFORM_API=http://127.0.0.1:8000
npm install
npm run dev
```

Open `/platform`.

## 4 — Agent observe-only sync

Dry HTTP first:

```powershell
python -m endpoint_agent --once --dry-run --api http://127.0.0.1:8000
```

Then allow POST with retry/backoff (still **no repairs**):

```powershell
python -m endpoint_agent --once --api http://127.0.0.1:8000
```

## 5 — Remediation posture check

Always expect **`dry_run` default** on `POST /platform/remediation/execute`. Attempt **`reset_firewall`** preview + execute should surface **`blocked`** or dry-run semantics—correlate with `platform_data/remediation_executions.jsonl` and `audit.jsonl`.

## Talk track

> “We collect locally, attribute honestly, policy-gate previews, audit before subprocess, and block high-risk actions from the API path—while leaving beginner `.bat` scripts unchanged.”
