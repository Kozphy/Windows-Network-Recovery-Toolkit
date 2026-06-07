"""Append-only audit JSONL contract tests."""

from __future__ import annotations

import json

from platform_core.audit import write_audit
from platform_core.models import PlatformAuditRecord


def test_platform_audit_record_required_fields() -> None:
    rec = PlatformAuditRecord(
        audit_id="audit-test-1",
        actor="pytest",
        action="remediation_preview",
        target_type="failure_event",
        target_id="ev-1",
        decision="allowed",
        rationale="fixture",
        timestamp="2026-06-04T12:00:00+00:00",
    )
    blob = rec.model_dump()
    for key in ("audit_id", "actor", "action", "timestamp"):
        assert key in blob


def test_write_audit_appends_single_jsonl_line(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    rec = write_audit(
        actor="pytest",
        action="remediation_preview",
        target_type="event",
        target_id="e-1",
        decision="allowed",
        rationale="contract test",
    )
    audit_path = tmp_path / "audit.jsonl"
    assert audit_path.is_file()
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["audit_id"] == rec.audit_id
    assert row["action"] == "remediation_preview"
    assert row["decision"] == "allowed"


def test_audit_append_is_additive(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    write_audit(actor="a", action="first", decision="ok")
    write_audit(actor="b", action="second", decision="ok")
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["action"] == "first"
    assert json.loads(lines[1])["action"] == "second"
