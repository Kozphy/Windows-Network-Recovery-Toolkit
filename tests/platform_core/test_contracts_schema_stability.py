"""Contract schema stability tests."""

from __future__ import annotations

from src.platform_core import SCHEMA_VERSION
from src.platform_core.contracts import Decision, EvidenceBundle, NormalizedEvent


def test_normalized_event_schema_version() -> None:
    ev = NormalizedEvent(
        event_id="e1",
        timestamp_utc="2026-01-01T00:00:00Z",
        source="test",
        category="proxy",
        title="t",
    )
    assert ev.schema_version == SCHEMA_VERSION


def test_decision_roundtrip() -> None:
    d = Decision(
        decision_id="d1",
        incident_id="i1",
        timestamp_utc="2026-01-01T00:00:00Z",
        incident_type="WININET_PROXY_DRIFT",
        recommended_action="PREVIEW",
        confidence=0.8,
    )
    restored = Decision.model_validate_json(d.model_dump_json())
    assert restored.decision_id == "d1"


def test_evidence_bundle_defaults() -> None:
    b = EvidenceBundle(
        bundle_id="b1",
        incident_id="i1",
        created_at="2026-01-01T00:00:00Z",
    )
    assert b.tier == "OBSERVED_ONLY"
