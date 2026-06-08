"""SRE platform tests — event sourcing, projections, MTTR, postmortems, failure domains."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from platform_core.sre.event_store import DomainEventStore
from platform_core.sre.failure_domains import (
    DomainDegradedError,
    FailureDomain,
    execute_in_domain,
    reset_domains_for_tests,
)
from platform_core.sre.incident_aggregate import IncidentAggregate
from platform_core.sre.investigation import run_investigation
from platform_core.sre.models import DomainEvent, IncidentPhase
from platform_core.sre.mttr import compute_incident_mttr_metrics
from platform_core.sre.postmortem import generate_postmortem
from platform_core.sre.projector import Projector, rebuild_incident
from platform_core.sre.rca import build_rca_report
from platform_core.sre.timeline import reconstruct_timeline


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("platform_core.storage.platform_data_dir", lambda: tmp_path)
    reset_domains_for_tests()
    yield
    reset_domains_for_tests()


def test_event_store_sequence_enforcement(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-1", title="proxy drift", store=store)
    events = store.load_aggregate_events(agg.incident_id)
    assert events[0].sequence == 1
    # duplicate sequence rejected
    bad = DomainEvent(
        sequence=1,
        aggregate_id=agg.incident_id,
        aggregate_type="incident",
        event_type="incident.acknowledged",
        correlation_id=agg.incident_id,
        payload={},
    )
    with pytest.raises(ValueError, match="sequence mismatch"):
        store.append(bad)


def test_deterministic_projection_replay(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-2", title="test", store=store)
    agg.acknowledge()
    agg.start_investigation()
    proj1 = rebuild_incident(agg.incident_id, store=store)
    proj2 = Projector.fold(store.load_aggregate_events(agg.incident_id), incident_id=agg.incident_id)
    assert proj1.phase == proj2.phase == IncidentPhase.INVESTIGATING
    assert proj1.acknowledged_at == proj2.acknowledged_at


def test_incident_lifecycle_mttr(tmp_path, monkeypatch) -> None:
    store = DomainEventStore()
    base = datetime(2026, 6, 4, 12, 0, 0, tzinfo=UTC)

    def fake_now():
        return base.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    monkeypatch.setattr("platform_core.models.utc_now_iso", fake_now)
    agg = IncidentAggregate.open(endpoint_id="ep-mttr", title="mttr test", store=store)
    detected = base

    monkeypatch.setattr(
        "platform_core.models.utc_now_iso",
        lambda: (detected + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    )
    agg.acknowledge()

    monkeypatch.setattr(
        "platform_core.models.utc_now_iso",
        lambda: (detected + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    )
    agg.start_investigation()

    monkeypatch.setattr(
        "platform_core.models.utc_now_iso",
        lambda: (detected + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    )
    agg.identify_root_cause(
        root_cause_summary="node.exe local proxy listener",
        accepted_hypothesis="Known developer tool",
        confidence_tier="correlated",
        evidence_event_ids=["evt-1"],
        limitations=["observation only"],
    )

    monkeypatch.setattr(
        "platform_core.models.utc_now_iso",
        lambda: (detected + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    )
    agg.resolve(resolution="proxy disabled and listener stopped")

    metrics = compute_incident_mttr_metrics(store=store)
    assert metrics.incident_count == 1
    assert metrics.resolved_count == 1
    assert metrics.mean_time_to_detect_seconds == 300.0
    assert metrics.mean_time_to_identify_seconds == 1800.0
    assert metrics.mean_time_to_recover_seconds == 3600.0


def test_timeline_reconstruction(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-tl", title="timeline", store=store)
    agg.acknowledge()
    entries = reconstruct_timeline(agg.incident_id, store=store)
    assert len(entries) >= 2
    assert entries[0].sequence <= entries[-1].sequence


def test_investigation_emits_hypothesis_event(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-inv", title="investigate", store=store)
    result = run_investigation(
        agg.incident_id,
        [
            {"signal_name": "wininet_proxy_enabled", "value": 1},
            {"signal_name": "localhost_proxy_detected"},
        ],
    )
    assert result["status"] == "ok"
    assert result["policy_outcome"] == "PREVIEW"
    proj = rebuild_incident(agg.incident_id, store=store)
    assert proj.phase in (IncidentPhase.INVESTIGATING, IncidentPhase.ROOT_CAUSE_IDENTIFIED)
    assert proj.decision_run_ids


def test_rca_includes_limitations(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-rca", title="rca", store=store)
    report = build_rca_report(agg.incident_id)
    assert any("Observation" in lim or "investigative" in lim.lower() for lim in report.limitations)


def test_postmortem_generation(tmp_path) -> None:
    store = DomainEventStore()
    agg = IncidentAggregate.open(endpoint_id="ep-pm", title="postmortem test", store=store)
    agg.acknowledge()
    agg.start_investigation()
    agg.resolve(resolution="fixed")
    doc = generate_postmortem(agg.incident_id, store=store)
    md = doc.to_markdown()
    assert "Postmortem" in md
    assert agg.incident_id in md
    assert "MTTR" in md


def test_failure_domain_isolation(tmp_path) -> None:
    domain = FailureDomain.HYPOTHESIS_ENGINE
    cb_failures = 0

    def flaky() -> str:
        nonlocal cb_failures
        cb_failures += 1
        raise RuntimeError("probe down")

    for _ in range(5):
        with pytest.raises(RuntimeError):
            execute_in_domain(domain, flaky, correlation_id="test")

    with pytest.raises(DomainDegradedError):
        execute_in_domain(domain, flaky, correlation_id="test")
