"""Map primary issue → suggested fixes (paths only — never executed here)."""

from __future__ import annotations

from typing import TypedDict


class ActionHint(TypedDict):
    title: str
    detail: str
    script: str | None
    risk: str


def suggestions(issue: str, features: dict[str, object]) -> tuple[ActionHint, ...]:
    """Return ordered human suggestions; safest script-backed rows first."""

    tw = int(features.get("time_wait_count", 0))
    est = int(features.get("established_count", 0))

    diag_auto = ActionHint(
        title="Structured diagnosis",
        detail="Capture another snapshot after any change.",
        script=r"scripts\auto_diagnose.bat",
        risk="LOW",
    )
    dns_fix = ActionHint(
        title="Flush DNS resolver",
        detail="Clears stale cache; script is low-impact.",
        script=r"scripts\reset_dns.bat",
        risk="LOW",
    )
    proxy_fix = ActionHint(
        title="Clear user/WinHTTP proxy settings",
        detail="Stale manual proxies are a common root cause.",
        script=r"scripts\reset_proxy.bat",
        risk="LOW",
    )
    doc_only = ActionHint(
        title="Document symptom scope",
        detail="Confirm whether every app fails vs browser-only.",
        script=None,
        risk="LOW",
    )

    if issue == "dns_issue":
        return (diag_auto, dns_fix, doc_only)

    if issue == "proxy_issue":
        return (diag_auto, proxy_fix, doc_only)

    if issue == "firewall_issue":
        return (
            doc_only,
            ActionHint(
                title="Firewall review",
                detail="Inspect Defender/advanced firewall; reset only with explicit ops approval.",
                script=None,
                risk="LOW",
            ),
            ActionHint(
                title="Optional check script",
                detail="Read-oriented connectivity checks.",
                script=r"scripts\check_network.bat",
                risk="LOW",
            ),
            ActionHint(
                title="Reset firewall defaults (HIGH risk)",
                detail="Only run interactively via batch when you intend rule wipe.",
                script=r"scripts\reset_firewall.bat",
                risk="HIGH",
            ),
        )

    if issue == "network_adapter_issue":
        return (
            doc_only,
            ActionHint(
                title="Physical link triage",
                detail="Cable/Wi-Fi/VPN/airplane toggle before stack repair.",
                script=None,
                risk="LOW",
            ),
            ActionHint(
                title="Guided repair (destructive-ish)",
                detail="Runs broad stack repairs — confirm before running batch.",
                script=r"scripts\one_click_fix.bat",
                risk="MEDIUM",
            ),
        )

    if issue == "isp_router_issue":
        base = (
            doc_only,
            ActionHint(
                title="CPE restart / alternate path",
                detail="Power-cycle router; try hotspot to isolate ISP.",
                script=None,
                risk="LOW",
            ),
        )
        if tw >= 5000 or est >= 8000:
            return base + (
                ActionHint(
                    title="Socket exhaustion check",
                    detail="Read-only BAT for leak hints.",
                    script=r"scripts\check_connection_exhaustion.bat",
                    risk="LOW",
                ),
            )
        return base

    if issue == "winsock_issue":
        return (
            doc_only,
            ActionHint(
                title="Read-only network check",
                detail="Narrows Winsock/stack symptoms.",
                script=r"scripts\check_network.bat",
                risk="LOW",
            ),
            ActionHint(
                title="Guided Winsock/TCP/IP reset",
                detail="Potentially disruptive; run batch manually with awareness.",
                script=r"scripts\one_click_fix.bat",
                risk="MEDIUM",
            ),
        )

    if issue == "browser_only_issue":
        return (
            doc_only,
            ActionHint(
                title="Isolate browser/profile",
                detail="InPrivate, alternate profile/engine.",
                script=None,
                risk="LOW",
            ),
            ActionHint(
                title="Connection hygiene scan",
                detail="BAT read-only exhaustion hints.",
                script=r"scripts\check_connection_exhaustion.bat",
                risk="LOW",
            ),
        )

    return (
        diag_auto,
        ActionHint(
            title="Guided remediation",
            detail="Mixed evidence — escalate via auto_fix.bat only after manual review.",
            script=r"scripts\auto_fix.bat",
            risk="MEDIUM",
        ),
    )

