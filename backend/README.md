# Backend (FastAPI)

## Run locally (Windows)

Use the **project virtual environment**. If `uvicorn` comes from another venv (e.g. Hermes agent), imports like `stripe` will fail even though this repo lists them in `pyproject.toml`.

```powershell
# From repo root — one-time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start API (fixture-safe demo)
$env:PYTHONPATH = (Get-Location).Path
$env:PLATFORM_FIXTURE_MODE = "1"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Or use the helper script:

```powershell
.\scripts\run-backend.ps1
.\scripts\run-backend.ps1 -Reload
```

Open **http://127.0.0.1:8000/docs** for OpenAPI. Technology-risk routes live under `/v1/*`.

## Run locally (Unix / Make)

```bash
pip install -r requirements.txt
make demo-api
```

## Environment

Copy `.env.example` to `.env` and set as needed:

- `SUPABASE_JWT_SECRET` — SaaS JWT routes (`/diagnose`, `/history`)
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` — billing demo only
- `TRISK_API_TOKEN` — `/v1/*` demo token (default `dev-trisk-token`)
- `CORS_ALLOW_ORIGINS` — comma-separated origins for hosted UIs

Billing routes return **503** when the `stripe` package is missing; `/v1/*` and `/platform/*` still load.

## Deploy

- Railway or Render (recommended for MVP)
- Set env vars in hosting dashboard
- Use managed Postgres/Supabase for production (SQLite is local MVP default)
