"""Regression tests for proxy_investigation collectors."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.proxy_investigation.collectors import collect_dev_process_correlation, collect_proxy_state


def _fake_reg(enable: int = 0, server: str | None = None):
    return type(
        "R",
        (),
        {
            "proxy_enable": enable,
            "proxy_server": server,
            "proxy_override": None,
            "auto_config_url": None,
            "auto_detect": None,
            "to_dict": lambda self: {"proxy_enable": enable, "proxy_server": server},
        },
    )()


def _fake_snap():
    return type(
        "S",
        (),
        {
            "winhttp_proxy": "Direct",
            "winhttp_direct_access": True,
            "winhttp_proxy_server_literal": None,
            "proxy_enable": 0,
            "proxy_server": None,
            "proxy_override": None,
            "auto_config_url": None,
            "auto_detect": None,
            "captured_at": "2026-01-01T00:00:00Z",
            "user_http_proxy": None,
            "user_https_proxy": None,
            "user_all_proxy": None,
            "user_no_proxy": None,
            "git_http_proxy": None,
            "git_https_proxy": None,
            "npm_proxy": None,
            "npm_https_proxy": None,
        },
    )()


def test_collect_proxy_state_parses_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.proxy_investigation.collectors.read_proxy_registry",
        lambda **_: _fake_reg(1, "127.0.0.1:64642"),
    )
    monkeypatch.setattr(
        "src.proxy_investigation.collectors.capture_proxy_snapshot",
        lambda **_: _fake_snap(),
    )

    state = collect_proxy_state(run=MagicMock())
    assert state["parsed_proxy"]["localhost_port"] == 64642
    assert state["parsed_proxy"]["is_localhost_proxy"] is True
    assert "registry_merge" in state


def test_collect_dev_process_correlation_uses_parsed_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.proxy_investigation.collectors.read_proxy_registry",
        lambda **_: _fake_reg(1, "127.0.0.1:57324"),
    )
    monkeypatch.setattr(
        "src.proxy_investigation.collectors.capture_process_inventory",
        lambda **_: {"process_rows": [], "listening_pids": []},
    )

    block = collect_dev_process_correlation(run=MagicMock())
    assert block["listening_pids"] == []
