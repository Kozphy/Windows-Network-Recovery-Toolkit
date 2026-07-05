# Senior platform review (Staff / platform engineering)

Answers for production-system portfolio reviewers. **Not enterprise-deployed** — honest prototype boundaries throughout.

## 1. What production risks remain?

- Demo token auth (`X-Api-Token`) — no SSO/mTLS
- Single-node Postgres/Redis — no HA or backup automation in compose
- RQ worker is one process — no K8s HPA, no DLQ enterprise integration
- SLOs are aspirational — see [service-level-objectives.md](service-level-objectives.md)

## 2. Malformed evidence?

- Pydantic validation on `POST /v1/evidence` → 422 with field errors
- Worker quarantine path → `classification_status=quarantined`
- Tests: `tests/backend/test_malformed_evidence_quarantine.py`, `tests/security/test_abuse_cases.py`

## 3. Unsafe remediation?

- No `/v1` remediation execute routes
- Policy registry blocks kill/firewall/adapter disable
- Even `admin` role cannot bypass — `tests/security/test_policy_bypass_blocked.py`

## 4. Audit verify failure?

- `GET /v1/audit/verify` runs `verify_chain` on JSONL path
- DB `AuditChainEntry` dual-write; tamper → verification failure metric
- Runbook: [operational-runbook.md](operational-runbook.md)

## 5. AI constraints?

- Explanation guardrails block malware/MITM/autonomous language
- AI does not approve human review — `human_review.py`
- `tests/security/test_prompt_injection_guardrails.py`

## 6. SLOs?

- Documented targets for demo stack only — not attested
- Metrics: `classification_latency_seconds`, ingest counters on `/metrics`

## 7. Worker failure?

- RQ retries (bounded); poison → quarantine
- Redis down → ingest may 202 but job stalls — runbook Redis section
- `QUEUE_BACKEND=memory` + `TRISK_SYNC_CLASSIFY=1` for CI inline path

## 8. Duplicate events?

- `content_hash` + unique `event_id` idempotency
- `tests/backend/test_idempotency.py`

## 9. Known gaps?

- [production-readiness-scorecard.md](production-readiness-scorecard.md)
- [production-readiness-gap.md](production-readiness-gap.md)

## 10. Enterprise deploy path?

1. Entra ID OAuth for `/v1`
2. Managed Postgres + Redis (Azure Cache / Elasticache)
3. K8s deployments for API + worker with HPA on queue depth
4. Formal retention/legal hold — [data-retention-policy.md](data-retention-policy.md)
5. SIEM export from audit chain — not implemented

**Architecture:** [production-architecture.md](production-architecture.md) · **Compose:** [docker-production-shaped-demo.md](docker-production-shaped-demo.md)
