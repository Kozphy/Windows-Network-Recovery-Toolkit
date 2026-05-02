"""Offline regression coverage for ``evidence/`` parsers and :func:`~evidence.attribution_engine.build_attribution`.

Module responsibility:
    Lock parsing of registry-diff hints, Sysmon EID13 fixtures, Procmon CSV-shaped rows, and the stub
    ETW reader without touching the Windows registry or live Event Log subscriptions.

System placement:
    Complements docs in ``docs/evidence_pipeline.md``; does not exercise ``backend.platform_routes`` HTTP.

Key invariants:
    * Assertions encode the honest attribution boundary—heuristic tiers unless Sysmon paths satisfy
      :func:`~evidence.attribution_engine.build_attribution` elevation rules mirrored in production code.
    * No subprocess or network I/O—all inputs are dict literals.

Input assumptions:
    Fixture dicts mimic exporter column names tolerated by parsers (case variants included where tested).

Raises:
    Test failures surface contract drift—pytest itself raises ``AssertionError`` on mismatch.

Audit Notes:
    When attribution scoring rules change, update expected ``attribution_level`` / ``notes`` substrings here
    and cite the changelog in PR text so auditors can reconcile JSONL replay diffs.

See Also:
    ``tests/test_platform_reliability_rbac_metrics.py`` for HTTP-layer attribution fixtures.
"""

from __future__ import annotations

from evidence.attribution_engine import build_attribution, parse_sysmon_sequence
from evidence.etw_reader import ETWTraceBatch, StubETWReader
from evidence.procmon_importer import ProcmonRegistryWrite, procmon_concerns_proxy, procmon_row_to_dict
from evidence.registry_event_parser import describe_diff, parse_registry_hint
from evidence.sysmon_reader import parse_sysmon_row, registry_event_concerns_internet_settings


def test_parse_registry_hint_proxy_delta() -> None:
    h = parse_registry_hint(
        {
            "before": {"ProxyEnable": "0"},
            "after": {"ProxyEnable": "1", "ProxyServer": "127.0.0.1:8899"},
        },
    )
    assert h.proxy_enable_after == "1"
    assert describe_diff(h)


def test_sysmon_event_parse_and_filter() -> None:
    row = {
        "EventID": "13",
        "Image": "C:\\Tools\\setter.exe",
        "TargetObject": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\\ProxyEnable",
        "UtcTime": "2026-05-02T12:00:00.0000000Z",
    }
    ev = parse_sysmon_row(row)
    assert ev is not None
    assert registry_event_concerns_internet_settings(ev)


def test_procmon_proxy_row_detected() -> None:
    r = ProcmonRegistryWrite(
        process_name="evil.exe",
        operation="RegSetValue",
        path="HKCU\\...\\Internet Settings",
        detail="Binary Data: ProxyServer → 127.0.0.1:8899",
    )
    assert procmon_concerns_proxy(r)
    procmon_row_to_dict(r)


def test_attribution_heuristic_only_without_sysmon_procmon_etw() -> None:
    res = build_attribution(
        event_id="e-heur",
        failure_summary="stale localhost proxy",
        registry_context={"before": {"ProxyEnable": "0"}, "after": {"ProxyEnable": "1"}},
        process_inventory={"candidate_name": "svchost.exe"},
        listeners=[{"address": "127.0.0.1", "port": "8899"}],
    )
    assert res.attribution_level == "heuristic"
    assert 0.0 <= res.confidence <= 1.0
    assert "Honest_boundary" in res.notes


def test_attribution_confirmed_by_sysmon_path() -> None:
    rows = parse_sysmon_sequence(
        [
            {
                "EventID": "13",
                "Image": "C:\\Tools\\proxy_flipper.exe",
                "TargetObject": "Internet Settings\\\\ProxyEnable",
            },
        ],
    )
    res = build_attribution(
        event_id="e-sys",
        sysmon_events=rows,
        registry_context={"after": {"ProxyEnable": "1"}},
        listeners=[{"address": "", "port": "8899"}],
    )
    assert res.attribution_level == "sysmon_confirmed"


def test_attribution_listener_match_without_structured_telemetry() -> None:
    res = build_attribution(
        event_id="e-listener",
        registry_context={
            "before": {"ProxyEnable": "0"},
            "after": {"ProxyEnable": "1", "ProxyServer": "127.0.0.1:7788"},
        },
        listeners=[{"address": "127.0.0.1", "port": "7788"}],
    )
    assert res.attribution_level == "listener_match"


def test_stub_etw_reader_drain_batches() -> None:
    reader = StubETWReader()
    reader.push_batch(ETWTraceBatch(provider="Microsoft-Windows-Kernel-Registry", events=[]))
    assert reader.drain_batches()
