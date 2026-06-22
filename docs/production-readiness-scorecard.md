# Production Readiness Scorecard

Weighted self-assessment for senior reviewer conversations. **Not a certification.**

| Area | Weight | Current (portfolio) | Target (enterprise) | Score /10 |
|------|--------|---------------------|---------------------|-----------|
| Durable storage | 15% | Postgres + SQLModel `/v1` | Multi-AZ, backups | 6 |
| Async processing | 15% | RQ + abstraction | K8s autoscale workers | 6 |
| Fleet ingestion | 10% | `/v1/evidence` + fleet-benchmark | Signed agent fleet | 5 |
| API contract | 10% | Versioned `/v1` OpenAPI | SLA + rate limits | 7 |
| RBAC | 10% | Demo token headers | Entra ID + mTLS | 5 |
| Observability | 10% | Prometheus + Grafana JSON | SLO dashboards + tracing | 6 |
| Performance benchmarks | 5% | fleet-benchmark markdown | CI gates on p95 | 6 |
| Security abuse tests | 10% | `tests/security/*` | Pen test + STRIDE | 7 |
| Runbooks | 5% | operational-runbook.md | PagerDuty linked | 5 |
| Honest non-claims | 10% | CI safety contracts | Legal review of exports | 9 |

**Composite (illustrative):** ~6.2 / 10 — production-**shaped**, not production-**certified**.

## Pass criteria for senior demo

- [ ] `make prod-demo-up` healthy
- [ ] `POST /v1/evidence` returns 202 with idempotency
- [ ] Worker classifies without duplicate incidents
- [ ] `GET /metrics` exposes trisk counters
- [ ] `fleet-benchmark --endpoints 1000` completes
- [ ] `pytest -q tests/security` passes
- [ ] Governance report states management information only

See [production-readiness-gap.md](production-readiness-gap.md) for detailed gap table.
