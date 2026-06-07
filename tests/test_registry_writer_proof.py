"""Registry writer proof facade: unavailable, found, and permission/error handling."""

from __future__ import annotations

from typing import Any

import pytest

from evidence.registry_writer import RegistryWriterEvidence
from evidence.registry_writer_proof import build_registry_writer_proof


def test_sysmon_unavailable_returns_clear_limitation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "evidence.registry_writer_proof.collect_registry_writer_evidence",
        lambda **_kwargs: {
            "evidence": [],
            "limitations": ["writer proof unavailable; enable Sysmon registry telemetry or import Procmon trace."],
            "sysmon_status": {"installed": False, "running": False, "log_available": False, "limitations": []},
        },
    )
    payload = build_registry_writer_proof()
    proof = payload["registry_writer_proof"]
    assert proof["status"] == "unavailable"
    assert proof["evidence_level"] == "observation"
    assert proof["events"] == []
    assert "Sysmon" in proof["reason"] or "writer proof unavailable" in proof["reason"].lower()
    assert "listener/process correlation does not prove" in proof["limitation"]


def test_mock_sysmon_event_is_parsed_into_proof_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_evidence = RegistryWriterEvidence(
        timestamp="2026-05-09T11:30:01Z",
        process_image=r"C:\Program Files\nodejs\node.exe",
        process_id=4242,
        user="DESKTOP-USER",
        target_object=r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\ProxyServer",
        value_name="ProxyServer",
        previous_value=None,
        current_value="127.0.0.1:54321",
        event_source="sysmon_event_13",
        source_event_id="13",
        confidence=0.94,
        limitations=[],
    )
    monkeypatch.setattr(
        "evidence.registry_writer_proof.collect_registry_writer_evidence",
        lambda **_kwargs: {
            "evidence": [fake_evidence],
            "limitations": [],
            "sysmon_status": {"installed": True, "running": True, "log_available": True, "limitations": []},
        },
    )
    payload = build_registry_writer_proof()
    proof = payload["registry_writer_proof"]
    assert proof["status"] == "found"
    assert proof["evidence_level"] == "proof_candidate"
    assert len(proof["events"]) == 1
    event = proof["events"][0]
    assert event["value_name"] == "ProxyServer"
    assert event["image"].endswith("node.exe")
    assert event["event_source"] == "sysmon_event_13"


def test_permission_error_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_kwargs: Any) -> Any:
        raise PermissionError("Access is denied")

    monkeypatch.setattr("evidence.registry_writer_proof.collect_registry_writer_evidence", boom)
    payload = build_registry_writer_proof()
    proof = payload["registry_writer_proof"]
    assert proof["status"] == "unavailable"
    assert "permission_denied" in proof["reason"].lower()


def test_os_error_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_kwargs: Any) -> Any:
        raise OSError("query exploded")

    monkeypatch.setattr("evidence.registry_writer_proof.collect_registry_writer_evidence", boom)
    payload = build_registry_writer_proof()
    assert payload["registry_writer_proof"]["status"] == "unavailable"
