# AI Technology Risk & Recovery Platform

This directory is the first end-to-end AI application layer for the Windows Network Recovery Toolkit.

## What this adds

- FastAPI backend for incidents, agent chat, approvals, and audit events.
- Deterministic agent orchestration with grounded retrieval and structured tool proposals.
- Human approval gates for state-changing recovery actions.
- Regression eval cases that verify tool selection, approval policy, and evidence retrieval.
- React/Vite frontend in `../web` for chat, evidence review, and approve/reject flows.
- GitHub Actions workflow that runs API tests, AI regression evals, and the frontend build.

## Architecture

```text
React UI
   |
FastAPI
   |
Agent Orchestrator
   |---- Retrieval / grounded evidence
   |---- Structured tool proposal
   |---- Risk classification
   |---- Human approval gate
   `---- Audit events
```

The current retrieval and agent policies are intentionally deterministic baselines. They provide a testable contract before introducing an external LLM, vector database, hybrid retrieval, or production remediation executor.

## Run backend

```bash
cd ai_app
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Run tests and evals

```bash
cd ai_app
pytest -q
python evals/run_eval.py
```

## Run frontend

```bash
cd web
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000`. Set `VITE_API_URL` to point it at another API endpoint.

## Next production upgrades

1. Replace keyword retrieval with hybrid/vector retrieval and source citations.
2. Add an LLM adapter with structured outputs and provider-independent interfaces.
3. Persist conversations, incidents, approvals, and audit events in PostgreSQL.
4. Add Redis-backed state/queues for asynchronous tool execution.
5. Connect the agent tool registry to the toolkit's existing diagnostics and verification logic.
6. Add retrieval metrics, task success, safety-policy violations, latency, and cost to eval reports.
7. Add authentication, authorization, rate limits, secrets management, observability, and cloud deployment.
