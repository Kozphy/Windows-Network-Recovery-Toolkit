from __future__ import annotations

from typing import Any

from proxy_guard.port_process_attribution import _parse_netstat_listener_pids
from proxy_guard.proxy_risk_inference import infer_proxy_risk
from proxy_guard.proxy_signal_collector import parse_proxy_server


def _proxy(
    *,
    enabled: int,
    server: str | None,
    localhost: bool = False,
    port: int | None = None,
) -> dict[str, Any]:
    return {
        "proxy_enable": enabled,
        "proxy_server": server,
        "auto_config_url": None,
        "parsed_proxy": {
            "is_localhost_proxy": localhost,
            "localhost_port": port,
        },
        "limitations": [],
    }


def _attr(name: str | None, path: str | None, conf: str = "high", pid: int | None = 1234) -> dict[str, Any]:
    return {
        "port": 5000,
        "pid": pid,
        "process_name": name,
        "process_path": path,
        "parent_pid": 1,
        "attribution_confidence": conf,
        "limitations": [],
    }


def _persistence(text: str = "") -> dict[str, Any]:
    return {"startup_entries": text, "scheduled_tasks": [], "run_keys": {}, "persistence_entry_count": 1 if text else 0}


def _certs(suspicious: int = 0, recent: int = 0) -> dict[str, Any]:
    return {
        "suspicious_certificates": [{} for _ in range(suspicious)],
        "recent_root_additions": [{} for _ in range(recent)],
        "unknown_issuer_candidates": [],
    }


def test_no_proxy() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=0, server=None),
        attribution=_attr(None, None, conf="low", pid=None),
        persistence=_persistence(),
        certificates=_certs(),
    )
    assert out["classification"] == "NO_PROXY"
    assert out["risk_score"] == 0.0


def test_localhost_proxy_known_dev_process() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=1, server="127.0.0.1:8888", localhost=True, port=8888),
        attribution=_attr("node.exe", r"C:\Program Files\nodejs\node.exe", conf="high"),
        persistence=_persistence(),
        certificates=_certs(),
    )
    assert out["classification"] == "KNOWN_DEV_PROXY"
    assert out["risk_level"] == "low"
    assert out["confidence"] >= 0.7


def test_localhost_proxy_unknown_node_appdata_path() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=1, server="127.0.0.1:50347", localhost=True, port=50347),
        attribution=_attr("node.exe", r"C:\Users\me\AppData\Roaming\npm\node.exe", conf="medium"),
        persistence=_persistence(),
        certificates=_certs(),
    )
    assert out["classification"] == "SUSPICIOUS_PROXY"
    assert out["risk_score"] >= 0.65
    assert any("appdata" in r.lower() or "user-space" in r.lower() for r in out["reasons"])


def test_proxy_with_startup_persistence() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=1, server="127.0.0.1:60001", localhost=True, port=60001),
        attribution=_attr("evilproxy.exe", r"C:\Users\me\AppData\Local\Temp\evilproxy.exe", conf="medium"),
        persistence=_persistence(text="evilproxy.exe --autostart"),
        certificates=_certs(),
    )
    assert out["classification"] in {"SUSPICIOUS_PROXY", "POSSIBLE_MITM_RISK"}
    assert any("persistence" in r.lower() for r in out["reasons"])


def test_suspicious_certificate_plus_proxy() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=1, server="127.0.0.1:61000", localhost=True, port=61000),
        attribution=_attr("unknownproxy.exe", r"C:\Users\me\AppData\Local\Temp\unknownproxy.exe", conf="medium"),
        persistence=_persistence(),
        certificates=_certs(suspicious=1, recent=1),
    )
    assert out["classification"] == "POSSIBLE_MITM_RISK"
    assert out["risk_level"] in {"high", "critical"}


def test_unattributed_proxy_port() -> None:
    out = infer_proxy_risk(
        proxy_signals=_proxy(enabled=1, server="127.0.0.1:62000", localhost=True, port=62000),
        attribution=_attr(None, None, conf="low", pid=None),
        persistence=_persistence(),
        certificates=_certs(),
    )
    assert any("does not prove" in x.lower() for x in out["limitations"])
    assert out["confidence"] < 0.7


def test_proxy_server_parser_detects_ipv6_loopback() -> None:
    parsed = parse_proxy_server("http=[::1]:8080;https=localhost:8081")
    assert parsed["is_localhost_proxy"] is True
    assert parsed["localhost_host"] == "::1"
    assert parsed["localhost_port"] == 8080


def test_netstat_parser_matches_any_local_listener_address() -> None:
    output = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:50347          0.0.0.0:0              LISTENING       4242
  TCP    [::]:50347             [::]:0                 LISTENING       4242
"""
    assert _parse_netstat_listener_pids(output, 50347) == [4242]
