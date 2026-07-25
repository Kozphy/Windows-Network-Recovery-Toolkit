"""Deterministic tests for the domain event kernel."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.audit.writer import append_audit, reset_chain_for_tests
from src.platform_core.domain_events.compat import (
    is_legacy_audit_record,
    legacy_record_as_envelope_view,
)
from src.platform_core.domain_events.envelope import (
    DOMAIN_EVENT_SCHEMA,
    LEGACY_AUDIT_SCHEMA,
    build_envelope,
    validate_envelope,
)
from src.platform_core.domain_events.verify import inspect_stream, verify_domain_stream
from src.platform_core.domain_events.writer import append_domain_event, reset_domain_chain_for_tests
from src.platform_core.governance.chain_of_custody import audit_hash_body, chain_hash, verify_chain

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "domain_events"


def test_valid_domain_stream_verifies(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "stream.jsonl"
    append_domain_event("guardian.check", source="proxy_guardian", payload={"classification": "NO_PROXY"}, path=path)
    append_domain_event(
        "decision.diagnosis",
        source="src.cli.diagnose",
        payload={"diagnosis_id": "d1"},
        action_type="decision_created",
        path=path,
    )
    result = verify_domain_stream(path, require_tip=True)
    assert result["verified"] is True
    assert result["domain_event_records"] == 2
    assert result["chain_verified"] is True


def test_golden_valid_stream_fixture() -> None:
    path = FIXTURES / "valid_stream.jsonl"
    assert path.is_file()
    result = verify_domain_stream(path)
    # Tip may be absent in committed fixture — chain + envelope must pass.
    assert result["chain_verified"] is True
    assert not result["envelope_errors"]
    assert not result["malformed_records"]
    assert result["domain_event_records"] >= 2


def test_tampered_payload_breaks_chain(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "tamper.jsonl"
    append_domain_event("guardian.check", source="proxy_guardian", payload={"x": 1}, path=path)
    append_domain_event("guardian.apply", source="proxy_guardian", payload={"x": 2}, path=path)
    lines = path.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["payload"] = {"x": 999, "tampered": True}
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = verify_domain_stream(path)
    assert result["chain_verified"] is False
    assert result["verified"] is False


def test_malformed_json_line_fails(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "bad.jsonl"
    append_domain_event("guardian.check", source="proxy_guardian", path=path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not-json\n")
    result = verify_domain_stream(path)
    assert result["malformed_records"]
    assert result["verified"] is False


def test_unsupported_schema_version_fails(tmp_path: Path) -> None:
    path = tmp_path / "future.jsonl"
    # Manually craft a hash-consistent single record with bad schema — chain may pass;
    # schema gate must fail.
    body = build_envelope(
        event_type="x",
        source="test",
        payload={},
        previous_hash="genesis",
        current_hash="",
    )
    body["schema_version"] = "wnrt.domain_event.v999"
    body["current_hash"] = chain_hash("genesis", audit_hash_body(body))
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    result = verify_domain_stream(path)
    assert result["unsupported_schema"]
    assert result["verified"] is False


def test_ordering_chain_integrity_failure(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "order.jsonl"
    a = append_domain_event("a", source="t", path=path)
    b = append_domain_event("b", source="t", path=path)
    # Swap lines — hashes no longer form a valid chain from genesis.
    path.write_text(json.dumps(b) + "\n" + json.dumps(a) + "\n", encoding="utf-8")
    result = verify_domain_stream(path)
    assert result["chain_verified"] is False


def test_legacy_erp_audit_compatibility(tmp_path: Path) -> None:
    """Pre-kernel erp.audit.v1 rows still chain-verify and project to envelope view."""
    reset_chain_for_tests()
    # Write a legacy-shaped row directly (bypass domain writer).
    from src.platform_core.governance.chain_of_custody import audit_hash_body, chain_hash

    path = tmp_path / "legacy.jsonl"
    rec1 = {
        "audit_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "schema_version": LEGACY_AUDIT_SCHEMA,
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "action_type": "event_received",
        "trace_id": "",
        "decision_id": "",
        "incident_id": "i1",
        "actor": "platform",
        "payload": {"subsystem": "proxy_guardian", "event": "guardian_check"},
        "previous_hash": "genesis",
        "current_hash": "",
        "signature_status": "hash_chained",
    }
    rec1["current_hash"] = chain_hash("genesis", audit_hash_body(rec1))
    rec2 = {
        "audit_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "schema_version": LEGACY_AUDIT_SCHEMA,
        "timestamp_utc": "2026-01-01T00:00:01Z",
        "action_type": "action_executed",
        "trace_id": "",
        "decision_id": "",
        "incident_id": "i1",
        "actor": "platform",
        "payload": {"subsystem": "proxy_guardian", "event": "guardian_apply"},
        "previous_hash": rec1["current_hash"],
        "current_hash": "",
        "signature_status": "hash_chained",
    }
    rec2["current_hash"] = chain_hash(rec1["current_hash"], audit_hash_body(rec2))
    path.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")

    assert is_legacy_audit_record(rec1)
    view = legacy_record_as_envelope_view(rec1)
    assert view["schema_version"] == DOMAIN_EVENT_SCHEMA
    assert view["event_type"] == "guardian_check"

    result = verify_domain_stream(path)
    assert result["legacy_audit_records"] == 2
    assert result["chain_verified"] is True
    assert result["verified"] is True  # no tip present → tip not required


def test_append_audit_returns_chainable_model_dump(tmp_path: Path) -> None:
    reset_chain_for_tests()
    path = tmp_path / "audit.jsonl"
    r1 = append_audit("event_received", incident_id="i1", path=path)
    r2 = append_audit("decision_created", incident_id="i1", decision_id="d1", path=path)
    ok, msg = verify_chain([r1.model_dump(), r2.model_dump()])
    assert ok is True, msg
    # On-disk records use domain event schema
    disk = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert disk[0]["schema_version"] == DOMAIN_EVENT_SCHEMA
    assert verify_domain_stream(path)["chain_verified"] is True


def test_validate_envelope_rejects_incomplete() -> None:
    ok, msg = validate_envelope({"schema_version": DOMAIN_EVENT_SCHEMA})
    assert ok is False
    assert "missing_fields" in msg


def test_inspect_stream(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "s.jsonl"
    append_domain_event("guardian.check", source="proxy_guardian", path=path)
    summary = inspect_stream(path)
    assert summary["record_count"] == 1
    assert summary["sample"][0]["event_type"] == "guardian.check"


def test_tip_mismatch_detected(tmp_path: Path) -> None:
    reset_domain_chain_for_tests()
    path = tmp_path / "tip.jsonl"
    append_domain_event("guardian.check", source="proxy_guardian", path=path)
    # Forge sibling tip to wrong hash while leaving JSONL alone
    from src.platform_core.audit.paths import tip_path_for
    from src.platform_core.audit.tip_anchor import write_tip_anchor

    tip_path = tip_path_for(path)
    write_tip_anchor(tip_hash="deadbeef", record_count=1, audit_path=path, tip_path=tip_path)
    result = verify_domain_stream(path, tip_path=tip_path, require_tip=True)
    assert result["tip_match"] is False
    assert result["verified"] is False
