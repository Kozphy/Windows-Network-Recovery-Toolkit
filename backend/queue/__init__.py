"""Queue backend factory."""

from __future__ import annotations

import os

from backend.queue.memory_backend import MemoryQueueBackend
from backend.queue.protocol import QueueBackend


def get_queue_backend() -> QueueBackend:
    backend = os.getenv("QUEUE_BACKEND", "memory").lower()
    if backend == "rq":
        from backend.queue.rq_backend import RQQueueBackend

        return RQQueueBackend()
    return MemoryQueueBackend()
