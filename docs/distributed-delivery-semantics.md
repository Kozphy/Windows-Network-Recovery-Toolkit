# Distributed delivery semantics

This repository now includes a dependency-light reference implementation for the semantics that matter before choosing Kafka, Redis, NATS, Service Bus, Pub/Sub, or another broker.

## Contract

`windows_network_toolkit/distributed_delivery.py` models:

- **At-least-once delivery tolerance**: a message may be redelivered.
- **Idempotent side effects**: `idempotency_key` is checked against a completed-effect ledger; duplicate delivery returns `DUPLICATE` rather than executing the side effect twice.
- **Retry classification**: transient failures are retried; permanent failures are dead-lettered immediately.
- **Bounded retry**: `max_attempts` prevents infinite poison-message loops.
- **Dead-letter queue**: exhausted transient failures and permanent failures are isolated for review/replay.
- **Backpressure**: bounded queues return `BACKPRESSURE` instead of accepting unbounded memory growth.

## Important ordering rule

The ledger records **effect completion**, not receipt. Marking a key completed before the side effect succeeds can lose work. Marking it only after success means a crash between the external side effect and durable ledger write is still a production concern; solving that requires a transactional outbox/inbox, an idempotent downstream API, or another atomicity boundary.

That limitation is intentional and should be stated in interviews.

## Delivery state flow

```text
receive
  |
  +-- key already completed --> DUPLICATE / ACK without side effect
  |
  +-- execute side effect
        |
        +-- success ----------------> mark completed --> ACK
        +-- permanent failure ------> DLQ
        +-- transient failure
              |
              +-- attempts exhausted --> DLQ
              +-- retry queue full ----> BACKPRESSURE
              +-- capacity available --> RETRY
```

## Why this is stronger than saying “use Kafka exactly-once”

Broker delivery guarantees do not automatically make external side effects exactly once. A consumer can still crash after changing a registry/database/external system and before acknowledging the message. The application therefore needs an idempotency boundary tied to the business effect.

Interview-safe wording:

> The transport can be at least once. I require the governed side effect to be idempotent. Redelivery can recompute a deterministic decision, but the same idempotency key must not produce a second mutation. Retry queues are bounded, poison messages terminate in a DLQ, and queue saturation is explicit backpressure rather than silent memory growth.

## What this does not prove

This is a local semantic model, not a production broker implementation. It does not prove multi-host durability, broker replication, transactional exactly-once behavior, network partition handling, or a production retry SLO.

## Tests

```bash
pytest -q tests/platform_core/evaluation/test_distributed_delivery.py
```

The tests demonstrate duplicate suppression, bounded retry, DLQ routing, permanent failure handling, and backpressure.
