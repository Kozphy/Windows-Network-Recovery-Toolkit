"""Audit hash chain verification tests for fleet export and governance."""

from __future__ import annotations

from pathlib import Path

from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.fleet.simulator import (
    build_audit_chain_records,
    load_fleet_fixture,
    verify_fleet_audit_chain,
)
from src.platform_core.governance.chain_of_custody import verify_chain

REPO = Path(__file__).resolve().parents[1]
FLEET = REPO / "tests" / "fixtures" / "fleet" / "fleet_100_endpoints.jsonl"


def test_audit_chain_passes_on_valid_file(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "chain.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", decision_id="d1", path=path)
    ok, msg = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok, msg


def test_audit_chain_fails_on_tampered_file(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "chain.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", decision_id="d1", path=path)
    tampered = r2.model_dump()
    tampered["decision_id"] = "tampered"
    ok, msg = verify_chain([r1.model_dump(), tampered])
    assert not ok
    assert "chain break" in msg


def test_fleet_audit_chain_from_fixture() -> None:
    rows = load_fleet_fixture(FLEET)
    chain = build_audit_chain_records(rows)
    ok, msg = verify_fleet_audit_chain(chain)
    assert ok, msg
    assert chain[0]["previous_hash"] == "genesis"
    for rec in chain:
        assert rec.get("event_id")
        assert rec.get("evidence_tier")
        assert rec.get("current_hash")
