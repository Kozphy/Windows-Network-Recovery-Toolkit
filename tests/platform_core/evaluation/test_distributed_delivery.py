from __future__ import annotations

from windows_network_toolkit.distributed_delivery import (
    BoundedDeliveryQueue,
    DeliveryDisposition,
    DeliveryEnvelope,
    DeliveryProcessor,
    PermanentDeliveryError,
    RetryPolicy,
    TransientDeliveryError,
)


def test_duplicate_side_effect_is_suppressed():
    processor = DeliveryProcessor[str]()
    env = DeliveryEnvelope(event_id="e1", idempotency_key="decision-1", payload="apply")
    calls: list[str] = []

    first = processor.process(env, calls.append)
    second = processor.process(env, calls.append)

    assert first.disposition is DeliveryDisposition.ACK
    assert second.disposition is DeliveryDisposition.DUPLICATE
    assert calls == ["apply"]


def test_transient_failure_retries_then_dead_letters():
    processor = DeliveryProcessor[str](retry_policy=RetryPolicy(max_attempts=2))

    def fail(_: str) -> None:
        raise TransientDeliveryError("temporary")

    first = processor.process(DeliveryEnvelope("e1", "k1", "x"), fail)
    assert first.disposition is DeliveryDisposition.RETRY
    retry = processor.retry_queue.get()
    assert retry is not None and retry.attempt == 2

    second = processor.process(retry, fail)
    assert second.disposition is DeliveryDisposition.DEAD_LETTER
    assert len(processor.dead_letter_queue) == 1


def test_permanent_failure_dead_letters_immediately():
    processor = DeliveryProcessor[str]()

    def fail(_: str) -> None:
        raise PermanentDeliveryError("bad payload")

    outcome = processor.process(DeliveryEnvelope("e1", "k1", "x"), fail)
    assert outcome.disposition is DeliveryDisposition.DEAD_LETTER
    assert len(processor.dead_letter_queue) == 1


def test_bounded_queue_exposes_backpressure():
    queue = BoundedDeliveryQueue[str](capacity=1)
    assert queue.try_put(DeliveryEnvelope("e1", "k1", "x")) is DeliveryDisposition.ACK
    assert queue.try_put(DeliveryEnvelope("e2", "k2", "y")) is DeliveryDisposition.BACKPRESSURE
    assert queue.utilization == 1.0


def test_retry_queue_can_surface_backpressure():
    processor = DeliveryProcessor[str](
        retry_policy=RetryPolicy(max_attempts=3),
        retry_queue=BoundedDeliveryQueue(capacity=1),
    )
    processor.retry_queue.try_put(DeliveryEnvelope("existing", "existing", "x"))

    def fail(_: str) -> None:
        raise TransientDeliveryError("temporary")

    outcome = processor.process(DeliveryEnvelope("e1", "k1", "x"), fail)
    assert outcome.disposition is DeliveryDisposition.BACKPRESSURE
