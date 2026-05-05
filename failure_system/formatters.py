"""Pure output formatters for ``failure_system`` diagnose payloads.

Module responsibility:
    Convert already-materialized diagnosis dictionaries into distinct output layers:
    decision summary (human), machine evidence (JSON via caller), communication (Markdown),
    and debugging (verbose evidence sections).

System placement:
    Called from ``failure_system.cli.cmd_diagnose`` after collection/rule/generation/storage have
    already completed. This module never invokes probes, persistence, or recommendation search.

Input assumptions:
    ``result`` matches the CLI payload shape with top-level keys such as ``failure_block``,
    ``rule_outcomes``, ``stored_path``, ``explanation_text``. Optional fields may be missing.

Output guarantees:
    Returns Unicode-safe strings only; callers choose stdout behavior.

Failure modes:
    Missing or malformed fields degrade to ``n/a`` placeholders instead of raising.

Audit Notes:
    Default human formatter intentionally suppresses raw command dumps to avoid terminal noise;
    use verbose mode or JSON for full evidence review.
"""

from __future__ import annotations

from typing import Any

_SEP = "────────────────────────────────────────"


def _title_case_risk(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return raw.capitalize() if raw else "Unknown"


def _fmt_conf(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value or "n/a")


def _status_from_signals(signals: list[str]) -> str:
    bad = [s for s in signals if "=fail" in s.lower() or "=error" in s.lower()]
    if bad:
        return "Degraded connectivity detected"
    return "Core connectivity OK"


def format_observed_signals(signals: list[str]) -> str:
    """Render observed ``key=value`` signal strings into aligned rows.

    Args:
        signals: Signal strings such as ``ping_ip=ok`` or ``proxy_line=no``.

    Returns:
        Multi-line human table-like block with icons and fixed-width keys.

    Constraints:
        Non ``key=value`` rows are preserved with an empty value column.
    """
    if not signals:
        return "(no observed signals recorded)"
    parsed: list[tuple[str, str]] = []
    for row in signals:
        if "=" in row:
            key, value = row.split("=", 1)
            parsed.append((key.strip(), value.strip()))
        else:
            parsed.append((str(row).strip(), ""))
    width = max(len(k) for k, _ in parsed) if parsed else 0
    lines: list[str] = []
    for k, v in parsed:
        icon = "✓" if v.lower() in {"ok", "yes", "true", "direct"} else "•"
        lines.append(f"{icon} {k:<{width}}   {v or '-'}")
    return "\n".join(lines)


def format_rule_outcomes(rule_outcomes: list[dict[str, Any]]) -> str:
    """Render a concise primary rule-outcome block.

    Args:
        rule_outcomes: Ordered rule dictionaries, typically from ``RuleEngine.evaluate``.

    Returns:
        Multi-line text block using the first outcome as primary explanation.
    """
    if not rule_outcomes:
        return "Rule        : n/a\nCause       : n/a\nConfidence  : n/a\nExplanation : n/a"
    top = rule_outcomes[0]
    return "\n".join(
        [
            f"Rule        : {top.get('rule_id', 'n/a')}",
            f"Cause       : {top.get('cause', 'n/a')}",
            f"Confidence  : {_fmt_conf(top.get('confidence'))}",
            f"Explanation : {top.get('explanation', 'n/a')}",
        ]
    )


def format_human_summary(result: dict[str, Any]) -> str:
    """Build the default CLI decision-layer output (no raw command dumps).

    Args:
        result: Diagnose payload dict assembled by ``failure_system.cli``.

    Returns:
        Readable summary with status, top hypothesis, signals, rule explanation, action, and safety.

    Side effects:
        None.
    """
    block = result.get("failure_block") or {}
    signals = block.get("observed_signals") or []
    lines = [
        "Diagnosis Summary",
        _SEP,
        f"Status              : {_status_from_signals(signals)}",
        f"Primary Hypothesis  : {block.get('name', 'n/a')}",
        f"Confidence          : {_fmt_conf(block.get('confidence_score'))}",
        f"Risk Level          : {_title_case_risk(block.get('risk_level'))}",
        f"Stored Path         : {result.get('stored_path', 'n/a')}",
        "",
        "Observed Signals",
        _SEP,
        format_observed_signals(signals),
        "",
        "Rule Outcome",
        _SEP,
        format_rule_outcomes(result.get("rule_outcomes") or []),
        "",
        "Recommended Action",
        _SEP,
        str(block.get("recommended_fix") or "n/a"),
        "",
        "Safety Boundary",
        _SEP,
        str(block.get("safety_boundary") or "n/a"),
    ]
    return "\n".join(lines)


def format_markdown_report(result: dict[str, Any]) -> str:
    """Render a Markdown communication report for issues/docs/runbooks.

    Args:
        result: Diagnose payload dict assembled by ``failure_system.cli``.

    Returns:
        Markdown string containing compact tables plus recommendation/safety sections.
    """
    block = result.get("failure_block") or {}
    signals = block.get("observed_signals") or []
    rule_outcomes = result.get("rule_outcomes") or []
    top = rule_outcomes[0] if rule_outcomes else {}

    signal_rows = []
    for row in signals:
        if "=" in row:
            k, v = row.split("=", 1)
            signal_rows.append(f"| {k.strip()} | {v.strip()} |")
        else:
            signal_rows.append(f"| {row} |  |")
    if not signal_rows:
        signal_rows.append("| n/a | n/a |")

    rule_rows = []
    for r in rule_outcomes[:10]:
        rule_rows.append(
            f"| {r.get('rule_id', 'n/a')} | {r.get('cause', 'n/a')} | {_fmt_conf(r.get('confidence'))} |"
        )
    if not rule_rows:
        rule_rows.append("| n/a | n/a | n/a |")

    return "\n".join(
        [
            "## Diagnosis Result",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Status | {_status_from_signals(signals)} |",
            f"| Primary Hypothesis | {block.get('name', 'n/a')} |",
            f"| Confidence | {_fmt_conf(block.get('confidence_score'))} |",
            f"| Risk Level | {_title_case_risk(block.get('risk_level'))} |",
            f"| Stored Log | `{result.get('stored_path', 'n/a')}` |",
            "",
            "### Observed Signals",
            "",
            "| Signal | Result |",
            "|---|---|",
            *signal_rows,
            "",
            "### Rule Outcomes",
            "",
            "| Rule | Cause | Confidence |",
            "|---|---|---|",
            *rule_rows,
            "",
            "### Recommended Action",
            "",
            str(block.get("recommended_fix") or "n/a"),
            "",
            "### Safety Boundary",
            "",
            str(block.get("safety_boundary") or "n/a"),
            "",
            "### Explanation Text",
            "",
            str(result.get("explanation_text") or top.get("explanation") or "n/a"),
        ]
    )


def format_verbose_report(result: dict[str, Any]) -> str:
    """Render summary plus raw evidence sections for deep debugging.

    Args:
        result: Diagnose payload dict assembled by ``failure_system.cli``.

    Returns:
        Human summary followed by raw diagnostic command outputs and provenance sections.
    """
    block = result.get("failure_block") or {}
    commands = block.get("diagnostic_commands") or {}
    source_logs = block.get("source_logs") or []
    parts = [format_human_summary(result), "", "Raw Evidence", _SEP]
    if commands:
        for name, text in commands.items():
            parts.extend(["", f"[{name}]", str(text or "")])
    else:
        parts.extend(["", "(no diagnostic_commands recorded)"])
    parts.extend(
        [
            "",
            "Source Logs",
            _SEP,
            "\n".join(f"- {x}" for x in source_logs) if source_logs else "(none)",
            "",
            "Explanation Text",
            _SEP,
            str(result.get("explanation_text") or "n/a"),
            "",
            "Rollback Plan",
            _SEP,
            str(block.get("rollback_plan") or "n/a"),
        ]
    )
    return "\n".join(parts)
