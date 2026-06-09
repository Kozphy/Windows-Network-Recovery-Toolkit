"""Hash-chained audit tests."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.governance.chain_of_custody import verify_chain


def test_hash_chain(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "chain.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", decision_id="d1", path=path)
    ok, msg = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True, msg
    assert r2.previous_hash == r1.current_hash
