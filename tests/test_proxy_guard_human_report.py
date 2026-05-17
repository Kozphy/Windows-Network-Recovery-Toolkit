"""Tests for human-readable proxy guard watch formatters."""

from __future__ import annotations

from src.proxy_guard.human_report import (
    format_proxy_guard_change,
    format_proxy_state_change_v1,
    format_watch_report,
    load_watch_jsonl,
)


def _sample_v2_reenable() -> dict:
    return {
        "schema_version": 2,
        "timestamp": "2026-05-16T09:40:31.874509+00:00",
        "event": "proxy_guard_change",
        "before_snapshot": {"proxy_enable": 0, "proxy_server": "127.0.0.1:58644"},
        "after_snapshot": {"proxy_enable": 1, "proxy_server": "127.0.0.1:58644"},
        "attribution": {
            "mode": "best_effort_process_snapshot",
            "confidence": "low",
            "process": {"pid": 28900, "ppid": 6884, "name": "node.exe", "exe": None, "cmdline": None},
            "limitations": ["polling_based_attribution_not_registry_writer_proof"],
        },
        "policy_decision": {
            "decision": "allowed",
            "reason": "localhost_loopback_policy_allow",
            "matched_rule": "localhost_listener_present",
        },
        "rollback_result": {"status": "skipped_not_blocked", "detail": "localhost_loopback_policy_allow"},
    }


def test_format_proxy_guard_change_mentions_reenable() -> None:
    text = format_proxy_guard_change(_sample_v2_reenable())
    assert "Proxy turned ON" in text
    assert "node.exe" in text
    assert "28900" in text
    assert "127.0.0.1:58644" in text
    assert "reset_proxy.bat" in text


def test_format_watch_report_empty() -> None:
    assert "No proxy watch events" in format_watch_report([])


def test_v1_format_chatgpt_hint() -> None:
    text = format_proxy_state_change_v1(
        {
            "timestamp_utc": "2026-05-17T07:50:05Z",
            "old_enable": 0,
            "new_enable": 1,
            "old_server_masked": "[IP]:56186",
            "new_server_masked": "[IP]:56186",
            "recent_processes": ["ChatGPT", "msedge"],
        }
    )
    assert "ChatGPT" in text
    assert "Proxy turned ON" in text
    assert "proxy-guard" in text


def test_load_watch_jsonl_tail(tmp_path) -> None:
    path = tmp_path / "watch.jsonl"
    path.write_text(
        '{"event":"a"}\n{"event":"b"}\n{"event":"c"}\n',
        encoding="utf-8",
    )
    rows = load_watch_jsonl(path, tail_n=2)
    assert [r["event"] for r in rows] == ["b", "c"]
