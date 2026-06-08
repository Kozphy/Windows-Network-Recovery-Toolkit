"""Proxy guard report integration for registry writer telemetry section."""

from __future__ import annotations

from proxy_guard.reporter import build_report_payload


def test_build_report_payload_includes_no_telemetry_by_default() -> None:
    payload = build_report_payload(
        raw_signals={},
        attribution={},
        persistence={},
        certificates={},
        risk={"classification": "unknown", "limitations": [], "recommended_actions": []},
    )
    section = payload["registry_writer_evidence"]
    assert section["evidence_level"] == "NO_WRITER_EVIDENCE"
    assert any(
        "registry writer telemetry" in item.lower() or "sysmon" in item.lower()
        for item in section["limitations"]
    )

    with_listener = build_report_payload(
        raw_signals={},
        attribution={"pid": 21712, "process_name": "node.exe"},
        persistence={},
        certificates={},
        risk={"classification": "unknown", "limitations": [], "recommended_actions": []},
    )
    listener_section = with_listener["registry_writer_evidence"]
    assert listener_section["evidence_level"] == "LISTENER_OBSERVED"
    assert any("correlation" in item.lower() or "listener" in item.lower() for item in listener_section["limitations"])
