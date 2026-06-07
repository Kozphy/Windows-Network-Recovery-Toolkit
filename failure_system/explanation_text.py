"""Plain-English explanations for UI and reports from structured diagnosis dicts.

Read-only string synthesis—no network or filesystem side effects.
"""

from __future__ import annotations

import re
from typing import Any


def _humanize_cause(cause: str) -> str:
    s = str(cause).strip()
    if not s:
        return "an undifferentiated issue"
    if "_" in s:
        return re.sub(r"_+", " ", s).strip().lower()
    return s


def _sentence_signals(signals: dict[str, Any]) -> str:
    """One sentence summarizing normalized probe signals."""

    if not signals:
        return "No structured connectivity signals were included in this explanation payload."

    # Prefer readable narrative when standard Failure Knowledge keys are present.
    if all(k in signals for k in ("ping_ip", "dns_lookup", "https_fetch")):
        pip = str(signals["ping_ip"])
        dns = str(signals["dns_lookup"])
        https = str(signals["https_fetch"])
        wd = signals.get("winhttp_direct")
        pl = signals.get("proxy_line")
        inter = signals.get("intermittent")
        parts = [
            f"IP-level ping is {pip}, DNS lookups are {dns}, and HTTPS fetch is {https}.",
        ]
        extra: list[str] = []
        if wd is not None:
            extra.append(
                f"WinHTTP appears {'direct' if str(wd).lower() in ('yes', 'true', '1') else 'non-direct'}"
            )
        if pl is not None:
            extra.append(
                f"a configured proxy line is {'present' if str(pl).lower() in ('yes', 'true', '1') else 'absent'}"
            )
        if extra:
            parts.append(" ".join(extra) + ".")
        if inter is not None and str(inter).lower() in ("yes", "true", "1"):
            parts.append("Intermittent behavior was flagged for this run.")
        return " ".join(parts)

    # Generic fallback: short comma-separated summary (sorted keys for stability).
    bits = []
    for key in sorted(signals.keys()):
        val = signals[key]
        if isinstance(val, bool):
            bits.append(f"{key.replace('_', ' ')}={'yes' if val else 'no'}")
        else:
            bits.append(f"{key.replace('_', ' ')}={val}")
    return "Observed signals: " + "; ".join(bits) + "."


def _sentence_attribution(attribution: dict[str, Any]) -> str:
    proc = str(attribution.get("owner_process") or "").strip()
    cls = str(attribution.get("classification") or "").strip()
    if proc and cls:
        return (
            f"Attribution suggests process {proc!r} with classification {_humanize_label(cls)!r}."
        )
    if proc:
        return f"Attribution points to process {proc!r}."
    if cls:
        return f"Attribution classification is {_humanize_label(cls)!r}."
    return "Process ownership and classification were not captured in this diagnostic pass."


def _humanize_label(cls: str) -> str:
    return re.sub(r"_+", " ", cls).strip()


def _sentence_decision(decision: dict[str, Any]) -> str:
    cause_raw = decision.get("cause")
    cause_h = _humanize_cause(str(cause_raw or "unknown"))

    try:
        conf = float(decision.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0

    risk = decision.get("risk_level")
    risk_part = ""
    if risk is not None and str(risk).strip():
        risk_part = f" The suggested manual action is rated {str(risk).strip()} risk."

    fix = decision.get("recommended_fix") or decision.get("fix") or ""
    fix = str(fix).strip()
    fix_part = ""
    if fix:
        fix_part = f" Recommended direction (confirm before changing anything): {fix}"

    return f"The primary hypothesis is {cause_h} (confidence {conf:.2f}).{risk_part}{fix_part}"


def generate_explanation_text(diag_result: dict[str, Any]) -> str:
    """Return a 2–3 sentence plain-English summary for UI or PDF/HTML reports.

    Args:
        diag_result: Same shape as ``generate_mermaid`` / ``diagnosis_from_failure_run`` output.

    Returns:
        Short paragraph (typically three sentences) with no markup.

    Raises:
        None; missing keys degrade to neutral placeholder phrases.
    """
    signals = diag_result.get("signals") if isinstance(diag_result.get("signals"), dict) else {}
    attribution = (
        diag_result.get("attribution") if isinstance(diag_result.get("attribution"), dict) else {}
    )
    decision = diag_result.get("decision") if isinstance(diag_result.get("decision"), dict) else {}

    s1 = _sentence_signals(signals or {})
    s2 = _sentence_attribution(attribution or {})
    s3 = _sentence_decision(decision or {})

    text = f"{s1} {s2} {s3}".strip()
    # Normalize whitespace; keep within a reasonable UI paragraph length.
    text = re.sub(r"\s+", " ", text)
    return text
