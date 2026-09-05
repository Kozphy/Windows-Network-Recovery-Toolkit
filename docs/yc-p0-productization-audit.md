# YC P0 Productization Audit

## Goal

Evolve the existing Technology Risk & Control Analytics Platform into a product that a real IT team can enroll endpoints into without weakening the existing evidence, policy, approval, audit, or dry-run safety boundaries.

## Reusable foundations already present

- FastAPI control plane in `backend/`
- SQLModel persistence with SQLite/Postgres-compatible configuration
- Existing `Endpoint` model and technology-risk evidence tables
- `/v1` authentication dependency and role model
- Deterministic evidence ingestion/classification pipeline
- Human review and policy-gated remediation boundaries
- Append-only/hash-linked audit support
- Docker/CI/observability foundations

## P0 gaps found

1. No expiring/revocable endpoint enrollment credential
2. No durable per-agent credential after bootstrap
3. No authenticated heartbeat persistence
4. No product-facing organization creation flow under `/v1`
5. No tenant-scoped product endpoint listing
6. No explicit distinction between liveness and evidence-backed health
7. No focused tests for enrollment replay, heartbeat idempotency, or tenant fleet isolation

## Implemented vertical slice

`Organization -> Enrollment Token -> Agent Enrollment -> Durable Endpoint Identity -> Heartbeat -> Endpoint Listing`

### Added tables

- `product_organizations`
- `product_enrollment_tokens`
- `product_agent_credentials`
- `product_agent_heartbeats`

The existing `trisk_endpoints` table remains the canonical endpoint identity table.

### Added API routes

- `POST /v1/organizations`
- `POST /v1/enrollment-tokens`
- `POST /v1/enrollment-tokens/{token_id}/revoke`
- `POST /v1/agents/enroll`
- `POST /v1/agents/heartbeat`
- `GET /v1/endpoints`

## Security decisions

- Organization IDs are not accepted from organization/enrollment request bodies; the authenticated principal determines the tenant context.
- Enrollment tokens expire, are revocable, and are single-use by default.
- Enrollment and agent secrets are returned only at issuance and stored as hashes.
- A deployment pepper (`TRISK_AGENT_TOKEN_PEPPER`) is supported and should be independently generated in deployed environments.
- Agent heartbeat authentication is separate from operator `/v1` authentication.
- Endpoint listing filters server-side by the authenticated tenant context.
- Enrollment/revocation events are appended to the existing audit chain.
- A heartbeat reports `ONLINE_UNASSESSED`; it never upgrades an endpoint to `HEALTHY` without evidence.

## Known limitations

- `/v1` operator authentication is still the repository's demo API-token/header model; tenant context currently comes from that authenticated principal abstraction. Production identity-provider membership claims are a later P0/P1 hardening item.
- `SQLModel.metadata.create_all()` remains the local/demo schema bootstrap. A proper migration revision should be added before production deployment.
- Agent credentials are long-lived hashes in this slice; rotation/revocation endpoints are next.
- No signed binary/package trust or update channel yet.
- No evidence ingestion tied to the newly enrolled agent credential yet.
- No customer-facing dashboard in this slice.

## P0 priority after this PR

### Next vertical slice

`Authenticated agent evidence upload -> tenant-bound deterministic finding -> incident creation -> endpoint detail/fleet summary`

Acceptance criteria:

1. Agent credential can submit evidence only for its own endpoint.
2. Server ignores/rejects attempts to submit another endpoint or organization ID.
3. Evidence rows inherit organization scope from the credential.
4. Existing deterministic classifier creates a finding/incident.
5. Fleet endpoint detail exposes evidence-backed state separately from liveness.
6. Tests cover cross-tenant and cross-endpoint injection attempts.

## Not done intentionally

- Kubernetes
- microservice split
- billing expansion
- autonomous remediation
- AI-authorized execution
- synthetic traction claims

The objective is a working customer path, not additional enterprise-looking surface area.
