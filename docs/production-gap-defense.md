# Production gap defense (cross-cutting Q&A)

Quick answers when reviewers challenge "is this production?"

## Is this deployed in enterprise?

**No.** It is a portfolio-grade, production-**shaped** prototype with Docker Compose, Postgres persistence, async workers, RBAC, metrics, and abuse-case tests.

## Why Postgres + JSONL dual-write?

- Postgres: queryable incidents for `/v1` API and executive reports
- JSONL: portable audit chain for offline `audit verify` and committee exports
- Enterprise gap: unified WORM storage + legal hold

## Why RQ not Kafka?

Sufficient for demo throughput; `QueueBackend` abstraction documents migration triggers — [queue-backend-choice.md](queue-backend-choice.md).

## Why demo tokens?

Fast reviewer path. Production needs Entra ID / OAuth2 — [rbac-model.md](rbac-model.md).

## Scorecard summary

| Area | Current | Target (enterprise) |
|------|---------|---------------------|
| Persistence | Postgres + SQLite tests | HA + backup |
| Async | RQ + Redis | K8s workers + DLQ |
| RBAC | Header tokens | SSO + ABAC |
| Observability | Prometheus counters | OTel + SLO dashboards |
| Security tests | Abuse suite in CI | Pen test + SOC2 mapping |
| Runbooks | Documented | On-call integrated |

Full matrix: [production-readiness-scorecard.md](production-readiness-scorecard.md)

## Interview close (both audiences)

"We built the **shape** of a technology risk pipeline — evidence ingestion, deterministic classification, control tests, human review, audit verify, and governance export — with explicit boundaries so it cannot be mistaken for EDR or autonomous repair."
