"""Unified events, attribution semantics, remediation gate engine, replay, registry compatibility."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.attribution.polling import PollingHeuristicProvider
from platform_core.attribution.windows_eventlog import WindowsEventLogAttributionProvider
from platform_core.event_bus import append_event, read_events, validate_schema_version
from platform_core.events import SUPPORTED_SCHEMA_VERSIONS, NormalizedEvent, PolicyDecisionPayload
from platform_core.policy import ACTION_REGISTRY
from platform_core.policy.engine import OperatorContext, evaluate
from platform_core.privacy import redact_text, sanitize_ip, stable_endpoint_hash
from platform_core.replay.runner import accumulate_replay_counters, summarize_inline

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "platform"


def test_normalized_event_schema_roundtrip() -> None:
    ev = NormalizedEvent(
        schema_version="1",
        event_id="e-schema",
        event_type="normalized.remediation_candidate",
        endpoint_id_hash="f" * 32,
        signals={"remediation_action": "inspect_proxy"},
    )
    ev.assert_supported_schema()
    dumped = ev.model_dump()
    restored = NormalizedEvent.model_validate(dumped)
    assert restored.event_id == "e-schema"


def test_schema_versions_include_one() -> None:
    assert "1" in SUPPORTED_SCHEMA_VERSIONS


def test_event_bus_append_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "evt.jsonl"
    row = {
        "schema_version": "1",
        "event_id": "bus-1",
        "event_type": "normalized.remediation_candidate",
        "timestamp": "2026-01-02T12:00:00+00:00",
        "source": "fixture",
        "severity": "low",
        "endpoint_id_hash": "aa" + "0" * 30,
        "signals": {
            "remediation_action": "reset_dns",
            "simulated_operator_role": "admin",
            "telemetry": {},
        },
    }
    append_event(row, path=p)
    good, errs = read_events(p, limit=10)
    assert not errs and len(good) == 1
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"schema_version": "999", "junk": True}, ensure_ascii=False) + "\n")
    _, errs_bad = read_events(p, limit=10)
    assert errs_bad


def test_event_bus_bad_line_tolerance(tmp_path: Path) -> None:
    p = tmp_path / "bad.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{not-json\n{"schema_version":"1","event_id":"e","event_type":"x","severity":"low","endpoint_id_hash":"' + ("b" * 32) + '","signals":{"remediation_action":"inspect_proxy"}}\n', encoding="utf-8")
    good, errs = read_events(p, limit=5)
    assert len(good) == 1
    assert errs


def test_privacy_masks_private_ips_and_paths() -> None:
    """Mask private IPv4; coarse path redaction for free-text payloads."""

    assert sanitize_ip("192.168.10.44") == "192.168.x.x"
    assert "192.168.x.x" in redact_text("traffic to 192.168.44.88 seen")


def test_stable_endpoint_hash_no_plain_hostname_persisted() -> None:
    h1 = stable_endpoint_hash("NODE-A", "10")
    h2 = stable_endpoint_hash("NODE-A", "10")
    assert h1 == h2
    assert "NODE" not in h1


def test_gate_default_deny_live_for_operator_reset_proxy() -> None:
    g = evaluate(
        {"telemetry": {}},
        "reset_proxy",
        OperatorContext(role="operator", surface="api"),
    )
    assert g.preview_allowed
    assert g.execute_allowed is False
    assert "operator_may_preview_only_live_requires_admin" in g.reason_codes


def test_gate_admin_reset_proxy_live_eligible_but_needs_confirmation() -> None:
    g = evaluate(
        {},
        "reset_proxy",
        OperatorContext(role="admin", surface="api"),
    )
    assert g.preview_allowed and g.execute_allowed
    assert g.required_confirmation


def test_gate_high_risk_firewall_blocked_execution() -> None:
    g = evaluate({}, "reset_firewall", OperatorContext(role="admin", surface="api"))
    assert g.preview_allowed is False
    assert g.execute_allowed is False


def test_gate_arbitrary_always_forbidden() -> None:
    v = evaluate({}, "arbitrary_command", OperatorContext(role="admin", surface="api"))
    assert v.preview_allowed is False
    assert v.execute_allowed is False


def test_attribution_heuristic_vs_eventlog_placeholder() -> None:
    polling = PollingHeuristicProvider()
    assert polling.attribute({"process_names_sample": ["clash-win.exe"]}).confidence == "low"
    evt = WindowsEventLogAttributionProvider().attribute({"enable_eventlog_experimental": False})
    assert evt.confidence == "none"


def test_attribution_protocol_compliance() -> None:
    p = PollingHeuristicProvider()
    assert callable(p.attribute)


def test_accumulate_fixture_file_replay_summaries() -> None:
    src = FIXTURE_DIR / "proxy_loopback_enabled.json"
    blob = json.loads(src.read_text(encoding="utf-8"))
    summary = summarize_inline([blob])
    assert summary.total_events == 1
    suspicious = json.loads((FIXTURE_DIR / "suspicious_proxy_change.json").read_text(encoding="utf-8"))
    s2 = summarize_inline([blob, suspicious])
    assert s2.total_events >= 1


def test_accumulate_manual_change_detection() -> None:
    stale_decision = {
        "execute_allowed": True,
        "preview_allowed": True,
        "reason_codes": ["legacy_ok"],
        "required_role": "admin",
        "required_confirmation": "RUN_DNS_RESET",
        "risk_tier": "medium",
    }
    rec = {
        "schema_version": "1",
        "event_id": "diff-1",
        "event_type": "normalized.remediation_candidate",
        "severity": "low",
        "endpoint_id_hash": "c" * 32,
        "signals": {"remediation_action": "reset_dns", "simulated_operator_role": "operator"},
        "policy_decision": stale_decision,
    }
    s = accumulate_replay_counters([rec])
    assert s.changed_decisions == 1
    assert s.newly_blocked_execute == 1


def test_validate_schema_helpers() -> None:
    ok, err = validate_schema_version({"schema_version": "1"})
    assert ok and err == ""
    assert not validate_schema_version({})[0]


def test_remediation_registry_action_registry_has_dns() -> None:
    meta = ACTION_REGISTRY.get("reset_dns")
    assert meta and meta.get("phrase") == "RUN_DNS_RESET"


def test_policy_decision_payload_aliases_engine_shape() -> None:
    PolicyDecisionPayload(execute_allowed=True, preview_allowed=True, reason_codes=["ok"], risk_tier="medium")
