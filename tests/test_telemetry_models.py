"""Tests for telemetry models."""

from __future__ import annotations

from datetime import datetime, timezone

from telemetry.models import RegistryWriteEvent, RegistryWriterEvidence


def test_registry_write_event_round_trip() -> None:
    event = RegistryWriteEvent(
        timestamp_utc=datetime(2026, 1, 15, 12, 0, 5, tzinfo=timezone.utc),
        source="sysmon",
        event_id=13,
        registry_path=r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyEnable",
        registry_value_name="ProxyEnable",
        registry_value_data="DWORD (0x00000001)",
        process_id=21712,
        process_name="node.exe",
        process_path=r"C:\Program Files\nodejs\node.exe",
        parse_warnings=["demo"],
    )
    payload = event.to_dict()
    restored = RegistryWriteEvent.from_dict(payload)
    assert restored.process_id == 21712
    assert restored.registry_value_name == "ProxyEnable"
    assert "raw_event" not in payload


def test_registry_writer_evidence_to_dict() -> None:
    evidence = RegistryWriterEvidence(
        evidence_level="NO_WRITER_EVIDENCE",
        limitations=["No telemetry supplied."],
        confidence_rank="none",
    )
    payload = evidence.to_dict()
    assert payload["evidence_level"] == "NO_WRITER_EVIDENCE"
    assert payload["confidence_rank"] == "none"
