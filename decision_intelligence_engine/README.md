# Decision Intelligence / AI Governance Engine

A production-shaped service for **evidence-backed, human-governed decision support**. It separates facts, assumptions, and unknowns; scores options deterministically; penalizes risk and uncertainty; evaluates policy-as-code controls; requires an independent human approval/rejection step; persists the lifecycle; verifies outcomes; exposes Prometheus metrics; and records governance events in a tamper-evident hash-chain audit log.

> AI may explain or enrich evidence later, but it does not authorize execution. Human approval and separation of duties are hard boundaries.

## v0.2 architecture

```text
Evidence / provenance
        ↓
Facts · Assumptions · Unknowns
        ↓
Deterministic scoring
        ↓
Risk + uncertainty penalties
        ↓
Policy-as-code evaluation
        ↓
Recommendation + policy flags
        ↓
Independent human approval/rejection
        ↓
Approved action boundary
        ↓
Independent outcome verification
        ↓
SQL persistence + Prometheus metrics + hash-chain audit trail
```

## Governance controls

- **Evidence provenance** — facts can carry source and confidence.
- **Explicit uncertainty** — assumptions and unknowns are first-class data.
- **Deterministic baseline** — recommendation scores are reproducible without an LLM.
- **Policy-as-code** — low evidence coverage and high-risk recommendations can block approval.
- **Separation of duties** — the requester cannot approve their own recommendation.
- **Independent verification** — the outcome verifier must differ from both requester and approver.
- **Durable persistence** — SQLite by default; PostgreSQL is supported through `DI_DATABASE_URL`.
- **Observability** — Prometheus counters and confidence histograms are exposed at `/metrics`.
- **Auditability** — recommendation, blocked approval, human decision, and outcome events are hash chained.
- **Honest confidence** — confidence remains a heuristic, not a calibrated probability.

## API

```text
GET  /health
GET  /metrics
POST /v1/decisions/analyze
GET  /v1/decisions/{decision_id}
POST /v1/decisions/{decision_id}/human-decision
POST /v1/decisions/{decision_id}/outcome
GET  /v1/audit/verify
```

## Run locally

```bash
cd decision_intelligence_engine
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

Default persistence uses:

```text
sqlite:///data/decisions.db
```

For PostgreSQL:

```bash
pip install -e ".[postgres]"
export DI_DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/decision_intelligence'
```

## Example workflow

Analyze:

```bash
curl -X POST http://127.0.0.1:8000/v1/decisions/analyze \\
  -H "Content-Type: application/json" \\
  --data @example_request.json
```

The response always includes:

```json
{
  "requires_human_approval": true,
  "status": "pending_human_review",
  "policy_flags": []
}
```

Approve or reject using an independent reviewer:

```bash
curl -X POST http://127.0.0.1:8000/v1/decisions/<decision_id>/human-decision \\
  -H "Content-Type: application/json" \\
  -d '{"approver":"risk-reviewer@example.com","action":"approve","rationale":"Evidence is sufficient and rollback is available."}'
```

Verify the realized outcome using a third person/service identity:

```bash
curl -X POST http://127.0.0.1:8000/v1/decisions/<decision_id>/outcome \\
  -H "Content-Type: application/json" \\
  -d '{"verifier":"control-testing@example.com","outcome":"successful","notes":"Target KPI improved after rollout.","realized_value":0.18}'
```

## Scoring model

```text
utility = weighted mean of criterion scores
adjusted = utility - risk_penalty*risk - uncertainty_penalty*uncertainty
```

All criterion scores, risk, and uncertainty are normalized to `[0, 1]`. The model is intentionally inspectable. The selected recommendation then passes through governance policy checks before a human can approve it.

## Policy-as-code defaults

Current default flags include:

```text
LOW_EVIDENCE_COVERAGE
LOW_CONFIDENCE
MATERIAL_UNKNOWNS
HIGH_RISK_RECOMMENDATION
```

`LOW_EVIDENCE_COVERAGE` and `HIGH_RISK_RECOMMENDATION` block approval by default. Other flags remain review signals.

## Tests

```bash
pytest -q
```

The suite covers the human-approval invariant, policy blocking, durable SQL persistence, and audit-chain tamper detection.

## Next upgrades

1. Replace identity strings with OIDC/JWT authentication and explicit RBAC roles.
2. Add Alembic migrations and PostgreSQL integration tests.
3. Move governance thresholds to versioned external policy bundles.
4. Add an LLM explanation adapter that cannot mutate recommendation or approval state.
5. Add calibration datasets, Brier/ECE-style confidence evaluation, and decision-quality benchmarks.
6. Add OpenTelemetry traces and Grafana governance dashboards.
7. Add immutable event IDs and event-sourced replay for the full lifecycle.

## Non-claims

This prototype is not a formal audit opinion, not a calibrated risk model, and not an autonomous decision-maker. It is a transparent governance skeleton designed to make evidence, uncertainty, accountability, policy enforcement, and post-decision verification explicit.
