"""Tests for the Failure Knowledge System (deterministic rules, storage, API)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from failure_system.api import create_app
from failure_system.collector import DiagnosticSnapshot
from failure_system.generator import build_failure_block
from failure_system.models import DiagnosticCommandResult, FailureBlock, RiskLevel, RuleOutcome
from failure_system.rules import RuleEngine
from failure_system.search import search_failure_blocks
from failure_system.storage import append_failure_block, iter_failure_blocks, load_failure_block_by_id


def test_rule_dns_issue() -> None:
    snap = DiagnosticSnapshot(
        ping_ip_ok=True,
        nslookup_ok=False,
        curl_https_ok=False,
        winhttp_direct=True,
        proxy_server_line_present=False,
        intermittent_reported=False,
        raw={},
    )
    out = RuleEngine().evaluate(snap)
    assert out and out[0].rule_id == "dns_failure_likely"


def test_rule_https_when_dns_ok() -> None:
    snap = DiagnosticSnapshot(
        ping_ip_ok=True,
        nslookup_ok=True,
        curl_https_ok=False,
        winhttp_direct=True,
        proxy_server_line_present=False,
        intermittent_reported=False,
        raw={},
    )
    out = RuleEngine().evaluate(snap)
    assert any(r.rule_id == "https_path_failure" for r in out)


def test_generator_shapes() -> None:
    snap = DiagnosticSnapshot(
        ping_ip_ok=True,
        nslookup_ok=False,
        curl_https_ok=False,
        raw={
            "ping": DiagnosticCommandResult(command=["ping"], exit_code=0, stdout="ok", ok=True),
        },
    )
    outcomes = RuleEngine().evaluate(snap)
    block = build_failure_block(snap, outcomes)
    assert block.confidence_score >= 0.0
    assert block.risk_level in RiskLevel
    assert block.symptom


def test_storage_roundtrip(tmp_path: Path) -> None:
    data_dir = tmp_path / "failure_blocks"
    block = FailureBlock(
        id=uuid4(),
        name="Test",
        symptom="Ping OK DNS fail",
        observed_signals=["nslookup=fail"],
        likely_causes=["DNS resolution failure"],
        diagnostic_commands={"nslookup_google_com": "fail"},
        confidence_score=0.9,
        recommended_fix="Flush DNS",
        risk_level=RiskLevel.LOW,
        safety_boundary="No auto repair",
        rollback_plan="Restore DNS list",
        created_at=datetime.now(timezone.utc),
        source_logs=["rules:dns_failure_likely"],
    )
    append_failure_block(block, data_dir=data_dir)
    loaded = load_failure_block_by_id(block.id, data_dir=data_dir)
    assert loaded is not None
    assert loaded.symptom == block.symptom


def test_search_matches(tmp_path: Path) -> None:
    data_dir = tmp_path / "failure_blocks"
    b = FailureBlock(
        id=uuid4(),
        name="DNS",
        symptom="browser fails but ping works",
        observed_signals=[],
        likely_causes=["DNS resolution failure"],
        diagnostic_commands={},
        confidence_score=0.8,
        recommended_fix="reset_dns.bat",
        risk_level=RiskLevel.LOW,
        safety_boundary="x",
        rollback_plan="y",
        created_at=datetime.now(timezone.utc),
        source_logs=[],
    )
    append_failure_block(b, data_dir=data_dir)
    hits = search_failure_blocks("dns browser", data_dir=data_dir)
    assert len(hits) == 1


def test_api_health_and_diagnose(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    snap = DiagnosticSnapshot(
        ping_ip_ok=True,
        nslookup_ok=True,
        curl_https_ok=True,
        winhttp_direct=True,
        proxy_server_line_present=False,
        intermittent_reported=False,
        raw={
            "ping_8_8_8_8": DiagnosticCommandResult(
                command=["ping"], exit_code=0, stdout="Reply from 8.8.8.8", ok=True
            ),
        },
    )

    import failure_system.api as api_mod

    monkeypatch.setenv("FAILURE_SYSTEM_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(api_mod, "collect_diagnostics", lambda **_: snap)

    app = create_app()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r2 = client.post("/diagnose", json={"intermittent": False})
    assert r2.status_code == 200
    body = r2.json()
    assert "failure_block" in body
    assert "explanation_text" in body
    assert isinstance(body["explanation_text"], str)
    assert len(body["explanation_text"]) > 20
    assert body["stored_path"]

    shard = Path(body["stored_path"])
    assert shard.exists()
    line = shard.read_text(encoding="utf-8").strip().splitlines()[-1]
    obj = json.loads(line)
    assert obj["symptom"]
