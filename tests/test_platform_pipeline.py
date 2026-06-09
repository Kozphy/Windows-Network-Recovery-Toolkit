"""Unified platform pipeline — cross-domain consistency."""

from __future__ import annotations

from src.platform.registry import all_adapters
from src.platform.replay import run_pipeline


def test_pipeline_deterministic_all_domains() -> None:
    for adapter in all_adapters():
        for fname in adapter.list_fixtures():
            a = run_pipeline(adapter, fixture_name=fname, record_audit=False)
            b = run_pipeline(adapter, fixture_name=fname, record_audit=False)
            assert a.fingerprint == b.fingerprint
            assert a.top_decision is not None
            assert a.top_decision.policy_status


def test_adapters_only_collect_and_evidence() -> None:
    adapter = all_adapters()[0]
    ev = adapter.collect_events(adapter.list_fixtures()[0])[0]
    evidence = adapter.build_evidence(ev)
    assert ev.event_id
    assert isinstance(evidence, list)
