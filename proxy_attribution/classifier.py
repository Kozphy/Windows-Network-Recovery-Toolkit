"""Rule-based classification for proxy ownership (deterministic, auditable)."""

from __future__ import annotations

from typing import Any

# Lowercase tokens matched against process base name / image name.
VPN_CLIENT_TOKENS: tuple[str, ...] = (
    "clash",
    "v2ray",
    "v2rayn",
    "xray",
    "shadowsocks",
    "ss-win",
    "trojan",
    "sing-box",
    "hiddify",
    "nekoray",
    "mihomo",
)

SECURITY_TOKENS: tuple[str, ...] = (
    "avast",
    "kaspersky",
    "kes",
    "norton",
    "symantec",
    "mcafee",
    "eset",
    "bitdefender",
    "sophos",
    "defender",  # rarely binds explicit proxy; kept for completeness
)


def _norm_proc(name: str | None) -> str:
    if not name:
        return ""
    base = name.lower().strip()
    if base.endswith(".exe"):
        base = base[:-4]
    return base


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    return any(n in haystack for n in needles)


def classify_proxy_source(
    *,
    process_name: str | None,
    proxy_signal_active: bool,
    proxy_server: str | None,
    localhost_port_mapped: bool,
) -> tuple[str, float, str]:
    """Assign ``classification``, ``confidence`` in ``[0,1]``, and a one-line rationale.

    Categories:
        ``vpn_client``, ``security_software``, ``enterprise_policy``, ``unknown``.

    Rules (summary):
        - Known VPN-related process image → ``vpn_client``, high confidence.
        - Known security-suite image → ``security_software``, high confidence.
        - Proxy configured but no resolving localhost listener/process → ``enterprise_policy``, low confidence.
        - Otherwise → ``unknown``.
    """

    if not proxy_signal_active and not (proxy_server or "").strip():
        return (
            "unknown",
            0.08,
            "No WinINET proxy server string and no WinHTTP explicit-proxy signal was detected.",
        )

    pn = _norm_proc(process_name)

    if pn:
        if _contains_any(pn, VPN_CLIENT_TOKENS):
            return (
                "vpn_client",
                0.92,
                "Process name matches a common local VPN / tunnel client pattern.",
            )
        if _contains_any(pn, SECURITY_TOKENS):
            return (
                "security_software",
                0.9,
                "Process name matches a common security product pattern.",
            )
        return (
            "unknown",
            0.62,
            "A owning listener process was found but does not match known VPN/security heuristics.",
        )

    # No process attribution
    if proxy_signal_active and (proxy_server or "").strip():
        if not localhost_port_mapped:
            return (
                "enterprise_policy",
                0.35,
                "Proxy settings are present without a resolved local listener; policy or remote proxy is plausible.",
            )
        return (
            "enterprise_policy",
            0.38,
            "Localhost proxy port did not resolve to a listener; stale config or short-lived process is plausible.",
        )

    return (
        "unknown",
        0.25,
        "Insufficient evidence to attribute proxy configuration to a specific software class.",
    )


def recommended_action_and_risk(classification: str) -> tuple[str, str]:
    """Map classification to operator-facing strings (no automated execution)."""

    m: dict[str, tuple[str, str]] = {
        "vpn_client": ("disable_proxy", "low"),
        "security_software": ("review_security_proxy", "low"),
        "enterprise_policy": ("review_enterprise_proxy", "medium"),
        "unknown": ("review_manual_proxy", "medium"),
    }
    return m.get(classification, ("review_manual_proxy", "medium"))
