from __future__ import annotations

"""Deterministic rule engine for network issue diagnosis.

This module is the decision core of the hybrid agent pipeline:
collectors -> decision engine -> report writer -> API/UI serving.
It converts normalized collector snapshots into ranked issue hypotheses with
explainable evidence and bounded confidence values.

Key invariants:
- Output is deterministic for identical snapshot input.
- Confidence values are bounded to [0.0, 1.0] and rounded for presentation.
- Returned issues use canonical names from `network_agent.engine.rules`.
- No external side effects (no file writes, no network calls).
"""

from .confidence import score
from .rules import (
    ALL_ISSUES,
    ISSUE_DNS_FAILURE,
    ISSUE_FIREWALL_BLOCK,
    ISSUE_HTTPS_CERT,
    ISSUE_PROXY_MISCONFIG,
    ISSUE_TCP_CONNECTIVITY,
    ISSUE_WINSOCK_CORRUPTION,
    RECOMMENDED_ACTIONS,
)


def _item(issue: str, confidence: float, evidence: list[str]) -> dict[str, object]:
    """Build a normalized diagnosis row for API/report consumers.

    Args:
        issue: Canonical issue key defined in `rules.py`.
        confidence: Raw confidence score before display rounding.
        evidence: Human-readable evidence statements supporting the decision.

    Returns:
        dict[str, object]: A diagnosis item containing issue key, rounded
        confidence, evidence list, and mapped recommended action.

    Raises:
        KeyError: If `issue` is not present in `RECOMMENDED_ACTIONS`.

    Example:
        >>> _item("DNS_FAILURE", 0.876, ["ping works", "nslookup fails"])
        {'issue': 'DNS_FAILURE', 'confidence': 0.88, ...}
    """
    return {
        "issue": issue,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "recommended_action": RECOMMENDED_ACTIONS[issue],
    }


def diagnose(snapshot: dict[str, object]) -> dict[str, object]:
    """Infer likely root causes from a collector snapshot.

    Decision intent:
        Provide an explainable, production-safe diagnosis without opaque model
        inference. This exists to support beginner-friendly remediation while
        preserving auditable logic.

    Input assumptions:
        - `snapshot` contains optional sections: `dns`, `proxy`, `tcp`,
          `https`, and `firewall`.
        - Section values are dict-like and may have missing keys.
        - Missing or malformed values are treated conservatively by relying on
          default `{}` and explicit `is True`/`is False` checks.

    Output guarantees:
        - Always returns a dict with keys `diagnosis` and `observed_issues`.
        - `diagnosis` is sorted by descending confidence.
        - If no issue exceeds threshold, returns a single fallback diagnosis
          with issue `NO_CLEAR_ISSUE`.
        - `observed_issues` contains only canonical issue keys.

    Side effects:
        None. This function is pure and idempotent.

    Constraints and limitations:
        - Rule thresholds and weights are heuristic and manually tuned.
        - Evidence quality depends on collector signal quality.
        - Not a replacement for deep packet inspection or enterprise telemetry.

    Known failure modes:
        - Concurrent failures can produce multiple close confidence values.
        - Incomplete snapshots may under-report true root cause confidence.
        - System-specific networking quirks can resemble proxy/firewall issues.

    Args:
        snapshot: Aggregated collector payload keyed by subsystem.

    Returns:
        dict[str, object]: Ranked diagnosis list and canonical observed issue
        keys suitable for report serialization and API responses.

    Raises:
        KeyError: If issue constants and action mapping become inconsistent.
        TypeError: If callers pass non-mapping snapshot structures.

    Example:
        >>> diagnose({"dns": {"ping_ip_ok": True, "nslookup_ok": False}})
        {'diagnosis': [...], 'observed_issues': ['DNS_FAILURE']}
    """
    dns = snapshot.get("dns", {})
    proxy = snapshot.get("proxy", {})
    tcp = snapshot.get("tcp", {})
    https = snapshot.get("https", {})
    firewall = snapshot.get("firewall", {})

    diagnosis: list[dict[str, object]] = []

    dns_evidence: list[str] = []
    dns_boosts: list[float] = []
    if dns.get("ping_ip_ok") is True:
        dns_evidence.append("ping 8.8.8.8 works")
        dns_boosts.append(0.25)
    if dns.get("nslookup_ok") is False:
        dns_evidence.append("nslookup google.com fails")
        dns_boosts.append(0.45)
    if dns.get("ping_domain_ok") is False and dns.get("ping_ip_ok") is True:
        dns_evidence.append("ping by domain fails while ping by IP works")
        dns_boosts.append(0.15)
    dns_conf = score(0.05, dns_boosts, [])
    if dns_conf >= 0.35:
        diagnosis.append(_item(ISSUE_DNS_FAILURE, dns_conf, dns_evidence))

    proxy_evidence: list[str] = []
    proxy_boosts: list[float] = []
    if proxy.get("proxy_enabled") is True:
        proxy_evidence.append("proxy configuration is enabled")
        proxy_boosts.append(0.45)
    if proxy.get("winhttp_proxy_enabled") is True:
        proxy_evidence.append("WinHTTP proxy is enabled")
        proxy_boosts.append(0.18)
    if https.get("https_ok") is False:
        proxy_evidence.append("HTTPS probe fails while proxy is active")
        proxy_boosts.append(0.2)
    proxy_conf = score(0.05, proxy_boosts, [])
    if proxy_conf >= 0.35:
        diagnosis.append(_item(ISSUE_PROXY_MISCONFIG, proxy_conf, proxy_evidence))

    tcp_evidence: list[str] = []
    tcp_boosts: list[float] = []
    if dns.get("ping_ip_ok") is True:
        tcp_evidence.append("basic ICMP connectivity works")
        tcp_boosts.append(0.1)
    if tcp.get("tcp_443_ok") is False:
        tcp_evidence.append("TCP 443 connection test fails")
        tcp_boosts.append(0.55)
    if https.get("https_ok") is False and dns.get("nslookup_ok") is True:
        tcp_evidence.append("HTTPS fails despite DNS lookup success")
        tcp_boosts.append(0.15)
    tcp_conf = score(0.05, tcp_boosts, [])
    if tcp_conf >= 0.35:
        diagnosis.append(_item(ISSUE_TCP_CONNECTIVITY, tcp_conf, tcp_evidence))

    cert_evidence: list[str] = []
    cert_boosts: list[float] = []
    if https.get("cert_issue_detected") is True:
        cert_evidence.append("TLS/certificate errors detected in HTTPS output")
        cert_boosts.append(0.65)
    if https.get("https_ok") is False and tcp.get("tcp_443_ok") is True:
        cert_evidence.append("TCP 443 works but HTTPS fails")
        cert_boosts.append(0.2)
    cert_conf = score(0.05, cert_boosts, [])
    if cert_conf >= 0.35:
        diagnosis.append(_item(ISSUE_HTTPS_CERT, cert_conf, cert_evidence))

    fw_evidence: list[str] = []
    fw_boosts: list[float] = []
    if firewall.get("firewall_profiles_enabled", 0) >= 1:
        fw_evidence.append("Windows Firewall profiles are enabled")
        fw_boosts.append(0.1)
    if tcp.get("tcp_443_ok") is True and https.get("https_ok") is False:
        fw_evidence.append("TCP is reachable but HTTPS fails")
        fw_boosts.append(0.28)
    if proxy.get("proxy_enabled") is False and dns.get("nslookup_ok") is True and https.get("https_ok") is False:
        fw_evidence.append("DNS is healthy and no proxy active but HTTPS still fails")
        fw_boosts.append(0.22)
    fw_conf = score(0.05, fw_boosts, [])
    if fw_conf >= 0.35:
        diagnosis.append(_item(ISSUE_FIREWALL_BLOCK, fw_conf, fw_evidence))

    ws_evidence: list[str] = []
    ws_boosts: list[float] = []
    failures = sum(
        1
        for ok in (
            dns.get("ping_ip_ok"),
            dns.get("nslookup_ok"),
            tcp.get("tcp_443_ok"),
            https.get("https_ok"),
        )
        if ok is False
    )
    if failures >= 3:
        ws_evidence.append("multiple transport layers fail simultaneously")
        ws_boosts.append(0.62)
    if dns.get("ping_ip_ok") is True and dns.get("nslookup_ok") is False and tcp.get("tcp_443_ok") is False:
        ws_evidence.append("mixed low-level success with upper stack failures")
        ws_boosts.append(0.12)
    ws_conf = score(0.05, ws_boosts, [])
    if ws_conf >= 0.35:
        diagnosis.append(_item(ISSUE_WINSOCK_CORRUPTION, ws_conf, ws_evidence))

    diagnosis.sort(key=lambda d: float(d["confidence"]), reverse=True)
    if not diagnosis:
        diagnosis = [
            {
                "issue": "NO_CLEAR_ISSUE",
                "confidence": 0.2,
                "evidence": ["No hypothesis passed threshold"],
                "recommended_action": "re-run_diagnosis_and_collect_more_signals",
            }
        ]

    return {
        "diagnosis": diagnosis,
        "observed_issues": [item["issue"] for item in diagnosis if item["issue"] in ALL_ISSUES],
    }
