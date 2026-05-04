from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.network_state.event_log import (
    SCHEMA_VERSION,
    correlation_key,
    count_drift_events,
    drift_severity,
    incident_id_from_proxy,
    log_drift,
    log_snapshot,
    log_verification,
    parse_proxy,
    path_drifts,
    path_snapshots,
    path_verifications,
)


def test_parse_proxy_localhost_port() -> None:
    parsed = parse_proxy(
        {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:55509"},
    )
    assert parsed["is_localhost_proxy"] is True
    assert parsed["localhost_port"] == 55509
    assert parsed["localhost_host"] == "127.0.0.1"


def test_correlation_key_stable() -> None:
    assert correlation_key("127.0.0.1:55509") == correlation_key("127.0.0.1:55509 ")
    assert correlation_key(None) == correlation_key("")


def test_incident_id_stable() -> None:
    assert incident_id_from_proxy("127.0.0.1:55509") == incident_id_from_proxy("127.0.0.1:55509")
    assert incident_id_from_proxy("127.0.0.1:55509") != incident_id_from_proxy("127.0.0.1:55510")


def test_log_snapshot_schema_version(tmp_path: Path) -> None:
    oid = log_snapshot(
        tmp_path,
        observed={
            "ProxyEnable": 1,
            "ProxyServer": "127.0.0.1:443",
            "AutoConfigURL": None,
            "AutoDetect": None,
            "ProxyOverride": None,
        },
    )
    line = path_snapshots(tmp_path).read_text(encoding="utf-8").strip().splitlines()[0]
    row = json.loads(line)
    assert row["schema_version"] == "2.0"
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["event_type"] == "snapshot"
    assert row["event_id"] == oid


def test_log_verification_ok_true_when_match(tmp_path: Path) -> None:
    log_verification(
        tmp_path,
        repair_event_id="rep-test",
        incident_id="inc-test",
        correlation_key_val="ck",
        expected={"ProxyEnable": 0},
        observed={"ProxyEnable": 0, "ProxyServer": "127.0.0.1:9"},
        ok=True,
    )
    raw = path_verifications(tmp_path).read_text(encoding="utf-8").strip().splitlines()[0]
    row = json.loads(raw)
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["ok"] is True
    assert row["confidence"] == 0.99


@pytest.mark.parametrize("rc,severity", [(1, "medium"), (2, "medium"), (3, "high"), (99, "high")])
def test_drift_severity_rule(rc: int, severity: str) -> None:
    assert drift_severity(rc) == severity


def test_log_drift_repeat_count_high_integration(tmp_path: Path) -> None:
    corr = correlation_key("127.0.0.1:11111")
    inc = incident_id_from_proxy("127.0.0.1:11111")
    for rc in range(1, 3):
        log_drift(
            tmp_path,
            drift_type="proxy_reenabled",
            incident_id=inc,
            correlation_key_val=corr,
            previous_known_good={"ProxyEnable": 0},
            current={"ProxyEnable": 1, "ProxyServer": "127.0.0.1:11111"},
            repeat_count=rc,
        )
    assert count_drift_events(tmp_path, corr) == 2
    rid = log_drift(
        tmp_path,
        drift_type="proxy_reenabled",
        incident_id=inc,
        correlation_key_val=corr,
        previous_known_good={"ProxyEnable": 0},
        current={"ProxyEnable": 1, "ProxyServer": "127.0.0.1:11111"},
        repeat_count=3,
        confidence=0.95,
    )
    assert drift_severity(3) == "high"
    drift_lines = path_drifts(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    tail = json.loads(drift_lines[-1])
    assert tail["event_id"] == rid
    assert tail["severity"] == "high"


def test_migration_preserves_original(tmp_path: Path) -> None:
    lg = tmp_path / "logs"
    lg.mkdir()
    audit = lg / "repair_audit.jsonl"
    row = json.dumps(
        {
            "type": "repair",
            "subtype": "proxy_disable",
            "timestamp": "2026-01-02T03:04:05+00:00",
            "snapshot_id": "x",
            "before": {"values": {"ProxyEnable": 1, "ProxyServer": "127.0.0.1:7"}},
            "planned_action": {},
            "after": {"proxy_enable": 0, "proxy_server": "127.0.0.1:7"},
            "verification_result": {"ok": True, "expected_proxy_enable": 0},
            "results": [],
        },
        ensure_ascii=False,
    )
    audit.write_text(row + "\n", encoding="utf-8")
    before = audit.read_bytes()
    h_prev = hashlib.sha256(before).hexdigest()
    mig = Path(__file__).resolve().parents[1] / "tools" / "migrate_v1_audit_to_v2.py"
    subprocess.check_call([sys.executable, str(mig), "--repo", str(tmp_path)], cwd=str(tmp_path))
    assert audit.read_bytes() == before
    assert hashlib.sha256(audit.read_bytes()).hexdigest() == h_prev
    out_snap = lg / "v2_migrated" / "snapshots.jsonl"
    assert out_snap.is_file()
