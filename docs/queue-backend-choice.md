# Queue backend choice

**Phase 4 selection:** Redis + **RQ** behind a `QueueBackend` protocol.

## Why RQ

- Minimal Python API — one Redis connection, one worker process
- JSON-serializable job args match evidence `event_id` payloads
- Easy local demo via `docker compose` worker service
- Sufficient for portfolio-scale classification throughput

## Abstraction

`backend/queue/protocol.py` defines `QueueBackend` so a future `DramatiqQueueBackend` or `CeleryQueueBackend` can swap without changing:

- `backend/v1_routes.py` ingestion
- `backend/workers/classifier_worker.py` domain logic

## Migration triggers

Consider **Dramatiq** or **Celery** when:

- Scheduled/cron classification jobs are required
- Fan-out to multiple worker types (export, SIEM, Power BI refresh)
- Kubernetes HPA on queue depth becomes a requirement
- Dead-letter queues need enterprise tooling integration

## Tests without Redis

`QUEUE_BACKEND=memory` + `TRISK_SYNC_CLASSIFY=1` runs classification inline for CI.
