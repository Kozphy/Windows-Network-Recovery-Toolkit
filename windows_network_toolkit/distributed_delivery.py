"""Deterministic delivery contracts for distributed-systems interview scenarios.

This module is intentionally dependency-light. It models the semantics that matter
before selecting Kafka, Redis, NATS, or a cloud queue: idempotency, bounded queues,
retry classification, dead-letter routing, and duplicate side-effect suppression.
It is a portfolio contract, not a production broker implementation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class DeliveryDisposition(str, Enum):
    ACK = "ACK"
    RETRY = "RETRY"
    DEAD_LETTER = "DEAD_LETTER"
    DUPLICATE = "DUPLICATE"
    BACKPRESSURE = "BACKPRESSURE"


@dataclass(frozen=True)
class DeliveryEnvelope(Generic[T]):
    event_id: str
    idempotency_key: str
    payload: T
    attempt: int = 1

    def next_attempt(self) -> "DeliveryEnvelope[T]":
        return DeliveryEnvelope(
            event_id=self.event_id,
            idempotency_key=self.idempotency_key,
            payload=self.payload,
            attempt=self.attempt + 1,
        )


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


@dataclass
class IdempotencyLedger:
    """Tracks completed side effects by stable idempotency key.

    This deliberately models *effect completion*, not message receipt. A retried
    delivery may be processed again until the side effect is durably recorded.
    """

    completed_keys: set[str] = field(default_factory=set)

    def is_completed(self, key: str) -> bool:
        return key in self.completed_keys

    def mark_completed(self, key: str) -> None:
        self.completed_keys.add(key)


@dataclass
class BoundedDeliveryQueue(Generic[T]):
    capacity: int
    _items: deque[DeliveryEnvelope[T]] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")

    @property
    def depth(self) -> int:
        return len(self._items)

    @property
    def utilization(self) -> float:
        return self.depth / self.capacity

    def try_put(self, item: DeliveryEnvelope[T]) -> DeliveryDisposition:
        if self.depth >= self.capacity:
            return DeliveryDisposition.BACKPRESSURE
        self._items.append(item)
        return DeliveryDisposition.ACK

    def get(self) -> DeliveryEnvelope[T] | None:
        if not self._items:
            return None
        return self._items.popleft()


@dataclass
class DeliveryOutcome(Generic[T]):
    disposition: DeliveryDisposition
    envelope: DeliveryEnvelope[T]
    error: str | None = None


class TransientDeliveryError(RuntimeError):
    """Retryable processing failure."""


class PermanentDeliveryError(RuntimeError):
    """Non-retryable processing failure."""


@dataclass
class DeliveryProcessor(Generic[T]):
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    ledger: IdempotencyLedger = field(default_factory=IdempotencyLedger)
    retry_queue: BoundedDeliveryQueue[T] = field(
        default_factory=lambda: BoundedDeliveryQueue(capacity=100)
    )
    dead_letter_queue: list[DeliveryEnvelope[T]] = field(default_factory=list)

    def process(
        self,
        envelope: DeliveryEnvelope[T],
        side_effect: Callable[[T], None],
    ) -> DeliveryOutcome[T]:
        if self.ledger.is_completed(envelope.idempotency_key):
            return DeliveryOutcome(DeliveryDisposition.DUPLICATE, envelope)

        try:
            side_effect(envelope.payload)
        except PermanentDeliveryError as exc:
            self.dead_letter_queue.append(envelope)
            return DeliveryOutcome(
                DeliveryDisposition.DEAD_LETTER,
                envelope,
                error=str(exc),
            )
        except TransientDeliveryError as exc:
            if envelope.attempt >= self.retry_policy.max_attempts:
                self.dead_letter_queue.append(envelope)
                return DeliveryOutcome(
                    DeliveryDisposition.DEAD_LETTER,
                    envelope,
                    error=str(exc),
                )
            retry_envelope = envelope.next_attempt()
            queued = self.retry_queue.try_put(retry_envelope)
            if queued is DeliveryDisposition.BACKPRESSURE:
                return DeliveryOutcome(
                    DeliveryDisposition.BACKPRESSURE,
                    envelope,
                    error=str(exc),
                )
            return DeliveryOutcome(
                DeliveryDisposition.RETRY,
                retry_envelope,
                error=str(exc),
            )

        self.ledger.mark_completed(envelope.idempotency_key)
        return DeliveryOutcome(DeliveryDisposition.ACK, envelope)
