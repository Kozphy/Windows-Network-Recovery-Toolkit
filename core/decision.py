"""Deterministic hypothesis scoring: one place for probe → issue + confidence (+ evidence)."""

from __future__ import annotations

from typing import Literal

from .features import Features

Cause = Literal[
    "dns_issue",
    "proxy_issue",
    "winsock_issue",
    "firewall_issue",
    "network_adapter_issue",
    "isp_router_issue",
    "browser_only_issue",
]

ALL_CAUSES: tuple[Cause, ...] = (
    "dns_issue",
    "proxy_issue",
    "winsock_issue",
    "firewall_issue",
    "network_adapter_issue",
    "isp_router_issue",
    "browser_only_issue",
)

_CONNECTION_TW_SPIKE = 5000
_CONNECTION_EST_SPIKE = 8000


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def score(features: Features) -> dict[str, object]:
    """Return ranked scores and primary ``issue``, ``confidence``, ``reason``.

    Mirrors the prior ``src.decision_engine.scoring`` heuristic weights (explainable rules only).
    """
    deltas: dict[Cause, float] = {c: 0.06 for c in ALL_CAUSES}
    notes: dict[Cause, list[str]] = {c: [] for c in ALL_CAUSES}

    def bump(cause: Cause, amt: float, msg: str) -> None:
        deltas[cause] += amt
        notes[cause].append(msg)

    if (
        features["time_wait_count"] >= _CONNECTION_TW_SPIKE
        or features["established_count"] >= _CONNECTION_EST_SPIKE
    ):
        ratio = max(
            features["time_wait_count"] / max(_CONNECTION_TW_SPIKE, 1),
            features["established_count"] / max(_CONNECTION_EST_SPIKE, 1),
        )
        bump("isp_router_issue", _clamp(0.35 + 0.25 * ratio), "High TIME_WAIT / ESTABLISHED counts.")

    if not features["adapter_connected"]:
        bump("network_adapter_issue", 0.78, "No physical adapter reported Up.")

    if features["gateway_reachable"] is False:
        bump("isp_router_issue", 0.62, "Default gateway ping failed.")
    elif features["gateway_reachable"] is True and not features["ping_ip_ok"]:
        bump("isp_router_issue", 0.55, "Gateway OK but WAN ping failed.")

    if not features["ping_ip_ok"] and features["gateway_reachable"] is not False:
        bump("network_adapter_issue", 0.45, "ICMP to public resolver failed.")

    if features["ping_ip_ok"] and not features["nslookup_ok"]:
        bump("dns_issue", 0.78, "IP reachability OK while nslookup failed.")
        if features["ping_domain_ok"]:
            bump("dns_issue", 0.08, "Hostname ping succeeded with nslookup failure.")
    elif not features["ping_domain_ok"] and features["ping_ip_ok"]:
        bump("dns_issue", 0.55, "Hostname ping failed while numeric ICMP OK.")

    if features["dns_servers_detected"] == 0 and features["adapter_connected"]:
        bump("dns_issue", 0.35, "No DNS servers enumerated from ipconfig.")

    if features["proxy_enabled"] and not features["browser_http_ok"]:
        bump("proxy_issue", 0.74, "Proxy signals active and HTTPS curl failed.")
    elif features["proxy_enabled"]:
        bump("proxy_issue", 0.32, "Proxy configured while HTTPS succeeded.")

    if features["firewall_path_suspected"]:
        bump("firewall_issue", 0.52, "HTTPS failed without clear TLS cue or WinHTTP hints blocking.")
    elif features["tls_cert_issue_detected"]:
        bump("firewall_issue", 0.42, "TLS/cert keywords in curl output.")

    stacked = (
        int(not features["ping_ip_ok"])
        + int(not features["nslookup_ok"])
        + int(not features["tcp_443_ok"])
        + int(not features["browser_http_ok"])
    )
    if stacked >= 3:
        bump("winsock_issue", 0.6, "Several transports failed simultaneously.")
    elif not features["tcp_443_ok"] and features["ping_ip_ok"] and features["nslookup_ok"]:
        bump("winsock_issue", 0.38, "TCP/443 failed with ICMP/DNS OK.")

    if (
        features["ping_ip_ok"]
        and features["nslookup_ok"]
        and features["tcp_443_ok"]
        and features["browser_http_ok"]
        and not features["proxy_enabled"]
        and stacked == 0
    ):
        bump("browser_only_issue", 0.48, "All automated probes succeeded — symptom may be browser-only.")

    by_cause: dict[str, dict[str, object]] = {}
    for c in ALL_CAUSES:
        ev = tuple(notes[c]) if notes[c] else ("Baseline prior.",)
        by_cause[c] = {"cause": c, "confidence": _clamp(deltas[c]), "evidence": ev}

    ranked = sorted(by_cause.values(), key=lambda s: (-float(s["confidence"]), str(s["cause"])))

    primary_c = ranked[0]["cause"]
    primary_conf = float(ranked[0]["confidence"])
    ev_p = ranked[0]["evidence"]
    bits = (
        f"ping_ip={'ok' if features['ping_ip_ok'] else 'fail'}, "
        f"dns={'ok' if features['nslookup_ok'] else 'fail'}, "
        f"curl_https={'ok' if features['browser_http_ok'] else 'fail'}, "
        f"proxy={'on' if features['proxy_enabled'] else 'off'}"
    )

    reason: str
    if ev_p and ev_p != ("Baseline prior.",):
        top = "; ".join(ev_p[:3])
        reason = f"{str(primary_c).replace('_', ' ')} (confidence {primary_conf:.2f}): {top}. Signals: ({bits})."
    else:
        reason = (
            f"{str(primary_c).replace('_', ' ')} weak signal ({primary_conf:.2f}) — ({bits}); "
            "no strong rule fired."
        )

    return {
        "primary": {"issue": primary_c, "confidence": primary_conf, "reason": reason},
        "scores": ranked,
        "features_snapshot": bits,
    }

