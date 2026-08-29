# Decision Intelligence / AI Governance Engine

A production-shaped service for **evidence-backed, human-governed decision support**. It separates facts, assumptions, and unknowns; scores options deterministically; applies versioned policy-as-code; requires independent approval and verification; persists the lifecycle; evaluates confidence calibration; exposes Prometheus metrics and OpenTelemetry hooks; and records replayable governance events in a tamper-evident hash chain.

> AI may explain or enrich evidence later, but it does not authorize execution. Identity, policy gates, human approval, separation of duties, and outcome verification are hard boundaries.

## v0.3 architecture

```text
Authenticated requester
        ↓
Evidence / provenance
        ↓
Facts · Assumptions · Unknowns
        ↓
Deterministic scoring
        ↓
Risk + uncertainty penalties
        ↓
Versioned policy bundle
        ↓
Recommendation + policy flags
        ↓
Authenticated independent approver
        ↓
Approved action boundary
        ↓
Authenticated independent verifier
        ↓
Outcome + calibration evaluation
        ↓
SQL persistence · Prometheus · OpenTelemetry · replayable hash-chain audit
```

## Governance controls

- **Signed identity boundary** — `DI_AUTH_MODE=jwt` validates signed JWTs, issuer, audience, expiry, subject, and roles.
- **Role enforcement** — API routes require `requester`, `approver`, `verifier`, or `auditor` roles.
- **Identity-derived accountability** — requester/approver/verifier identities come from the authenticated principal, not trusted JSON fields.
- **Separation of duties** — requester cannot approve their own recommendation; verifier must differ from requester and approver.
- **Versioned policy-as-code** — thresholds and blocking flags live in `policies/v1.json` and are loaded at runtime.
- **Durable persistence** — SQLite by default; PostgreSQL supported through `DI_DATABASE_URL`.
- **Schema migrations** — Alembic configuration and an initial decisions-table migration are included.
- **Calibration evaluation** — Brier score and expected calibration error (ECE) are exposed as an evaluation API.
- **Replayability** — lifecycle events can be reconstructed by decision ID only after the audit hash chain verifies.
- **Observability** — Prometheus metrics plus optional OpenTelemetry spans.
- **Human-in-the-loop invariant** — recommendation output always requires human approval.

## API

```text
GET  /health
GET  /metrics
POST /v1/decisions/analyze
GET  /v1/decisions/{decision_id}
POST /v1/decisions/{decision_id}/human-decision
POST /v1/decisions/{decision_id}/outcome
GET  /v1/decisions/{decision_id}/replay
POST /v1/evaluation/calibration
GET  /v1/audit/verify
```

## Run locally

```bash
cd decision_intelligence_engine
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

## Development identities

Authentication is disabled by default for local development. Use headers to simulate independent principals:

```text
X-DI-Subject: requester@example.com
X-DI-Roles: requester
```

Use different subjects for approval and verification. This preserves the separation-of-duties demo without requiring an identity provider.

## JWT production mode

```text
DI_AUTH_MODE=jwt
DI_JWT_SECRET=<secret>
DI_JWT_ISSUER=https://issuer.example
DI_JWT_AUDIENCE=decision-engine
DI_JWT_ALGORITHM=HS256
```

A valid JWT must contain `sub`, `iat`, `exp`, and a `roles` claim. The current implementation is a signed JWT boundary suitable for a portfolio prototype; OIDC discovery/JWKS rotation remains future production work.

## Persistence and migrations

Default database:

```text
sqlite:///data/decisions.db
```

PostgreSQL:

```bash
pip install -e ".[postgres]"
export DI_DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/decision_intelligence'
alembic upgrade head
```

## Policy bundles

The default bundle is `policies/v1.json`. It declares a semantic version, thresholds, and blocking flags. `DI_POLICY_PATH` can select another versioned bundle without changing scoring code.

Current signals include:

```text
LOW_EVIDENCE_COVERAGE
LOW_CONFIDENCE
MATERIAL_UNKNOWNS
HIGH_RISK_RECOMMENDATION
```

`LOW_EVIDENCE_COVERAGE` and `HIGH_RISK_RECOMMENDATION` block approval in v1.

## Evaluation

`POST /v1/evaluation/calibration` accepts historical confidence/outcome pairs and reports:

```text
Brier score
Expected Calibration Error (ECE)
Sample count
```

This does **not** make the current confidence heuristic a calibrated probability; it creates the measurement harness needed to test calibration honestly.

## Replay and audit

`GET /v1/decisions/{decision_id}/replay` returns matching lifecycle events only when the complete SHA-256 hash chain verifies. A modified or reordered record causes replay to fail closed.

## Observability

Prometheus metrics are available at `/metrics`. Set `DI_OTEL_ENABLED=true` to create OpenTelemetry spans around decision analysis. Exporter/backend wiring is intentionally environment-specific.

## Tests

```bash
pytest -q
```

The suite covers human approval invariants, versioned policy blocking, durable persistence, tamper detection and replay, calibration metrics, and signed JWT identity/role decoding.

## Next production upgrades

1. OIDC discovery + asymmetric JWKS key rotation instead of shared-secret JWT validation.
2. PostgreSQL integration tests in CI and migration drift checks.
3. Policy bundle signatures, approval workflow, and policy-version capture on each decision record.
4. LLM explanation adapter with read-only evidence access and immutable governance state.
5. Larger calibration/decision-quality benchmark datasets with confidence intervals.
6. OTLP exporter + Grafana governance dashboards and SLOs.
7. Dedicated event store with immutable event IDs, idempotency keys, and concurrency controls.

## Non-claims

This prototype is not a formal audit opinion, not a calibrated risk model, and not an autonomous decision-maker. It is a transparent governance system designed to make evidence, uncertainty, identity, policy enforcement, human accountability, post-decision verification, and auditability explicit.
