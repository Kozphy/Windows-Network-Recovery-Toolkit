"""Worker idempotency."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.db import get_engine
from backend.db.models import IncidentRecord
from backend.db.repositories import content_hash, ensure_endpoint, upsert_evidence
from backend.workers.classifier_worker import run_classification_job
from windows_network_toolkit.evidence_schema import make_event_id


def test_duplicate_job_no_duplicate_incident():
    raw = {
        "wininet_proxy_enabled": True,
        "wininet_proxy_server": "127.0.0.1:59081",
        "winhttp_direct_access": True,
    }
    event_id = make_event_id("2026-06-12T11:00:00Z", "proxy_state", {"endpoint_id": "ep-w2"})
    c_hash = content_hash("ep-w2", "sw2", raw)
    with Session(get_engine()) as session:
        ensure_endpoint(session, "ep-w2")
        upsert_evidence(
            session,
            event_id=event_id,
            endpoint_id="ep-w2",
            source_event_id="sw2",
            evidence_type="proxy_state",
            raw_snapshot=raw,
            normalized_fields={},
            evidence_tier="T1_STATE_EVIDENCE",
            limitations=[],
            c_hash=c_hash,
        )
        session.commit()

    run_classification_job(event_id)
    run_classification_job(event_id)

    with Session(get_engine()) as session:
        rows = list(
            session.exec(select(IncidentRecord).where(IncidentRecord.evidence_event_id == event_id))
        )
        assert len(rows) <= 1
