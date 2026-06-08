"""Tests for platform_core.reliability — deterministic pipeline, replay, policy, audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.reliability.audit_integrity import sign_decision_record, verify_decision_record
from platform_core.reliability.decision_engine import persist_decision, run_platform_decision
from platform_core.reliability.event_pipeline import EventPipeline, normalize_raw_observation
from platform_core.reliability.evidence_graph import build_evidence_graph
from platform_core.reliability.hypothesis_engine import rank_hypotheses
from platform_core.reliability.models import NormalizedPlatformEvent, PlatformState
from platform_core.reliability.platform_states import transition_platform_state
from platform_core.reliability.policy_config import PolicyConfig, evaluate_platform_policy
from platform_core.reliability.resilience import CircuitBreaker, retry_with_backoff
from platform_core.reliability.time_travel import TimeTravelReplay


@pytest.fixture
def isolated_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EventPipeline:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    return EventPipeline(path=tmp_path / "platform_events.jsonl")


def test_normalize_registry_event() -> None:
    ev = normalize_raw_observation(
        {"source": "registry", "signal_name": "wininet_proxy_enabled", "value": 1},
        endpoint_id="ep-1",
    )
    assert ev.source_kind == "registry"
    assert ev.signal_name == "wininet_proxy_enabled"
    assert ev.endpoint_id == "ep-1"


def test_state_transition_proxy_path() -> None:
    events = [
        normalize_raw_observation({"signal_name": "wininet_proxy_enabled", "value": 1}),
        normalize_raw_observation({"signal_name": "localhost_proxy_detected"}),
        normalize_raw_observation({"signal_name": "browser_https_failed"}),
    ]
    transitions, path = transition_platform_state(events)
    assert PlatformState.NORMAL in path
    assert PlatformState.LOCAL_PROXY_ENABLED in path
    assert len(transitions) >= 1
    assert all(t.replayable for t in transitions)


def test_hypothesis_ranking_developer_tool() -> None:
    events = [
        NormalizedPlatformEvent(
            source_kind="network_telemetry",
            signal_name="localhost_proxy_detected",
            payload={"process_name": "node.exe"},
        ),
        NormalizedPlatformEvent(source_kind="registry", signal_name="wininet_proxy_enabled"),
    ]
    ranking = rank_hypotheses(events, context={"allowlist_match": True})
    assert ranking
    assert ranking[0].category in ("known_developer_tool", "misconfiguration", "security_product")


def test_malware_hypothesis_capped_without_proof() -> None:
    events = [
        NormalizedPlatformEvent(
            source_kind="network_telemetry",
            signal_name="external_proxy",
            payload={"unresolved_path": True},
        ),
    ]
    ranking = rank_hypotheses(events, context={"external_proxy": True, "unresolved_path": True})
    malware = next((h for h in ranking if h.category == "potential_malware"), None)
    assert malware is not None
    outcome, codes = evaluate_platform_policy(hypothesis=malware, has_proof_tier=False)
    assert outcome == "PREVIEW"
    assert any("malware" in c for c in codes)


def test_policy_blocks_destructive_action() -> None:
    policy = PolicyConfig.production_defaults()
    outcome, codes = evaluate_platform_policy(
        hypothesis=None,
        policy=policy,
        requested_action="firewall_reset",
    )
    assert outcome == "BLOCK"
    assert any("blocked_action" in c for c in codes)


def test_evidence_graph_builds_nodes() -> None:
    events = [
        normalize_raw_observation({"source_kind": "sysmon", "signal_name": "registry_write_proxyenable"}),
        normalize_raw_observation({"signal_name": "localhost_proxy_detected"}),
    ]
    transitions, _ = transition_platform_state(events)
    graph = build_evidence_graph(events, transitions, process_snapshot={"process_name": "node.exe"})
    summary = graph.to_jsonable()
    assert summary["node_count"] >= 2
    assert summary["edge_count"] >= 1


def test_decision_pipeline_preview_default(isolated_pipeline: EventPipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    obs = [
        {"signal_name": "wininet_proxy_enabled", "value": 1},
        {"signal_name": "localhost_proxy_detected"},
    ]
    record = run_platform_decision(obs, endpoint_id="test-ep")
    assert record.policy_outcome == "PREVIEW"
    assert record.state_path
    assert record.audit_signature
    ok, _ = verify_decision_record(record)
    assert ok


def test_persist_and_replay_parity(isolated_pipeline: EventPipeline, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    obs = [
        {"source_kind": "registry", "signal_name": "wininet_proxy_enabled", "value": 1},
        {"source_kind": "network_telemetry", "signal_name": "localhost_proxy_detected"},
    ]
    record = run_platform_decision(obs, endpoint_id="replay-ep", run_id="run-test-001")
    events = [
        normalize_raw_observation(o, endpoint_id="replay-ep").model_copy(update={"event_id": eid})
        for o, eid in zip(obs, record.event_ids, strict=False)
    ]
    persist_decision(record, events=events, pipeline=isolated_pipeline)

    replay = TimeTravelReplay.load_and_replay("run-test-001", path=tmp_path / "platform_decisions.jsonl")
    assert replay.parity["policy_outcome"]
    assert replay.parity["state_path"]


def test_signed_audit_tamper_detection() -> None:
    record = run_platform_decision([{"signal_name": "wininet_proxy_enabled"}], endpoint_id="audit-ep")
    signed = sign_decision_record(record, secret="test-secret")
    ok, _ = verify_decision_record(signed, secret="test-secret")
    assert ok
    tampered = signed.model_copy(update={"accepted_hypothesis": "tampered"})
    ok2, reason = verify_decision_record(tampered, secret="test-secret")
    assert not ok2
    assert reason == "signature_mismatch"


def test_circuit_breaker_opens_after_failures() -> None:
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60)

    def fail() -> None:
        raise ValueError("probe failed")

    cb.call(fail)
    cb.call(fail)
    assert cb.state == "open"
    assert cb.call(fail) is None


def test_retry_with_backoff_succeeds() -> None:
    attempts = {"n": 0}

    def flaky() -> str:
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    assert retry_with_backoff(flaky, max_attempts=3) == "ok"
    assert attempts["n"] == 2


def test_append_only_pipeline(isolated_pipeline: EventPipeline) -> None:
    ev = isolated_pipeline.ingest({"signal_name": "proxy_enable", "value": 1})
    rows = list(isolated_pipeline.iter_events())
    assert len(rows) == 1
    assert rows[0].event_id == ev.event_id
