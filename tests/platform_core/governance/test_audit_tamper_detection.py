"""Audit hash chain verification tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain


def test_tamper_detection(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "audit.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", decision_id="d1", path=path)
    ok, _ = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True
    tampered = r2.model_dump()
    tampered["payload"] = {"tampered": True}
    ok2, msg2 = verify_chain([r1.model_dump(), tampered])
    assert ok2 is False
    assert "break" in msg2.lower() or "chain" in msg2.lower()


def test_verify_file_roundtrip(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "chain.jsonl"
    append_audit("event_received", path=path)
    append_audit("policy_evaluated", path=path, payload={"outcome": "PREVIEW_ONLY"})
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok, msg = verify_chain(records)
    assert ok, msg
