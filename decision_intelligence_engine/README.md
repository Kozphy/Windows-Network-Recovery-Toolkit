# Decision Intelligence / AI Governance Engine

A production-shaped portfolio service for **evidence-backed decision support**. It separates facts, assumptions, and unknowns; scores options deterministically; penalizes risk and uncertainty; produces a recommendation; requires a **human approval/rejection step**; and records the workflow in a tamper-evident hash-chain audit log.

> AI can explain or enrich evidence later, but it does not authorize execution. Human approval is a hard boundary.

## Decision flow

```text
Evidence -> Assumptions/Unknowns -> Criteria -> Option Scoring
         -> Risk + Uncertainty Penalties -> Recommendation
         -> Human Approval/Reject -> Action Boundary -> Verification -> Audit Trail
```

## Why this belongs in this repository

The parent platform already demonstrates evidence collection, control testing, policy gates, remediation previews, and audit trails. This module generalizes that pattern into a reusable **multi-domain decision governance engine** suitable for technology risk, FinOps, compliance, operations, and AI-assisted workflows.

## Governance properties

- **Evidence provenance:** facts can include a source and confidence.
- **Explicit uncertainty:** assumptions and unknowns are first-class data.
- **Deterministic baseline:** recommendation scores are reproducible without an LLM.
- **Risk-aware ranking:** risk and uncertainty lower the adjusted score.
- **Human-in-the-loop:** recommendations can never directly approve themselves.
- **Auditability:** recommendation and human-decision events are hash chained.
- **Tamper detection:** the audit verifier detects changed or reordered rows.
- **Honest confidence:** confidence is a heuristic based on evidence coverage and score margin, not a calibrated probability.

## API

```text
GET  /health
POST /v1/decisions/analyze
POST /v1/decisions/{decision_id}/human-decision
GET  /v1/audit/verify
```

### Run

```bash
cd decision_intelligence_engine
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

### Analyze a decision

```bash
curl -X POST http://127.0.0.1:8000/v1/decisions/analyze \\
  -H "Content-Type: application/json" \\
  --data @example_request.json
```

The response has `status: pending_human_review` and `requires_human_approval: true`.

### Record the human decision

```bash
curl -X POST http://127.0.0.1:8000/v1/decisions/<decision_id>/human-decision \\
  -H "Content-Type: application/json" \\
  -d '{"approver":"reviewer@example","action":"approve","rationale":"Evidence is sufficient and rollback is available."}'
```

## Scoring model

For each option:

```text
utility = weighted mean of criterion scores
adjusted = utility - risk_penalty*risk - uncertainty_penalty*uncertainty
```

All criterion scores, risk, and uncertainty are normalized to `[0, 1]`. The highest adjusted score becomes the recommendation. This is intentionally simple and inspectable; domain-specific models can be plugged in later.

## Tests

```bash
pytest -q
```

The initial tests verify that recommendations remain human-gated and that audit-chain tampering is detected.

## Next production upgrades

1. Persist decisions in PostgreSQL with immutable event IDs.
2. Add RBAC and separation-of-duties for requester/reviewer/approver roles.
3. Add policy-as-code gates for prohibited autonomous actions.
4. Add an LLM explanation adapter that consumes only approved evidence and never changes approval state.
5. Add calibrated confidence/evaluation datasets and benchmark decision quality.
6. Add OpenTelemetry traces, Prometheus metrics, and governance dashboards.
7. Add outcome verification so recommendations can be compared with realized results.

## Non-claims

This prototype is not a formal audit opinion, not a calibrated risk model, and not an autonomous decision-maker. It is a transparent decision-support and governance skeleton designed to make evidence, uncertainty, human accountability, and auditability explicit.
