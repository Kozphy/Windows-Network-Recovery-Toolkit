"""In-memory queue for tests and local sync classification."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from backend.queue.protocol import JobRef, JobStatus

_log = logging.getLogger(__name__)

_REGISTRY: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY: dict[str, str] = {}


class MemoryQueueBackend:
    def enqueue_classification_job(self, *, event_id: str, idempotency_key: str) -> JobRef:
        if idempotency_key in _IDEMPOTENCY:
            job_id = _IDEMPOTENCY[idempotency_key]
            return JobRef(job_id=job_id, idempotency_key=idempotency_key, status=_REGISTRY[job_id]["status"])

        job_id = f"mem-{uuid.uuid4().hex[:12]}"
        _IDEMPOTENCY[idempotency_key] = job_id
        _REGISTRY[job_id] = {
            "event_id": event_id,
            "status": JobStatus.QUEUED,
            "idempotency_key": idempotency_key,
        }
        _log.info("job_lifecycle event=queued job_id=%s event_id=%s", job_id, event_id)

        if os.getenv("TRISK_SYNC_CLASSIFY", "1") == "1":
            from backend.workers.classifier_worker import run_classification_job

            _REGISTRY[job_id]["status"] = JobStatus.STARTED
            _log.info("job_lifecycle event=started job_id=%s", job_id)
            try:
                run_classification_job(event_id)
                _REGISTRY[job_id]["status"] = JobStatus.SUCCEEDED
                _log.info("job_lifecycle event=succeeded job_id=%s", job_id)
            except Exception:
                _REGISTRY[job_id]["status"] = JobStatus.FAILED
                _log.exception("job_lifecycle event=failed job_id=%s", job_id)
                raise

        return JobRef(job_id=job_id, idempotency_key=idempotency_key, status=_REGISTRY[job_id]["status"])

    def get_job_status(self, job_id: str) -> JobStatus:
        row = _REGISTRY.get(job_id)
        if not row:
            return JobStatus.FAILED
        return row["status"]

    def cancel_job(self, job_id: str) -> bool:
        return False


def reset_memory_queue() -> None:
    _REGISTRY.clear()
    _IDEMPOTENCY.clear()
