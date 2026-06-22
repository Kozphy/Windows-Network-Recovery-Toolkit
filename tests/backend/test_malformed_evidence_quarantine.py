"""Malformed evidence quarantine."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.db import get_engine
from backend.db.models import ClassificationStatus, EvidenceEvent
from backend.db.repositories import content_hash, ensure_endpoint, upsert_evidence
from backend.workers.classifier_worker import run_classification_job
from windows_network_toolkit.evidence_schema import make_event_id


def test_empty_pipeline_quarantines():
    event_id = make_event_id("2026-06-12T12:00:00Z", "proxy_state", {"endpoint_id": "ep-q"})
    raw = {"unrecognized": True}
    c_hash = content_hash("ep-q", "sq", raw)
    with Session(get_engine()) as session:
        ensure_endpoint(session, "ep-q")
        upsert_evidence(
            session,
            event_id=event_id,
            endpoint_id="ep-q",
            source_event_id="sq",
            evidence_type="proxy_state",
            raw_snapshot=raw,
            normalized_fields={},
            evidence_tier="T1_STATE_EVIDENCE",
            limitations=[],
            c_hash=c_hash,
        )
        session.commit()

    run_classification_job(event_id)

    with Session(get_engine()) as session:
        row = session.exec(select(EvidenceEvent).where(EvidenceEvent.event_id == event_id)).first()
        assert row is not None
        assert row.classification_status in (
            ClassificationStatus.QUARANTINED.value,
            ClassificationStatus.CLASSIFIED.value,
        )
