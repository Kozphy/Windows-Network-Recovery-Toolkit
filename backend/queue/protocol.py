"""Queue backend protocol — migration-ready abstraction over RQ."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class JobStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"


@dataclass(frozen=True)
class JobRef:
    job_id: str
    idempotency_key: str
    status: JobStatus


class QueueBackend(Protocol):
    def enqueue_classification_job(self, *, event_id: str, idempotency_key: str) -> JobRef:
        """Enqueue classification; duplicate idempotency_key returns existing job."""

    def get_job_status(self, job_id: str) -> JobStatus:
        """Return current job status."""

    def cancel_job(self, job_id: str) -> bool:
        """Cancel if supported; return False when not supported."""
