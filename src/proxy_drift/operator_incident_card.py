"""Unified operator incident card — compose proxy, rewriter, path, and browser signals.

Module responsibility:
    Read-only merge of existing observation dicts into one envelope so operators do not
    false-clear on “proxy off” while IPv6/QUIC still stalls.

System placement:
    ``python -m src operator-incident`` (fixture-first; live gather on Windows only).

Key invariants:
    * No Windows mutation. Recommended commands are preview-first.
    * Source ``limitations[]`` are unioned, never dropped.
    * Confidence is ordinal, not statistical probability.
    * Classification is reliability triage — not malware or writer proof.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.platform_core.governance.evidence_to_action import attach_governance_envelope

SCHEMA = "operator_incident_card.v1"

_CARD_LIMITATIONS = [
    "Operator incident card is a compose of observations — not proof of root cause.",
    "Proxy healthy does not prove browser path healthy (false-clear risk).",
    "Rewriter match is correlation of persistence signals — not registry writer proof.",
    "Prefer-IPv4 and browser restart remain policy-gated; this card never applies them.",
    "Classification is not a malware verdict or EDR replacement.",
]

# Higher index = higher priority.
_PRIORITY: tuple[str, ...] = (
    "INSUFFICIENT_DATA",
    "HEALTHY",
    "PATH_OK",
    "NO_PROXY",
    "NO_PROXY_DIRECT_OK",
    "BOTH_DIRECT_AND_PROXY_WORK",
    "WININET_WINHTTP_MISMATCH",
    "IPV6_BROKEN_MITIGATED",
    "BROWSER_QUIC_STALL",
    "IPV6_PARTIAL_MITIGATION",
    "IPV6_BROKEN_IPV4_OK",
    "HAPPY_EYEBALLS_STALL",
    "PATH_UNREACHABLE",
    "LOCAL_PROXY_ACTIVE",
    "UNKNOWN_LOCAL_PROXY",
    "DEAD_PROXY_CONFIG",
    "STALE_LOCALHOST_PROXY",
    "STALE_PROXY_AFTER_PROCESS_EXIT",
    "BROKEN_LOCALHOST_PROXY",
    "REVERTER_SUSPECTED",
    "PROXY_FLAPPING",
    "LOCALHOST_REWRITER_SUSPECTED",
)

_PROXY_HIGH = frozenset(
    {
        "DEAD_PROXY_CONFIG",
        "STALE_LOCALHOST_PROXY",
        "STALE_PROXY_AFTER_PROCESS_EXIT",
        "BROKEN_LOCALHOST_PROXY",
        "REVERTER_SUSPECTED",
        "PROXY_FLAPPING",
        "UNKNOWN_LOCAL_PROXY",
        "DIRECT_ONLY_WORKS",
        "LISTENER_NOT_PROXY",
        "PROXY_FORWARDING_FAILED",
        "BOTH_DIRECT_AND_PROXY_FAIL",
        "PAC_CONFIGURED",
        "LOCAL_PROXY_ACTIVE",
        "KNOWN_DEV_PROXY",
        "KNOWN_VPN_PROXY",
        "PROXY_ENABLED_CHECK_GUARDIAN",
    }
)

_PATH_DEGRADED = frozenset(
    {
        "IPV6_BROKEN_IPV4_OK",
        "HAPPY_EYEBALLS_STALL",
        "IPV6_PARTIAL_MITIGATION",
        "PATH_UNREACHABLE",
    }
)

_NEXT_COMMAND: dict[str, str] = {
    "LOCALHOST_REWRITER_SUSPECTED": (
        "python -m src contain-localhost-rewriter --json"
    ),
    "DEAD_PROXY_CONFIG": "python -m src proxy-guardian --once --json",
    "STALE_LOCALHOST_PROXY": "python -m src proxy-guardian --once --json",
    "STALE_PROXY_AFTER_PROCESS_EXIT": "python -m src proxy-guardian --once --json",
    "BROKEN_LOCALHOST_PROXY": (
        "python -m src proxy-guardian --once --clear-broken --json"
    ),
    "REVERTER_SUSPECTED": "python -m src contain-localhost-rewriter --json",
    "PROXY_FLAPPING": "python -m src contain-localhost-rewriter --json",
    "UNKNOWN_LOCAL_PROXY": "python -m src proxy-guardian --once --json",
    "PROXY_ENABLED_CHECK_GUARDIAN": "python -m src proxy-guardian --once --json",
    "IPV6_BROKEN_IPV4_OK": "python -m src network-path-health --json",
    "IPV6_PARTIAL_MITIGATION": (
        "python -m src network-path-health --all-adapters --force --json"
    ),
    "HAPPY_EYEBALLS_STALL": "python -m src network-path-health --json",
    "BROWSER_QUIC_STALL": "python -m src fix-browser-stall --json",
    "IPV6_BROKEN_MITIGATED": "python -m src fix-browser-stall --json",
    "PATH_UNREACHABLE": "python -m src dns-health --json",
    "HEALTHY": "python -m src operator-incident --json",
    "PATH_OK": "python -m src operator-incident --json",
    "NO_PROXY_DIRECT_OK": "python -m src operator-incident --json",
    "INSUFFICIENT_DATA": (
        "python -m src operator-incident --fixture tests/fixtures/operator_incident/healthy.json"
    ),
}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rank(label: str) -> int:
    try:
        return _PRIORITY.index(label)
    except ValueError:
        return 0


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value if x]
    return []


def _label_from_proxy(proxy: dict[str, Any] | None) -> str | None:
    if not proxy:
        return None
    for key in ("classification", "incident_class", "legacy_classification"):
        raw = proxy.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            inner = raw.get("classification") or raw.get("incident_class")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return None


def _policy_for(primary: str) -> str:
    if primary in {
        "LOCALHOST_REWRITER_SUSPECTED",
        "REVERTER_SUSPECTED",
        "PROXY_FLAPPING",
        "UNKNOWN_LOCAL_PROXY",
    }:
        return "escalate"
    if primary in {
        "DEAD_PROXY_CONFIG",
        "STALE_LOCALHOST_PROXY",
        "STALE_PROXY_AFTER_PROCESS_EXIT",
        "BROKEN_LOCALHOST_PROXY",
        "IPV6_BROKEN_IPV4_OK",
        "IPV6_PARTIAL_MITIGATION",
        "HAPPY_EYEBALLS_STALL",
        "BROWSER_QUIC_STALL",
        "PATH_UNREACHABLE",
        "IPV6_BROKEN_MITIGATED",
        "PROXY_ENABLED_CHECK_GUARDIAN",
        "LOCAL_PROXY_ACTIVE",
        "DIRECT_ONLY_WORKS",
    }:
        return "preview"
    return "observe"


def _confidence_for(primary: str) -> float:
    if primary in {"INSUFFICIENT_DATA"}:
        return 0.2
    if primary in {"HEALTHY", "PATH_OK", "NO_PROXY_DIRECT_OK"}:
        return 0.8
    if primary in _PATH_DEGRADED or primary == "BROWSER_QUIC_STALL":
        return 0.75
    if primary in _PROXY_HIGH or primary == "LOCALHOST_REWRITER_SUSPECTED":
        return 0.82
    return 0.55


def _sli_hints(primary: str, contributing: list[str]) -> list[str]:
    hints: list[str] = []
    blob = {primary, *contributing}
    if blob & {
        "LOCALHOST_REWRITER_SUSPECTED",
        "DEAD_PROXY_CONFIG",
        "STALE_LOCALHOST_PROXY",
        "BROKEN_LOCALHOST_PROXY",
        "REVERTER_SUSPECTED",
        "PROXY_FLAPPING",
    }:
        hints.append("time_to_direct_after_rewrite")
    if (
        primary in _PATH_DEGRADED
        or primary == "BROWSER_QUIC_STALL"
        or "IPV6_BROKEN_IPV4_OK" in blob
        or "HAPPY_EYEBALLS_STALL" in blob
        or "BROWSER_QUIC_STALL" in blob
    ) and not (blob & _PROXY_HIGH):
        hints.append("false_clear_rate")
    if blob & {
        "IPV6_BROKEN_IPV4_OK",
        "HAPPY_EYEBALLS_STALL",
        "IPV6_PARTIAL_MITIGATION",
        "IPV6_BROKEN_MITIGATED",
        "PATH_OK",
    }:
        hints.append("dual_stack_path_success")
    hints.append("blocked_high_risk_actions")
    # Preserve order, unique
    seen: set[str] = set()
    out: list[str] = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


@dataclass
class OperatorIncidentCard:
    """Unified operator-facing incident envelope."""

    schema: str = SCHEMA
    timestamp_utc: str = ""
    primary_class: str = "INSUFFICIENT_DATA"
    contributing_classes: list[str] = field(default_factory=list)
    confidence: float = 0.2
    limitations: list[str] = field(default_factory=list)
    recommended_next_command: str = ""
    policy_action: str = "observe"
    sli_hints: list[str] = field(default_factory=list)
    sources: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compose_operator_incident_card(
    *,
    proxy: dict[str, Any] | None = None,
    rewriter: dict[str, Any] | None = None,
    path_health: dict[str, Any] | None = None,
    browser_stall: dict[str, Any] | None = None,
    timestamp_utc: str | None = None,
) -> dict[str, Any]:
    """Compose a read-only operator incident card from injected observation dicts.

    Args:
        proxy: Guardian / classify_proxy_drift / incident dict.
        rewriter: ``run_rewriter_containment`` detection or preview dict.
        path_health: ``assess_network_path`` / ``run_network_path_health`` dict.
        browser_stall: ``run_browser_stall_fix`` preview dict or stall class inject.
        timestamp_utc: Override; otherwise UTC now.

    Returns:
        Governance-enveloped dict with ``primary_class``, ``limitations[]``, preview command.

    Side effects:
        None.
    """
    limitations: list[str] = list(_CARD_LIMITATIONS)
    for src in (proxy, rewriter, path_health, browser_stall):
        if isinstance(src, dict):
            limitations.extend(_as_list(src.get("limitations")))
    # Unique preserve order
    seen_lim: set[str] = set()
    uniq_lim: list[str] = []
    for lim in limitations:
        if lim not in seen_lim:
            seen_lim.add(lim)
            uniq_lim.append(lim)

    candidates: list[str] = []
    proxy_label = _label_from_proxy(proxy)
    if proxy_label:
        candidates.append(proxy_label)

    rewriter_match = bool(rewriter and rewriter.get("match"))
    if rewriter_match:
        candidates.append("LOCALHOST_REWRITER_SUSPECTED")

    path_label = None
    if path_health:
        raw = path_health.get("classification")
        if isinstance(raw, str) and raw.strip():
            path_label = raw.strip()
            candidates.append(path_label)

    browser_label = None
    if browser_stall:
        raw_b = browser_stall.get("classification")
        if isinstance(raw_b, str) and raw_b.strip():
            browser_label = raw_b.strip()
            candidates.append(browser_label)
        elif path_label in {"HAPPY_EYEBALLS_STALL", "IPV6_BROKEN_MITIGATED"}:
            candidates.append("BROWSER_QUIC_STALL")
            browser_label = "BROWSER_QUIC_STALL"
        elif browser_stall.get("action_taken") in {"preview_only", "blocked"} and path_label in {
            "IPV6_BROKEN_IPV4_OK",
            "HAPPY_EYEBALLS_STALL",
            "IPV6_BROKEN_MITIGATED",
        }:
            candidates.append("BROWSER_QUIC_STALL")
            browser_label = "BROWSER_QUIC_STALL"

    if not candidates:
        primary = "INSUFFICIENT_DATA"
        uniq_lim.append("No proxy, rewriter, path-health, or browser-stall evidence supplied.")
    else:
        primary = max(candidates, key=_rank)

    contributing = sorted({c for c in candidates if c != primary})
    policy = _policy_for(primary)
    next_cmd = _NEXT_COMMAND.get(primary, "python -m src operator-incident --json")

    card = OperatorIncidentCard(
        schema=SCHEMA,
        timestamp_utc=timestamp_utc or _now(),
        primary_class=primary,
        contributing_classes=contributing,
        confidence=_confidence_for(primary),
        limitations=uniq_lim,
        recommended_next_command=next_cmd,
        policy_action=policy,
        sli_hints=_sli_hints(primary, contributing),
        sources={
            "proxy_class": proxy_label,
            "rewriter_match": rewriter_match,
            "path_class": path_label,
            "browser_class": browser_label,
        },
        dry_run=True,
    )
    payload = card.to_dict()
    return attach_governance_envelope(
        payload,
        primary_classification=primary,
        dry_run=True,
        requires_confirmation=policy != "observe",
        executed=False,
        limitations=uniq_lim,
    )


def load_operator_incident_fixture(path: Path) -> dict[str, Any]:
    """Load a fixture JSON for ``compose_operator_incident_card``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("operator incident fixture must be a JSON object")
    return compose_operator_incident_card(
        proxy=data.get("proxy") if isinstance(data.get("proxy"), dict) else None,
        rewriter=data.get("rewriter") if isinstance(data.get("rewriter"), dict) else None,
        path_health=data.get("path_health") if isinstance(data.get("path_health"), dict) else None,
        browser_stall=data.get("browser_stall") if isinstance(data.get("browser_stall"), dict) else None,
        timestamp_utc=str(data["timestamp_utc"]) if data.get("timestamp_utc") else None,
    )


def format_operator_incident_markdown(payload: dict[str, Any]) -> str:
    """Human-readable incident card (not an audit opinion)."""
    lines = [
        "# Operator incident card",
        "",
        f"- **primary_class:** `{payload.get('primary_class')}`",
        f"- **policy_action:** `{payload.get('policy_action')}` (preview-first; card does not apply)",
        f"- **confidence (ordinal):** {payload.get('confidence')}",
        f"- **recommended_next_command:** `{payload.get('recommended_next_command')}`",
        "",
        "## Contributing classes",
        "",
    ]
    contrib = payload.get("contributing_classes") or []
    if contrib:
        for c in contrib:
            lines.append(f"- `{c}`")
    else:
        lines.append("- (none)")
    lines.extend(["", "## SLI hints", ""])
    for h in payload.get("sli_hints") or []:
        lines.append(f"- `{h}`")
    lines.extend(["", "## Limitations", ""])
    for lim in payload.get("limitations") or []:
        lines.append(f"- {lim}")
    lines.extend(
        [
            "",
            "_Observation ≠ proof. This card is operator triage, not malware attribution._",
            "",
        ]
    )
    return "\n".join(lines)
