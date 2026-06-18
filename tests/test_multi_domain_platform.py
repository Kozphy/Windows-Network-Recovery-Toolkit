"""Multi-domain decision platform — models, adapters, engines, CLI, replay."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from src.domains.registry import all_adapters, get_adapter
from src.platform.audit import AuditRecord, append_audit, read_audit_tail
from src.platform.decision_engine import score_decision
from src.platform.evidence_engine import rank_hypotheses
from src.platform.models import DecisionOption, NormalizedEvent
from src.platform.outcome_engine import compute_metrics, record_outcome
from src.platform.policy_engine import validate_decision_policy
from src.platform.replay import run_pipeline
from src.platform.serialization import content_hash
from src.platform_handlers import (
    clear_platform_cache,
    cmd_platform_decide,
    cmd_platform_events,
    cmd_platform_metrics,
    cmd_platform_replay,
)

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    clear_platform_cache()
    yield
    clear_platform_cache()


def test_normalized_event_schema() -> None:
    schema = NormalizedEvent.model_json_schema()
    assert schema["title"] == "NormalizedEvent"
    ev = NormalizedEvent(
        event_id="t-1",
        domain="windows",
        category="test",
        title="Test",
        timestamp_utc="2026-06-04T00:00:00+00:00",
        source="unit",
    )
    assert ev.domain == "windows"


def test_evidence_confidence_bounded() -> None:
    ev = NormalizedEvent(
        event_id="win-proxy-localhost-001",
        domain="windows",
        category="proxy",
        title="Proxy",
        timestamp_utc="2026-06-04T10:00:00+00:00",
        source="fixture",
    )
    from src.platform.domains.fixture_graph import load_hypotheses

    adapter = get_adapter("windows")
    event = adapter.collect_events("proxy_localhost.json")[0]
    evidence = adapter.build_evidence(event)
    hypotheses = load_hypotheses(adapter, event)
    result = rank_hypotheses(ev, evidence, hypotheses)
    assert 0.0 <= result.confidence_score <= 1.0
    for h in result.ranked_hypotheses:
        assert 0.0 <= h.confidence <= 1.0
    assert result.explanation


def test_decision_ranking_deterministic() -> None:
    adapter = get_adapter("windows")
    r1 = run_pipeline(adapter, fixture_name="proxy_localhost.json", record_audit=False)
    r2 = run_pipeline(adapter, fixture_name="proxy_localhost.json", record_audit=False)
    assert r1.fingerprint == r2.fingerprint
    assert [x.decision.decision_id for x in r1.ranked_decisions] == [
        x.decision.decision_id for x in r2.ranked_decisions
    ]


def test_policy_blocks_destructive() -> None:
    ev = NormalizedEvent(
        event_id="x",
        domain="security",
        category="test",
        title="Kill process now",
        timestamp_utc="2026-06-04T00:00:00+00:00",
        source="fixture",
    )
    dec = DecisionOption(
        decision_id="d1",
        event_id="x",
        title="kill process on endpoint",
        action_type="execute_like",
        expected_benefit=0.9,
        risk_score=0.8,
    )
    status, _ = validate_decision_policy(ev, dec, confidence=0.9)
    assert status == "BLOCK_DESTRUCTIVE_ACTION"


def test_policy_blocks_low_confidence() -> None:
    ev = NormalizedEvent(
        event_id="x",
        domain="cloud",
        category="test",
        title="Research",
        timestamp_utc="2026-06-04T00:00:00+00:00",
        source="fixture",
    )
    dec = DecisionOption(
        decision_id="d2",
        event_id="x",
        title="Research logs",
        action_type="research",
        expected_benefit=0.5,
        risk_score=0.1,
    )
    status, _ = validate_decision_policy(ev, dec, confidence=0.3)
    assert status == "BLOCK_LOW_CONFIDENCE"


def test_outcome_metrics() -> None:
    dec = DecisionOption(
        decision_id="dec-inspect-proxy",
        event_id="e1",
        title="Inspect",
        action_type="research",
        expected_benefit=0.7,
        risk_score=0.1,
        confidence=0.6,
    )
    oc = record_outcome(dec, success=True, observed_result="ok")
    metrics = compute_metrics([oc], {"dec-inspect-proxy": dec}, domain_by_decision={"dec-inspect-proxy": "windows"})
    assert metrics.decision_accuracy == 1.0
    assert metrics.success_rate_by_domain["windows"] == 1.0


def test_audit_append_and_hash_stable(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    r1 = AuditRecord(
        timestamp_utc="2026-06-04T00:00:00+00:00",
        domain="windows",
        event_id="e1",
        command="replay",
        input_hash="abc",
        output_hash="def",
        policy_status="PREVIEW_ONLY",
        explanation="test",
    )
    append_audit(r1, path=path)
    rows = read_audit_tail(path=path)
    assert len(rows) == 1
    assert content_hash({"a": 1}) == content_hash({"a": 1})


@pytest.mark.parametrize("domain", ["windows", "security", "cloud", "infrastructure", "market"])
def test_adapter_has_fixtures(domain: str) -> None:
    adapter = get_adapter(domain)
    assert len(adapter.list_fixtures()) >= 3 or domain == "market"


def test_all_adapters_pipeline_stable(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    for adapter in all_adapters():
        for fname in adapter.list_fixtures():
            a = run_pipeline(adapter, fixture_name=fname, audit_path=audit, record_audit=True)
            b = run_pipeline(adapter, fixture_name=fname, audit_path=audit, record_audit=False)
            assert a.fingerprint == b.fingerprint


def test_platform_cli_events() -> None:
    assert (
        cmd_platform_events(
            argparse.Namespace(platform_domain="windows", platform_fixture=None, platform_format="json")
        )
        == 0
    )


def test_platform_cli_decide() -> None:
    assert (
        cmd_platform_decide(
            argparse.Namespace(event_id="win-proxy-localhost-001", platform_format="json", audit_path=None)
        )
        == 0
    )


def test_platform_cli_replay(tmp_path: Path) -> None:
    assert (
        cmd_platform_replay(
            argparse.Namespace(
                platform_domain=None,
                platform_fixture=None,
                platform_format="json",
                audit_path=str(tmp_path / "audit.jsonl"),
            )
        )
        == 0
    )


def test_platform_cli_metrics() -> None:
    assert cmd_platform_metrics(argparse.Namespace(platform_format="json", audit_path=None)) == 0


def test_score_decision_explainable() -> None:
    dec = DecisionOption(
        decision_id="d",
        event_id="e",
        title="Research",
        action_type="research",
        expected_benefit=0.6,
        risk_score=0.2,
        policy_status="ALLOW_RESEARCH",
    )
    ranked = score_decision(dec, hypothesis_confidence=0.7)
    assert "benefit=" in ranked.explanation
    assert 0.0 <= ranked.final_score <= 1.0


def test_cross_domain_consistency() -> None:
    """Every domain produces ranked decisions with policy_status set."""
    for adapter in all_adapters():
        fname = adapter.list_fixtures()[0]
        result = run_pipeline(adapter, fixture_name=fname, record_audit=False)
        assert result.top_decision is not None
        assert result.top_decision.policy_status
        assert result.top_decision.final_score >= 0.0
