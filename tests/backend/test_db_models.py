"""Database model tests."""

from __future__ import annotations

from sqlmodel import Session

from backend.db import get_engine, init_trisk_schema
from backend.db.repositories import content_hash, ensure_endpoint, upsert_evidence


def test_upsert_evidence_idempotent():
    init_trisk_schema()
    with Session(get_engine()) as session:
        ensure_endpoint(session, "ep-1")
        c_hash = content_hash("ep-1", "s1", {"a": 1})
        row1, created1 = upsert_evidence(
            session,
            event_id="evt-1",
            endpoint_id="ep-1",
            source_event_id="s1",
            evidence_type="proxy_state",
            raw_snapshot={"a": 1},
            normalized_fields={},
            evidence_tier="T1_STATE_EVIDENCE",
            limitations=[],
            c_hash=c_hash,
        )
        row2, created2 = upsert_evidence(
            session,
            event_id="evt-2",
            endpoint_id="ep-1",
            source_event_id="s1",
            evidence_type="proxy_state",
            raw_snapshot={"a": 1},
            normalized_fields={},
            evidence_tier="T1_STATE_EVIDENCE",
            limitations=[],
            c_hash=c_hash,
        )
        session.commit()
        assert created1 is True
        assert created2 is False
        assert row1.event_id == row2.event_id
