"""Explainable Mermaid flowcharts from structured diagnosis payloads.

Read-only: transforms dict-shaped results into ``flowchart TD`` text. No subprocess or I/O
unless callers write or print the returned string.

Expected ``diag_result`` shape (all sections optional except meaningful content):

    {
        "signals": {"proxy_enabled": true, "https_fail": true, "tcp_ok": true},
        "attribution": {"owner_process": "app.exe", "classification": "vpn_client"},
        "decision": {
            "cause": "dead_local_proxy",
            "confidence": 0.91,
            "risk_level": "low",
            "recommended_fix": "Disable proxy",  # optional; aliases: fix
        },
    }

CLI adapters map ``FailureBlock`` / probe snapshots into this shape before calling
``generate_mermaid``.
"""

from __future__ import annotations

import re
from typing import Any

_MAX_LABEL = 52


def _short(text: str, max_len: int = _MAX_LABEL) -> str:
    t = " ".join(str(text).split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _humanize_snake(value: str) -> str:
    s = str(value).strip()
    if not s:
        return "—"
    return _short(re.sub(r"_+", " ", s).strip().title())


def _format_signals(signals: dict[str, Any]) -> list[tuple[str, str]]:
    """Return ordered (label, display_value) pairs for diagram nodes."""
    rows: list[tuple[str, str]] = []
    if not signals:
        return [("Signals", "No signal payload")]
    for key in sorted(signals.keys()):
        label = _humanize_snake(key.replace(".", " "))
        raw = signals[key]
        if isinstance(raw, bool):
            val = "Yes" if raw else "No"
        elif raw is None:
            val = "Unknown"
        else:
            val = _short(str(raw), 36)
        rows.append((label, val))
    return rows


def _next_ids(count: int) -> list[str]:
    """Alphanumeric node ids: A..Z, then N26.. (rare large graphs)."""

    out: list[str] = []
    for i in range(count):
        if i < 26:
            out.append(chr(ord("A") + i))
        else:
            out.append(f"N{i}")
    return out


def generate_mermaid(diag_result: dict[str, Any]) -> str:
    """Build a ``flowchart TD`` diagram string from a diagnosis dict.

    Layers (each concept is one node):

    - Entry: user / network request
    - Signal nodes: one per sorted signal key (label + value)
    - Attribution: process name + classification (placeholders if absent)
    - Decision: primary cause
    - Confidence (+ embedded risk in label when present)
    - Recommendation / fix text

    Args:
        diag_result: Payload with optional ``signals``, ``attribution``, ``decision`` keys.

    Returns:
        Mermaid source text with Unix newlines, ending with a newline.

    Raises:
        None by contract; malformed inputs degrade to placeholder labels.
    """
    signals = diag_result.get("signals") or {}
    attribution = diag_result.get("attribution") or {}
    decision = diag_result.get("decision") or {}

    signal_pairs = _format_signals(signals if isinstance(signals, dict) else {})

    proc_raw = str(attribution.get("owner_process") or "").strip()
    cls_raw = str(attribution.get("classification") or "").strip()
    proc_label = _short(f"Process: {proc_raw}") if proc_raw else "Process: Not captured"
    cls_label = (
        _short(f"Classification: {_humanize_snake(cls_raw)}")
        if cls_raw
        else "Classification: Not captured"
    )

    cause = decision.get("cause") if isinstance(decision, dict) else None
    if cause is None or str(cause).strip() == "":
        cause_txt = "Cause: Unknown"
    else:
        cause_txt = _short(f"Cause: {_humanize_snake(str(cause))}")

    try:
        conf_val = float(decision.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf_val = 0.0
    risk = decision.get("risk_level")
    risk_part = ""
    if risk is not None and str(risk).strip():
        risk_part = f" · Risk: {_short(str(risk).strip(), 16)}"
    conf_label = _short(f"Confidence: {conf_val:.2f}{risk_part}")

    fix = decision.get("recommended_fix") or decision.get("fix") or ""
    if str(fix).strip():
        fix_txt = _short(f"Fix: {str(fix).strip()}", max_len=56)
    else:
        fix_txt = "Fix: Review operator runbooks"

    # Build node list in flow order
    node_labels: list[str] = [_short("User / Network Request")]

    for lbl, val in signal_pairs:
        node_labels.append(_short(f"{lbl}: {val}"))

    node_labels.append(proc_label)
    node_labels.append(cls_label)
    node_labels.append(cause_txt)
    node_labels.append(conf_label)
    node_labels.append(fix_txt)

    ids = _next_ids(len(node_labels))
    lines = ["flowchart TD"]
    for i, nid in enumerate(ids):
        lines.append(f"{nid}[{_escape_bracket(node_labels[i])}]")
    for i in range(len(ids) - 1):
        lines.append(f"{ids[i]} --> {ids[i + 1]}")

    return "\n".join(lines) + "\n"


def _escape_bracket(text: str) -> str:
    """Escape characters that break Mermaid bracket labels."""

    return text.replace("[", "(").replace("]", ")").replace('"', "'")


def diagnosis_from_failure_run(
    *,
    snapshot_signals: dict[str, Any],
    owner_process: str | None,
    classification: str | None,
    cause: str,
    confidence: float,
    risk_level: str,
    recommended_fix: str,
) -> dict[str, Any]:
    """Normalize CLI/API failure-system artefacts into ``generate_mermaid`` input."""

    att: dict[str, Any] = {}
    if owner_process:
        att["owner_process"] = owner_process
    if classification:
        att["classification"] = classification

    return {
        "signals": snapshot_signals,
        "attribution": att,
        "decision": {
            "cause": cause,
            "confidence": confidence,
            "risk_level": risk_level,
            "recommended_fix": recommended_fix,
        },
    }


def snapshot_to_signal_dict(snapshot: Any) -> dict[str, Any]:
    """Map a ``DiagnosticSnapshot`` model into flat signal keys for diagrams."""

    return {
        "ping_ip": "OK" if snapshot.ping_ip_ok else "Fail",
        "dns_lookup": "OK" if snapshot.nslookup_ok else "Fail",
        "https_fetch": "OK" if snapshot.curl_https_ok else "Fail",
        "winhttp_direct": "Yes" if snapshot.winhttp_direct else "No",
        "proxy_line": "Yes" if snapshot.proxy_server_line_present else "No",
        "intermittent": "Yes" if getattr(snapshot, "intermittent_reported", False) else "No",
    }
