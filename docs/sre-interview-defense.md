# SRE interview defense

Production-shaped **demo** stack for SRE reviewers — not a live SLO-attested service.

## On-call scenarios

| Alert (conceptual) | First action | Doc |
|--------------------|--------------|-----|
| API unhealthy | `curl /health`, check compose logs | [operational-runbook.md](operational-runbook.md) |
| Worker backlog | `redis-cli LLEN rq:queue:trisk`, scale worker replicas | [queue-backend-choice.md](queue-backend-choice.md) |
| Postgres full | Vacuum/retention; demo retention policy | [data-retention-policy.md](data-retention-policy.md) |
| Audit verify fail | Stop ingest; compare JSONL vs DB chain | runbook |

## Metrics to watch

- `evidence_events_ingested_total`
- `classification_latency_seconds` (sum/count)
- `worker_job_failures_total`
- `human_review_queue_depth`
- `unknown_classification_ratio` (gauge)

Grafana: `observability/grafana/technology-risk-dashboard.json`

## Blast radius

- No autonomous remediation — worst case is bad classification + human review queue
- Policy blocks destructive registry mutations

## Load testing

```powershell
make prod-demo-benchmark
python -m windows_network_toolkit fleet-benchmark --scenario duplicate_event_replay --endpoints 500 --seed 1
```

## What we would add for production

- Multi-AZ Postgres, Redis Sentinel
- OpenTelemetry traces API → queue → worker
- Error budget policy tied to classification p95
- PagerDuty on `audit_chain_verification_failures_total`

See [senior-platform-review.md](senior-platform-review.md) for cross-role Q&A.
