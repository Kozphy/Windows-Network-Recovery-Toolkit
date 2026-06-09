"""Audit JSONL schema tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.audit.schema import export_schema_json, validate_audit_record
from src.platform_core.audit.writer import append_audit, reset_chain_for_tests


def test_audit_record_valid(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "audit.jsonl"
    rec = append_audit("event_received", incident_id="inc-1", path=path)
    blob = rec.model_dump()
    assert validate_audit_record(blob)
    assert blob["previous_hash"] == "genesis"
    assert blob["current_hash"]


def test_audit_schema_export() -> None:
    schema = export_schema_json()
    assert "ERPAuditRecord" in schema
