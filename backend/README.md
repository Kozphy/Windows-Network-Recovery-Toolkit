# Backend (FastAPI)

## Run locally

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment

Copy `.env.example` to `.env` and set:

- `SUPABASE_JWT_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

## Deploy

- Railway or Render (recommended for MVP)
- Set env vars in hosting dashboard
- Use managed Postgres/Supabase for production (SQLite is local MVP default)
