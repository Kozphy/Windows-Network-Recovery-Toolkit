# ADR-015: Idempotent delivery, bounded retry, and backpressure

## Status

Accepted for the portfolio reference implementation; production broker/storage technology remains undecided.

## Context

A future fleet control plane may use at-least-once delivery. Redelivery is normal under consumer restart, acknowledgement loss, timeout, or partition recovery. The dangerous failure is not duplicate computation; it is duplicate **side effect** such as applying the same governed remediation twice.

Unbounded retry is also unsafe. A poison message can create a retry storm, consume worker capacity, increase queue age, and starve healthy work.

## Decision

Define transport-independent semantics before choosing infrastructure:

1. Every governed effect carries a stable `idempotency_key`.
2. Completion is recorded only after a successful effect.
3. A completed key suppresses later duplicate effects.
4. Transient errors retry only up to a configured `max_attempts`.
5. Permanent errors and exhausted transient errors go to a dead-letter queue.
6. Retry queues are bounded. Saturation returns explicit `BACKPRESSURE`; the producer/consumer must slow, reject, or shed according to policy rather than growing memory without bound.
7. Delivery semantics are observable through counts for ACK, RETRY, DLQ, DUPLICATE, and BACKPRESSURE.

Reference implementation: `windows_network_toolkit/distributed_delivery.py`.

## Atomicity limitation

The local ledger is not a distributed transaction. A crash after an external effect succeeds but before the completion ledger is durably written can still cause a duplicate effect on redelivery. Production designs must close this gap using an idempotent downstream API, transactional inbox/outbox, database transaction boundary, or equivalent mechanism.

This ADR therefore does **not** claim exactly-once delivery.

## Alternatives considered

### Rely on broker exactly-once features

Rejected as the sole guarantee. Broker transaction semantics do not automatically make arbitrary external side effects exactly once.

### Infinite retry

Rejected. Poison messages can monopolize capacity and destroy recovery time.

### Unbounded in-memory queue

Rejected. It converts overload into memory exhaustion and hides backpressure from callers.

### Drop duplicates by `event_id` only

Insufficient. The same business effect can be represented by redelivered or regenerated messages. The idempotency boundary should correspond to the governed side effect/decision identity.

## Consequences

- Redelivery is expected and safe only when side effects are idempotent.
- DLQ is an operational workflow, not a trash can; replay requires review and reason tracking.
- Queue depth/utilization becomes an SRE signal.
- Backpressure must propagate rather than be silently converted into latency or memory growth.
- Production implementation technology remains an evidence-driven choice.

## Verification

```bash
pytest -q tests/platform_core/evaluation/test_distributed_delivery.py
pytest -q tests/platform_core/evaluation/test_concurrency_benchmark.py
```

See also: [../distributed-delivery-semantics.md](../distributed-delivery-semantics.md) and [ADR-008](ADR-008-fleet-scale-100k-endpoints.md).
