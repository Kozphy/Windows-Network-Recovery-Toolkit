"""Tests for local observability — structured logs, trace propagation, metrics."""

from __future__ import annotations

import json

import pytest

from src.platform_core.operability.context import observability_scope
from src.platform_core.operability.events import (
    record_blocked_action,
    record_control_test_executed,
    record_evidence_collected,
    record_incident_classified,
    record_policy_decision,
    record_remediation_preview,
)
from src.platform_core.operability.metrics_registry import (
    METRIC_AUDIT_APPENDED,
    METRIC_BLOCKED_ACTIONS,
    METRIC_CONTROL_TESTS_EXECUTED,
    METRIC_EVIDENCE_COLLECTED,
    METRIC_INCIDENTS_CLASSIFIED,
    METRIC_POLICY_DECISIONS,
    METRIC_REMEDIATION_PREVIEWS,
    METRIC_SPOOL_DEPTH,
    get_counter,
    get_gauge,
    render_prometheus_text,
    reset_metrics_for_tests,
)
from src.platform_core.operability.structured_logging import log_json


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    reset_metrics_for_tests()
    yield
    reset_metrics_for_tests()


def test_log_json_includes_trace_and_audit_id(capsys: pytest.CaptureFixture[str]) -> None:
    with observability_scope(trace_id="trace-abc", audit_id="audit-xyz"):
        record = log_json("info", "test_event", event_kind="unit_test")
    assert record["trace_id"] == "trace-abc"
    assert record["audit_id"] == "audit-xyz"
    err = capsys.readouterr().err
    parsed = json.loads(err.strip())
    assert parsed["trace_id"] == "trace-abc"
    assert parsed["audit_id"] == "audit-xyz"
    assert parsed["message"] == "test_event"


def test_evidence_collected_metric_increments() -> None:
    with observability_scope(trace_id="t1"):
        record_evidence_collected(endpoint_id="ep-1", source="test")
    assert get_counter(METRIC_EVIDENCE_COLLECTED, labels={"source": "test"}) == 1.0


def test_incident_classified_metric_labeled() -> None:
    record_incident_classified(classification="DEAD_PROXY_CONFIG", incident_id="INC-1")
    assert (
        get_counter(METRIC_INCIDENTS_CLASSIFIED, labels={"classification": "DEAD_PROXY_CONFIG"})
        == 1.0
    )


def test_control_tests_and_policy_metrics() -> None:
    record_control_test_executed(control_id="CTRL-001", result="PASS")
    record_policy_decision(decision="PREVIEW", action_id="disable_wininet_proxy")
    assert get_counter(METRIC_CONTROL_TESTS_EXECUTED, labels={"control_id": "CTRL-001", "result": "PASS"}) == 1.0
    assert get_counter(METRIC_POLICY_DECISIONS, labels={"decision": "PREVIEW"}) == 1.0


def test_blocked_action_and_remediation_preview_metrics() -> None:
    record_blocked_action(action_id="KILL_PROXY_PROCESS")
    record_remediation_preview(action_id="disable_wininet_proxy", dry_run=True)
    assert get_counter(METRIC_BLOCKED_ACTIONS, labels={"action_id": "KILL_PROXY_PROCESS"}) == 1.0
    assert (
        get_counter(METRIC_REMEDIATION_PREVIEWS, labels={"action_id": "disable_wininet_proxy"})
        == 1.0
    )


def test_audit_append_via_jsonl_hook(tmp_path: pytest.TempPathFactory) -> None:
    from src.logging.audit import append_jsonl

    path = tmp_path / "audit.jsonl"
    with observability_scope(trace_id="trace-hook"):
        append_jsonl(path, {"event_kind": "unit_audit"})
    assert path.is_file()
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["trace_id"] == "trace-hook"
    assert "audit_id" in row
    assert get_counter(METRIC_AUDIT_APPENDED) == 1.0


def test_spool_gauge_and_prometheus_render() -> None:
    from src.platform_core.operability.events import update_spool_queue_depth

    update_spool_queue_depth(7)
    assert get_gauge(METRIC_SPOOL_DEPTH) == 7.0
    text = render_prometheus_text()
    assert "spool_queue_depth 7.0" in text
    assert "# TYPE spool_queue_depth gauge" in text


def test_agent_collect_once_emits_trace_and_metrics(
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pathlib import Path

    from windows_network_toolkit.agent.read_only import collect_once

    fixture = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "agent"
        / "sample_evidence_bundle.json"
    )
    spool = tmp_path / "obs-spool.jsonl"
    result = collect_once(spool_path=spool, fixture_path=fixture, endpoint_id="ep-obs")
    assert result["trace_id"]
    assert result["audit_id"]
    assert get_counter(METRIC_EVIDENCE_COLLECTED, labels={"source": "read_only_agent"}) == 1.0
    assert get_gauge(METRIC_SPOOL_DEPTH) == 1.0
    row = json.loads(spool.read_text(encoding="utf-8").strip())
    assert row["trace_id"] == result["trace_id"]
    assert row["audit_id"] == result["audit_id"]


def test_metrics_endpoint_includes_operability_counters() -> None:
    from fastapi.testclient import TestClient

    from backend.main import app
    from src.platform_core.operability.metrics_registry import inc_counter

    inc_counter(METRIC_POLICY_DECISIONS, labels={"decision": "BLOCK"})
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'policy_decisions_total{decision="BLOCK"}' in response.text
