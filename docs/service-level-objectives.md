# Service Level Objectives

**Disclaimer:** Aspirational targets for the **local production-shaped demo stack**. Not attested SLAs.

## API availability (demo)

| SLI | Target | Measurement |
|-----|--------|-------------|
| `/trisk/health` success | 99.9% during demo window | Docker healthcheck |
| `/v1/evidence` 2xx/4xx (not 5xx) | 99.5% | Prometheus `http_requests` |

## Ingestion latency

| SLI | Target (demo) | Notes |
|-----|---------------|-------|
| Evidence persist p95 | &lt; 200 ms | SQLite/Postgres local |
| Classification job queued p95 | &lt; 50 ms | Redis local |
| End-to-end classify p95 | &lt; 5 s | Worker + deterministic pipeline |

## Worker reliability

| SLI | Target | Mitigation |
|-----|--------|------------|
| Job success after retries | &gt; 99% on valid evidence | Bounded retry policy |
| Poison message rate | &lt; 0.1% | Quarantine status |
| Duplicate incident rate | 0% | Idempotency keys |

## Audit integrity

| SLI | Target |
|-----|--------|
| `verify_chain` pass on clean export | 100% |
| Tamper detection | 100% on altered rows |

## Error budget (portfolio)

Demo stack may be restarted freely. No production error budget applies.

## Gaps vs enterprise SLOs

- No multi-AZ failover
- No on-call paging integration
- No SLO dashboards in customer tenant
