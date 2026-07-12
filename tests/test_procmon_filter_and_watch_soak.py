"""Procmon filter set + short proxy-watch soak."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.proxy_guard.procmon_filter_set import (
    FILTER_SET_ID,
    build_procmon_filter_rules,
    export_procmon_filter_set,
    format_procmon_filter_instructions,
    procmon_filter_set_payload,
)
from src.proxy_guard.proxy_watch import run_proxy_watch_loop


def test_procmon_filter_set_has_regsetvalue_and_proxy_paths() -> None:
    payload = procmon_filter_set_payload()
    assert payload["filter_set_id"] == FILTER_SET_ID
    rules = build_procmon_filter_rules()
    assert rules[0].column == "Operation"
    assert rules[0].value == "RegSetValue"
    paths = [r.value for r in rules[1:]]
    assert any("ProxyEnable" in p for p in paths)
    assert any("ProxyServer" in p for p in paths)
    text = format_procmon_filter_instructions()
    assert "Drop Filtered Events" in text
    assert "proxy-attribution --procmon" in text


def test_procmon_filter_set_export_and_shipped_json(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "filter.json"
    written = export_procmon_filter_set(out)
    assert written.is_file()
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded["filter_set_id"] == FILTER_SET_ID
    assert len(loaded["rules"]) >= 2

    shipped = (
        Path(__file__).resolve().parents[1]
        / "telemetry"
        / "procmon"
        / "wininet_proxy_regsetvalue.filter.json"
    )
    assert shipped.is_file()
    shipped_payload = json.loads(shipped.read_text(encoding="utf-8"))
    assert shipped_payload["filter_set_id"] == FILTER_SET_ID
    assert shipped_payload["rules"] == loaded["rules"]


def _state(enable: int, server: str = "") -> dict:
    return {
        "proxy_enable": enable,
        "proxy_server": server,
        "auto_config_url": "",
        "proxy_override": "",
        "parsed_proxy_server": {},
    }


def test_watch_soak_stable_when_unchanged(tmp_path: Path) -> None:
    states = [_state(0), _state(0), _state(0)]
    clock = {"t": 0.0}

    def mono() -> float:
        return clock["t"]

    def sleep(sec: float) -> None:
        clock["t"] += sec

    with (
        patch("src.proxy_guard.proxy_watch.snapshot_wininet_state", side_effect=states + [_state(0)] * 10),
        patch("src.proxy_guard.proxy_watch.load_watch_policy", return_value={}),
    ):
        result = run_proxy_watch_loop(
            repo_root=tmp_path,
            interval_seconds=1.0,
            once=False,
            soak_minutes=0.05,  # 3 seconds
            exit_on_rewrite=True,
            sleep_fn=sleep,
            monotonic_fn=mono,
            run=MagicMock(),
        )
    assert result is not None
    assert result.status == "STABLE"
    assert result.changes_observed == 0
    assert result.samples >= 2


def test_watch_soak_rewrite_detected(tmp_path: Path) -> None:
    states = [_state(0), _state(1, "127.0.0.1:9999")]
    clock = {"t": 0.0}

    def mono() -> float:
        return clock["t"]

    def sleep(sec: float) -> None:
        clock["t"] += sec

    with (
        patch("src.proxy_guard.proxy_watch.snapshot_wininet_state", side_effect=states),
        patch("src.proxy_guard.proxy_watch.load_watch_policy", return_value={}),
        patch("src.proxy_guard.proxy_watch.capture_enriched_process_snapshot", return_value={}),
        patch(
            "src.proxy_guard.proxy_watch.attribute_proxy_change",
            return_value={"candidates": [], "limitations": []},
        ),
        patch("src.proxy_guard.proxy_watch.emit_proxy_change_detected_audit"),
        patch("src.proxy_guard.proxy_watch._emit_v2_watch_events"),
        patch("src.proxy_guard.proxy_watch._run_causation_and_print", return_value=None),
        patch("src.proxy_guard.proxy_watch._run_final_causation_if_enabled", return_value=None),
        patch("src.proxy_guard.proxy_watch._localhost_health_for_watch", return_value=None),
        patch("src.proxy_guard.proxy_watch._print_human_banner"),
        patch("src.proxy_guard.proxy_watch.diff_wininet_states", return_value={"changed": True, "changed_fields": ["ProxyEnable"]}),
    ):
        result = run_proxy_watch_loop(
            repo_root=tmp_path,
            interval_seconds=1.0,
            once=False,
            soak_minutes=5.0,
            exit_on_rewrite=True,
            sleep_fn=sleep,
            monotonic_fn=mono,
            run=MagicMock(),
        )
    assert result is not None
    assert result.status == "REWRITE_DETECTED"
    assert result.changes_observed >= 1
    assert result.baseline_proxy_enable == 0
    assert result.last_proxy_enable == 1
