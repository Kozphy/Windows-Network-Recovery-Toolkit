"""Memory queue backend tests."""

from __future__ import annotations

from backend.queue.memory_backend import MemoryQueueBackend, reset_memory_queue
from backend.queue.protocol import JobStatus


def test_enqueue_idempotent(monkeypatch):
    monkeypatch.setenv("TRISK_SYNC_CLASSIFY", "0")
    reset_memory_queue()
    backend = MemoryQueueBackend()
    j1 = backend.enqueue_classification_job(event_id="evt-a", idempotency_key="key-1")
    j2 = backend.enqueue_classification_job(event_id="evt-a", idempotency_key="key-1")
    assert j1.job_id == j2.job_id


def test_job_status_unknown():
    reset_memory_queue()
    backend = MemoryQueueBackend()
    assert backend.get_job_status("missing") == JobStatus.FAILED
