"""Translate diagnostic artefacts into persisted ``FailureBlock`` rows.

System placement:
    Consumed by CLI/API immediately after ``RuleEngine.evaluate`` succeeds.

Key invariants:
    - Primary FailureBlock mirrors the highest-confidence ``RuleOutcome`` after sorting.
    - ``created_at`` stamps UTC via ``datetime.now(timezone.utc)``.
    - ``diagnostic_commands`` copies truncated stdout strings from ``snapshot.raw``.

Side effects:
    None inside this module—callers persist outputs via ``storage.append_failure_block``.

Engineering Notes:
    Risk escalation relies on substring scans inside ``escalate_if_destructive`` to avoid labeling
    destructive manual fixes as LOW severity.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from failure_system.models import (
    DiagnosticSnapshot,
    FailureBlock,
    RiskLevel,
    RuleOutcome,
)
from failure_system.safety import DEFAULT_SAFETY_BOUNDARY, escalate_if_destructive


def _risk_for_rule(top: RuleOutcome | None) -> RiskLevel:
    """Map a primary rule id to a baseline risk tier before fix-text escalation."""
    if top is None:
        return RiskLevel.LOW
    rid = top.rule_id
    if rid == "ping_fail_path":
        return RiskLevel.LOW
    if rid == "dns_failure_likely":
        return RiskLevel.LOW
    if rid in ("https_path_failure", "proxy_misconfiguration"):
        return RiskLevel.MEDIUM
    if rid == "intermittent_instability":
        return RiskLevel.MEDIUM
    if rid == "baseline_ok":
        return RiskLevel.LOW
    return RiskLevel.MEDIUM


def _symptom_from_rules(snapshot: DiagnosticSnapshot, top: RuleOutcome | None) -> str:
    """Compose a short symptom sentence from probe booleans and top rule context."""
    if top is None:
        return "Network behavior unclear from current probes."
    parts: list[str] = []
    if not snapshot.ping_ip_ok:
        parts.append("Public IP ping fails.")
    elif not snapshot.nslookup_ok:
        parts.append("Ping OK but DNS lookup fails.")
    elif not snapshot.curl_https_ok:
        parts.append("Ping and DNS OK but HTTPS fetch fails.")
    elif snapshot.intermittent_reported:
        parts.append("Intermittent network symptoms reported.")
    else:
        parts.append("Core connectivity probes succeeded in this snapshot.")
    return " ".join(parts)


def _name_from_top(top: RuleOutcome | None) -> str:
    """Derive a compact FailureBlock title from the top rule cause."""
    if top is None:
        return "Undifferentiated network symptom"
    return top.cause[:120]


def _recommended_fix(top: RuleOutcome | None, snapshot: DiagnosticSnapshot) -> str:
    """Select conservative remediation guidance text for the primary rule."""
    if top is None:
        return (
            "Re-run diagnostics; consult toolkit scripts/README for targeted resets only after manual review."
        )
    if top.rule_id == "dns_failure_likely":
        return (
            "Safe first step: run `scripts/reset_dns.bat` or equivalent DNS flush after backing up context; "
            "verify DNS server settings in adapter properties."
        )
    if top.rule_id == "https_path_failure":
        return (
            "Review proxy settings (`scripts/proxy_status.bat`, WinHTTP show proxy); "
            "try `scripts/reset_proxy.bat` only after confirming proxy misalignment (guided confirmation)."
        )
    if top.rule_id == "proxy_misconfiguration":
        return (
            "Align WinINET/WinHTTP proxy with policy; use `scripts/reset_proxy.bat` with explicit confirmation "
            "if misconfiguration is confirmed."
        )
    if top.rule_id == "ping_fail_path":
        return (
            "Physical/link troubleshooting first; avoid stack resets until link-layer causes are ruled out."
        )
    if top.rule_id == "intermittent_instability":
        return (
            "Gather longitudinal snapshots; prefer driver/router fixes before broad stack resets."
        )
    return top.recommended_next_action


def _rollback(top: RuleOutcome | None) -> str:
    """Describe rollback expectations for the suggested guidance path."""
    if top and top.rule_id == "dns_failure_likely":
        return (
            "Note prior DNS server list; restore static DNS if changed; resolver cache repopulates automatically."
        )
    if top and top.rule_id in ("https_path_failure", "proxy_misconfiguration"):
        return (
            "Export current WinINET/WinHTTP proxy keys before edits; restore exported `.reg` snippet if needed."
        )
    if top and top.rule_id == "ping_fail_path":
        return (
            "Link-layer changes (cable swap, Wi-Fi reconnect) generally need no rollback; router reboot restores prior DHCP."
        )
    return "No automated state mutation was performed by this tool; rollback N/A for diagnostics-only run."


def _observed_signals(snapshot: DiagnosticSnapshot) -> list[str]:
    """Serialize booleans into stable ``key=value`` signal strings."""
    return [
        f"ping_ip={'ok' if snapshot.ping_ip_ok else 'fail'}",
        f"nslookup={'ok' if snapshot.nslookup_ok else 'fail'}",
        f"curl_https={'ok' if snapshot.curl_https_ok else 'fail'}",
        f"winhttp_direct={'yes' if snapshot.winhttp_direct else 'no'}",
        f"proxy_line={'yes' if snapshot.proxy_server_line_present else 'no'}",
        f"intermittent_reported={'yes' if snapshot.intermittent_reported else 'no'}",
    ]


def build_failure_block(
    snapshot: DiagnosticSnapshot,
    outcomes: list[RuleOutcome],
) -> FailureBlock:
    """Materialize a ``FailureBlock`` using the top sorted rule outcome.

    Args:
        snapshot: Raw probe outputs plus normalized booleans.
        outcomes: Rule outcomes from ``RuleEngine.evaluate`` (already sorted descending). When empty,
            the generator emits conservative fallback copy with low confidence.

    Returns:
        Fully populated ``FailureBlock`` ready for JSON serialization.

    Audit Notes:
        Verify ordering before persistence—unsorted inputs skew which hypothesis becomes primary text.
    """
    top = outcomes[0] if outcomes else None
    confidence = top.confidence if top else 0.25
    base_risk = _risk_for_rule(top)
    fix_text = _recommended_fix(top, snapshot)
    risk = escalate_if_destructive(fix_text, base_risk)

    likely = [o.cause for o in outcomes[:5]]
    explanations = [o.explanation for o in outcomes[:3]]

    diagnostic_commands = {
        k: v.stdout for k, v in snapshot.raw.items()
    }

    source_logs = [
        f"rules:{','.join(o.rule_id for o in outcomes[:6])}",
        *([f"explain:{explanations[0][:500]}"] if explanations else []),
    ]

    return FailureBlock(
        id=uuid4(),
        name=_name_from_top(top),
        symptom=_symptom_from_rules(snapshot, top),
        observed_signals=_observed_signals(snapshot),
        likely_causes=likely,
        diagnostic_commands=diagnostic_commands,
        confidence_score=confidence,
        recommended_fix=fix_text,
        risk_level=risk,
        safety_boundary=DEFAULT_SAFETY_BOUNDARY,
        rollback_plan=_rollback(top),
        created_at=datetime.now(timezone.utc),
        source_logs=source_logs,
    )
