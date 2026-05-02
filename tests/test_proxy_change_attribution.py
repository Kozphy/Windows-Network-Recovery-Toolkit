"""Offline regressions for proxy-watch drift classification + probabilistic attribution."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.proxy_guard.audit import emit_proxy_change_detected_audit, proxy_change_audit_jsonl_path
from src.proxy_guard.change_attribution import attribute_proxy_change
from src.proxy_guard.evidence_import import confidence_boost_from_csv
from src.proxy_guard.parser import parse_proxy_server
from src.proxy_guard.wininet_change_diff import diff_wininet_states


def _minimal_state(enable: int, server: str | None, pac: str | None = None) -> dict:
    parsed = parse_proxy_server(server)
    return {
        "proxy_enable": enable,
        "proxy_server": server,
        "auto_config_url": pac,
        "auto_detect": None,
        "proxy_override": None,
        "is_enabled": enable == 1,
        "parsed_proxy_server": {
            "raw": parsed.raw,
            "is_localhost_proxy": parsed.is_localhost_proxy,
            "localhost_host": parsed.localhost_host,
            "localhost_port": parsed.localhost_port,
            "proxy_mode": "manual_localhost" if parsed.is_localhost_proxy else "manual_remote",
        },
    }


def test_diff_high_when_enabled_localhost_transition() -> None:
    before = _minimal_state(0, None)
    after = _minimal_state(1, "127.0.0.1:55509")
    d = diff_wininet_states(before, after)
    assert d["changed"]
    assert d["risk_level"] == "high"
    assert "ProxyEnable" in d["changed_fields"]


def test_diff_low_when_disable_transition() -> None:
    before = _minimal_state(1, "10.2.3.4:8080")
    after = _minimal_state(0, "10.2.3.4:8080")
    pol = {}
    d = diff_wininet_states(before, after, policy=pol)
    assert d["changed"]
    assert d["risk_level"] == "low"


def test_attribution_listen_match_boosts_candidate() -> None:
    diff = diff_wininet_states(_minimal_state(0, None), _minimal_state(1, "127.0.0.1:9"))
    now = _minimal_state(1, "127.0.0.1:9")
    invent = {
        "process_rows": [
            {"pid": 42, "parent_pid": 7, "process_name": "node.exe", "executable_path": "C:\\n\\node.exe", "command_line": "node x", "creation_time_utc": None},
        ],
        "localhost_listener_block": {"owners": [{"pid": 42, "process_name": "node.exe"}], "notes": []},
        "listening_pids": [42],
        "collection_warnings": [],
    }
    out = attribute_proxy_change(proxy_diff=diff, current_state=now, inventory=invent)
    assert out["confidence"] >= 0.45
    assert out["primary_suspect"]["pid"] == 42


def test_allowlist_port_softens_high_risk_guard() -> None:
    pol = {"allowed_proxy_ports": [55509], "deny_unknown_localhost_proxy": True}
    before = _minimal_state(0, None)
    after = _minimal_state(1, "127.0.0.1:55509")
    d = diff_wininet_states(before, after, policy=pol)
    assert d["risk_level"] == "medium"


def test_parse_proxy_server_http_https_scheme_localhost() -> None:
    p = parse_proxy_server("http=127.0.0.1:88;https=127.0.0.1:443")
    assert p.is_localhost_proxy
    assert p.http_localhost_port == 88
    assert p.https_localhost_port == 443
    assert p.proxy_mode == "http_https_localhost"
    # Primary displayed localhost port favors the first loopback assignment in scheme order.
    assert p.localhost_port == 88


def test_parse_proxy_server_plain_loopback_host_port() -> None:
    p = parse_proxy_server("127.0.0.1:7777")
    assert p.is_localhost_proxy
    assert p.localhost_host == "127.0.0.1"
    assert p.localhost_port == 7777
    assert p.proxy_mode == "manual_localhost"


def test_proxy_change_audit_row_has_schema(tmp_path: Path) -> None:
    emit_proxy_change_detected_audit(
        tmp_path,
        diff={"changed": True, "risk_level": "medium"},
        attribution={"confidence": 0.2},
        decision={"action": "alert"},
    )
    lp = proxy_change_audit_jsonl_path(tmp_path)
    payload = json.loads(lp.read_text(encoding="utf-8").strip())
    assert payload["schema_version"] == "1"
    assert payload["event"] == "proxy_change_detected"
    sb = payload.get("safety_boundary") or {}
    assert sb.get("requires_confirmation_for_rollback") is True


def test_procmon_boost_nonzero(tmp_path: Path) -> None:
    csvp = tmp_path / "p.csv"
    csvp.write_text(
        "Time,PID,Process Name,Path,detail\n12:34,99,svc.exe,"
        '"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings"'
        ',test\n',
        encoding="utf-8",
    )
    boost, hits = confidence_boost_from_csv(csvp)
    assert boost > 0
    assert hits


def test_inventory_grace_on_powershell_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.proxy_guard.process_inventory import capture_process_inventory

    def boom_run(*a, **k):
        raise OSError("no powershell")

    inv = capture_process_inventory(proxy_localhost_port=None, run=boom_run)
    assert isinstance(inv["process_rows"], list)
    assert inv["process_rows"] == [] or isinstance(inv["process_rows"], list)

