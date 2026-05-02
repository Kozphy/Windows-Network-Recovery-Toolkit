"""FastAPI integration tests for ``/platform/*`` RBAC, metrics merge, and attribution responses (offline).

Module responsibility:
    Validate header-derived roles against ingest and read routes, verify
    :func:`~platform_core.metrics.compute_platform_metrics` merges ``platform_signals.jsonl`` KPIs into
    dashboard payloads, and exercise attribution handlers with tempfile-isolated JSONL roots.

System placement:
    Uses :class:`fastapi.testclient.TestClient` against ``backend.main:app``; monkeypatches
    ``platform_core.storage.platform_data_dir`` to ephemeral directories—no writes under the developer's
    real ``platform_data/`` folder.

Key invariants:
    * Admin vs viewer headers must produce expected HTTP statuses per ``platform_core.rbac`` matrices.
    * Metrics tests depend on deterministic JSON line ordering inside temp files—not on production data.

Raises:
    ``pytest`` assertions; fixture failures indicate router or RBAC regressions.

Audit Notes:
    Failed RBAC assertions often mean route dependencies changed—compare with ``docs/rbac_and_remediation.md``
    before loosening expectations.

Side effects:
    Creates temporary directories only; removed by pytest.

See Also:
    ``docs/platform_api_contract.md``, ``tests/test_evidence_pipeline.py``.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def plat(tmp_path, monkeypatch):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)
    from backend.main import app

    return app


@pytest.fixture()
def admin_client(plat):  # type: ignore[no-untyped-def]
    return TestClient(
        plat,
        headers={"X-Operator-Role": "admin", "X-Operator-Id": "u-admin"},
    )


def test_compute_platform_metrics_merges_signals(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    signals = tmp_path / "platform_signals.jsonl"
    signals.write_text(
        "\n".join(
            [
                json.dumps({"kind": "proxy_registry_change"}),
                json.dumps({"kind": "proxy_enable_transition"}),
                json.dumps({"kind": "rollback_preview"}),
                json.dumps({"kind": "heartbeat"}),
                json.dumps({"kind": "heartbeat"}),
                json.dumps({"kind": "attribution_sample", "confidence": 0.6}),
                json.dumps({"kind": "unknown_actor_marker"}),
                json.dumps({"unknown_actor": True}),
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "failure_events.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "endpoints.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "remediation_previews.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "remediation_executions.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "audit.jsonl").write_text("", encoding="utf-8")

    from platform_core.metrics import compute_platform_metrics as _compute_local

    m = _compute_local(platform_root=tmp_path)
    assert m["proxy_changes_total"] >= 1
    assert m["proxy_enable_transitions_total"] >= 1
    assert m["rollback_preview_total"] >= 1
    assert m["endpoint_heartbeat_total"] >= 2
    assert m["unknown_actor_events_total"] >= 2
    assert m["attribution_confidence_avg"] is not None


def test_security_header_alias_reads_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)
    from backend.main import app

    sec = TestClient(app, headers={"X-Operator-Role": "security", "X-Operator-Id": "sec-u"})
    assert sec.get("/platform/audit?limit=5").status_code == 200


def test_security_blocked_heartbeat_ingest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    monkeypatch.setattr("platform_core.event_bus.platform_data_dir", lambda: tmp_path)
    from backend.main import app

    sec = TestClient(
        app,
        headers={"X-Operator-Role": "security", "X-Operator-Id": "sec-ingest"},
    )
    r = sec.post(
        "/platform/agent/heartbeat",
        json={"endpoint_id": "x", "os_family": "Windows", "os_version": "", "agent_version": "t"},
    )
    assert r.status_code == 403


def test_viewer_reads_metrics(plat) -> None:  # type: ignore[no-untyped-def]
    vw = TestClient(
        plat,
        headers={"X-Operator-Role": "viewer", "X-Operator-Id": "v-metrics"},
    )
    assert vw.get("/platform/metrics").status_code == 200


def test_attribution_route_with_fixture_context(admin_client: TestClient) -> None:  # type: ignore[no-untyped-def]
    from platform_core.storage import append_attribution_context, append_failure_event

    append_failure_event(
        {
            "event_id": "attrib-evt-1",
            "endpoint_id": "ep-fix",
            "severity": "low",
            "category": "proxy",
            "confidence": 0.42,
            "summary": "loopback stale proxy suspicion",
            "recommended_action_key": "inspect_proxy",
        },
    )
    append_attribution_context(
        {
            "event_id": "attrib-evt-1",
            "registry_context": {
                "before": {"ProxyEnable": "0"},
                "after": {"ProxyEnable": "1", "ProxyServer": "127.0.0.1:9999"},
            },
            "listeners": [{"port": "9999", "address": "127.0.0.1"}],
            "sysmon": [
                {
                    "EventID": "13",
                    "Image": "C:\\Fixtures\\corp_agent.exe",
                    "TargetObject": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyEnable",
                },
            ],
        },
    )
    r = admin_client.get("/platform/attribution/attrib-evt-1")
    assert r.status_code == 200
    body = r.json()
    assert body["event_id"] == "attrib-evt-1"
    assert body["attribution_level"] in (
        "sysmon_confirmed",
        "procmon_confirmed",
        "etw_confirmed",
        "heuristic",
        "listener_match",
    )
    assert isinstance(body["confidence"], (int, float))


def test_operator_dry_run_execute_allowed(admin_client: TestClient) -> None:
    from platform_core.storage import append_failure_event

    append_failure_event(
        {
            "event_id": "dry-ev-77",
            "endpoint_id": "ep-d",
            "severity": "low",
            "category": "dns",
            "confidence": 0.55,
            "summary": "",
            "recommended_action_key": "reset_dns",
        },
    )

    prv = admin_client.post(
        "/platform/remediation/preview",
        json={
            "endpoint_id": "ep-d",
            "failure_event_id": "dry-ev-77",
            "requested_action": "reset_dns",
        },
    )
    pid = prv.json()["preview_id"]

    op = TestClient(
        admin_client.app,
        headers={"X-Operator-Role": "operator", "X-Operator-Id": "op-live"},
    )
    exec_r = op.post(
        "/platform/remediation/execute",
        json={"preview_id": pid, "confirmation_phrase": "RUN_DNS_RESET", "dry_run": True},
    )
    assert exec_r.status_code == 200
    assert exec_r.json()["result"] == "dry_run"
