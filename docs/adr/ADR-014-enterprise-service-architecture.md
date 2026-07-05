# ADR-014: Enterprise Service-Oriented Decision Platform

## Status

Accepted — 2026-06-12

## Context

The toolkit accumulated multiple API surfaces (`/platform/*`, `/v1/*`, `/trisk/*`, `/decision-intelligence/*`) and fragmented persistence. Enterprise technology risk teams need a single **decision infrastructure** with auditability, explainability, governance, and multi-tenant operation — without chatbot/RAG/autonomous remediation scope creep.

## Decision

Introduce a **service-oriented layer** under `backend/services/` exposed via `/v1/enterprise/*`:

1. Evidence Service
2. Risk Classification Service
3. Policy Engine Service (YAML + canonical evaluator)
4. Audit Service (tenant hash chain)
5. Reporting Service

Implement the pipeline:

**Observation → Hypothesis → Evidence → Confidence → Decision → Audit**

PostgreSQL schemas: evidence (extended), hypotheses, decisions, controls (existing), audit_logs.

Multi-tenant via `X-Api-Tenant` + `trisk_tenants`. RBAC extends existing `V1Role` matrix.

## Consequences

### Positive

- Clear service boundaries for committee and auditor conversations
- Policy-as-code per tenant without code deploys
- Hash-chained audit logs with correlation IDs
- OpenAPI-documented FastAPI surface
- Reuses deterministic classifier — no LLM authority

### Negative

- Parallel to legacy `/v1` ingest until clients migrate
- SQLite tests lack Postgres RLS — tenant isolation is application-layer only
- Human review still dual-writes possible (JSONL + DB) until Phase 4 unification

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Microservices per service | Operational overhead exceeds portfolio scope |
| Single monolithic `decision.py` | Poor testability and auditor explainability |
| LLM orchestration layer | Violates no-autonomous-AI-authority constraint |
| Replace all `/v1` routes | Breaking change for existing 1476+ test portfolio |

## Compliance

- No autonomous remediation endpoints added
- All decisions include `limitations[]`
- Human approval required for critical classifications per YAML policy
