from __future__ import annotations

from failure_system.layer_decision import decide_layer


def _base() -> dict[str, object]:
    return {
        "ping_ip_ok": True,
        "nslookup_ok": True,
        "tcp_443_ok": True,
        "curl_google_ok": True,
        "curl_ms_ok": True,
        "media_disconnected": False,
        "adapter_down": False,
        "gateway_present": True,
        "winhttp_direct": True,
        "wininet_proxy_enable": 0,
        "wininet_proxy_server": None,
        "is_localhost_proxy": False,
        "localhost_listener_found": None,
        "multi_device_failure_reported": False,
        "intermittent_snapshot": False,
        "recommended_next_test_hint": "next",
    }


def test_l1_l2_physical_failure() -> None:
    s = _base()
    s["media_disconnected"] = True
    r = decide_layer(s)
    assert r["layer"] == "L1_L2"


def test_l3_failure() -> None:
    s = _base()
    s["ping_ip_ok"] = False
    r = decide_layer(s)
    assert r["layer"] == "L3"


def test_l4_failure() -> None:
    s = _base()
    s["tcp_443_ok"] = False
    r = decide_layer(s)
    assert r["layer"] == "L4"


def test_l7_proxy_failure() -> None:
    s = _base()
    s["winhttp_direct"] = True
    s["wininet_proxy_enable"] = 1
    r = decide_layer(s)
    assert r["layer"] == "L7"
    assert r["failure_type"] == "browser_layer_proxy_drift"


def test_dns_only_failure() -> None:
    s = _base()
    s["nslookup_ok"] = False
    r = decide_layer(s)
    assert r["layer"] == "L7"
    assert r["failure_type"] == "dns_resolution_failure"


def test_winhttp_direct_but_wininet_proxy_enabled() -> None:
    s = _base()
    s["winhttp_direct"] = True
    s["wininet_proxy_enable"] = 1
    r = decide_layer(s)
    assert r["failure_type"] == "browser_layer_proxy_drift"


def test_localhost_proxy_listener_found() -> None:
    s = _base()
    s["is_localhost_proxy"] = True
    s["localhost_listener_found"] = True
    s["wininet_proxy_server"] = "127.0.0.1:8888"
    r = decide_layer(s)
    assert "Localhost proxy attribution is heuristic" in " ".join(r["attribution_notes"])


def test_localhost_proxy_listener_missing() -> None:
    s = _base()
    s["is_localhost_proxy"] = True
    s["localhost_listener_found"] = False
    s["wininet_proxy_server"] = "127.0.0.1:8888"
    r = decide_layer(s)
    assert r["confidence_score"] < 0.3 or r["layer"] == "L7"


def test_no_strong_failure_signature() -> None:
    r = decide_layer(_base())
    assert r["layer"] == "UNKNOWN"


def test_conflicting_signals() -> None:
    s = _base()
    s["tcp_443_ok"] = False
    s["nslookup_ok"] = False
    r = decide_layer(s)
    assert r["failure_type"] == "conflicting_signals"


def test_intermittent_failure_snapshot() -> None:
    s = _base()
    s["tcp_443_ok"] = False
    s["intermittent_snapshot"] = True
    r = decide_layer(s)
    assert r["confidence_score"] < 0.78

