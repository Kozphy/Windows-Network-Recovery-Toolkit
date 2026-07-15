"""Listener classification for localhost proxy attribution."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.attribution.classifier import classify_listener
from src.platform_core.attribution.models import (
    ListenerClassification,
    ProcessAttribution,
    ProxyStateSnapshot,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "erp"


def test_no_proxy_when_disabled() -> None:
    proxy = ProxyStateSnapshot(wininet_proxy_enable=0)
    cls, _, _ = classify_listener(proxy, ProcessAttribution(), listener_detected=False)
    assert cls == ListenerClassification.NO_PROXY


def test_dead_proxy_config() -> None:
    proxy = ProxyStateSnapshot(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:8080",
        localhost_port=8080,
    )
    cls, rationale, _ = classify_listener(proxy, ProcessAttribution(), listener_detected=False)
    assert cls == ListenerClassification.DEAD_PROXY_CONFIG
    assert "8080" in rationale


def test_resolve_listener_matches_wildcard_bind() -> None:
    """Node/Cursor often bind 0.0.0.0:port — must not be reported as dead."""
    from src.platform_core.attribution.collector import resolve_listener_process

    netstat = (
        "  TCP    0.0.0.0:60072          0.0.0.0:0              LISTENING       62284\n"
        "  TCP    [::]:60072             [::]:0                 LISTENING       62284\n"
    )

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        first = cmd[0] if isinstance(cmd, (list, tuple)) and cmd else ""
        if first == "netstat":
            r = R()
            r.stdout = netstat
            return r
        if first == "tasklist":
            r = R()
            r.stdout = '"node.exe","62284","Console","1","100 K"\n'
            return r
        r = R()
        r.stdout = '{"Path":"C:\\\\node.exe","Cmd":"node","Parent":1,"User":"u","Start":""}'
        return r

    attr, found = resolve_listener_process(60072, run=fake_run, timeout=5.0)
    assert found is True
    assert attr.pid == 62284
    assert "node" in (attr.process_name or "").lower()


def test_known_dev_proxy() -> None:
    proxy = ProxyStateSnapshot(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:3000",
        localhost_port=3000,
    )
    proc = ProcessAttribution(pid=1234, process_name="node.exe", command_line="webpack-dev-server")
    cls, _, _ = classify_listener(proxy, proc, listener_detected=True)
    assert cls == ListenerClassification.KNOWN_DEV_PROXY


def test_suspicious_proxy_keywords() -> None:
    proxy = ProxyStateSnapshot(
        wininet_proxy_enable=1,
        wininet_proxy_server="127.0.0.1:8888",
        localhost_port=8888,
    )
    proc = ProcessAttribution(pid=99, process_name="unknown.exe", command_line="mitm-proxy --listen")
    cls, _, lim = classify_listener(proxy, proc, listener_detected=True)
    assert cls == ListenerClassification.SUSPICIOUS_PROXY
    assert any("human review" in x.lower() for x in lim)


def test_fixture_snapshot_loads() -> None:
    data = json.loads((FIXTURES / "attribution_dead_proxy.json").read_text(encoding="utf-8"))
    assert data["classification"] == "DEAD_PROXY_CONFIG"
