"""Worker classification tests."""

from __future__ import annotations

from sqlmodel import Session, select

from backend.db import get_engine
from backend.db.models import IncidentRecord
from backend.db.repositories import content_hash, ensure_endpoint, upsert_evidence
from backend.workers.classifier_worker import run_classification_job
from windows_network_toolkit.evidence_schema import make_event_id


def test_worker_classifies_evidence():
    raw = {
        "wininet_proxy_enabled": True,
        "wininet_proxy_server": "127.0.0.1:59081",
        "winhttp_direct_access": True,
        "localhost_port": 59081,
    }
    event_id = make_event_id("2026-06-12T10:00:00Z", "proxy_state", {"endpoint_id": "ep-w1"})
    c_hash = content_hash("ep-w1", "sw1", raw)
    with Session(get_engine()) as session:
        ensure_endpoint(session, "ep-w1")
        upsert_evidence(
            session,
            event_id=event_id,
            endpoint_id="ep-w1",
            source_event_id="sw1",
            evidence_type="proxy_state",
            raw_snapshot=raw,
            normalized_fields={},
            evidence_tier="T1_STATE_EVIDENCE",
            limitations=["Does not prove malware or MITM."],
            c_hash=c_hash,
        )
        session.commit()

    result = run_classification_job(event_id)
    assert "incident_id" in result or result.get("skipped")

    with Session(get_engine()) as session:
        inc = session.exec(select(IncidentRecord).where(IncidentRecord.evidence_event_id == event_id)).first()
        if not result.get("skipped"):
            assert inc is not None
