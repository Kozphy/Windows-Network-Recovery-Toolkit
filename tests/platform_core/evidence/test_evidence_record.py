"""Typed evidence record — serialization, validation, replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.evidence.record import (
    TypedEvidenceRecord,
    records_from_fixture,
    records_to_bundle,
)
from src.platform_core.serialization import content_hash

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "erp"


def test_rejects_probability_confidence() -> None:
    with pytest.raises(ValueError, match="ordinal"):
        TypedEvidenceRecord.from_observation(
            source="test",
            collector="unit",
            evidence_type="signal",
            observed_value="1",
            confidence_level=0.95,  # type: ignore[arg-type]
        )


def test_integrity_hash_stable() -> None:
    rec = TypedEvidenceRecord.from_observation(
        source="wininet",
        collector="unit",
        evidence_type="proxy_enable",
        observed_value="1",
        confidence_level="high",
    )
    rec2 = rec.model_copy(update={"timestamp": rec.timestamp})
    assert rec.with_integrity().chain_of_custody.integrity_hash == rec2.with_integrity().chain_of_custody.integrity_hash


def test_to_evidence_item_preserves_tier() -> None:
    rec = TypedEvidenceRecord.from_observation(
        source="netstat",
        collector="unit",
        evidence_type="listener",
        observed_value="node.exe:4321",
        evidence_tier="CORRELATED",
        confidence_level="medium",
    )
    item = rec.with_integrity().to_evidence_item()
    assert item.tier == "CORRELATED"
    assert item.raw_data["confidence_level"] == "medium"


def test_bundle_deterministic_replay() -> None:
    records = [
        TypedEvidenceRecord.from_observation(
            source="a",
            collector="unit",
            evidence_type="x",
            observed_value="1",
        ),
        TypedEvidenceRecord.from_observation(
            source="b",
            collector="unit",
            evidence_type="y",
            observed_value="2",
        ),
    ]
    b1 = records_to_bundle(records, incident_id="inc-1")
    b2 = records_to_bundle(records, incident_id="inc-1")
    assert b1["bundle_hash"] == b2["bundle_hash"]
    assert len(records_from_fixture(b1)) == 2


def test_schema_roundtrip() -> None:
    rec = TypedEvidenceRecord.from_observation(
        source="test",
        collector="unit",
        evidence_type="proxy_server",
        observed_value="127.0.0.1:8080",
        limitations=["correlation only"],
    ).with_integrity()
    raw = json.loads(rec.model_dump_json())
    restored = TypedEvidenceRecord.model_validate(raw)
    assert restored.observed_value == "127.0.0.1:8080"
    assert restored.chain_of_custody.integrity_hash
