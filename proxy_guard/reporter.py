"""Proxy guard reporting helpers (text, JSON, append-only audit).

Module responsibility:
    Normalize final scan output for operator-readable text, machine-readable JSON, and append-only
    JSONL audit persistence.

System placement:
    Final emission layer called by :mod:`proxy_guard.main` after observations and inference finish.

Key invariants:
    - Timestamp is timezone-aware UTC.
    - JSON report preserves full payload shape (raw signals + inference context).
    - Audit writes append one line per event (no file rewrites).

Audit Notes:
    Audit rows may include sensitive host metadata from persistence/certificate collectors.
    Review and redact before external sharing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    """Return timezone-aware UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def build_report_payload(
    *,
    raw_signals: dict[str, Any],
    attribution: dict[str, Any],
    persistence: dict[str, Any],
    certificates: dict[str, Any],
    risk: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical report payload for CLI and JSONL sinks.

    Args:
        raw_signals: Raw proxy/registry observations.
        attribution: Port-to-process attribution details.
        persistence: Startup/task/run-key preview outputs.
        certificates: Root-certificate indicator outputs.
        risk: Inference payload from risk scoring layer.

    Returns:
        dict[str, Any]: Canonical report envelope with stable top-level keys.
    """
    return {
        "timestamp": _now_iso(),
        "raw_signals": raw_signals,
        "attribution": attribution,
        "persistence_indicators": persistence,
        "certificate_indicators": certificates,
        "inferred_classification": risk.get("classification"),
        "risk_score": risk.get("risk_score"),
        "risk_level": risk.get("risk_level"),
        "confidence": risk.get("confidence"),
        "limitations": risk.get("limitations", []),
        "recommended_next_steps": risk.get("recommended_actions", []),
        "inference": risk,
    }


def format_text_report(payload: dict[str, Any]) -> str:
    """Format concise explainable text report for terminal output."""
    inf = payload.get("inference") or {}
    lines = [
        "Proxy Hijack & MITM Risk Detection",
        "----------------------------------",
        f"timestamp: {payload.get('timestamp')}",
        f"classification: {inf.get('classification')}",
        f"risk_score: {inf.get('risk_score')} ({inf.get('risk_level')})",
        f"confidence: {inf.get('confidence')}",
        "",
        "reasons:",
    ]
    for r in inf.get("reasons", []):
        lines.append(f"- {r}")
    lines.extend(["", "limitations:"])
    for r in inf.get("limitations", []):
        lines.append(f"- {r}")
    lines.extend(["", "recommended_actions:"])
    for r in inf.get("recommended_actions", []):
        lines.append(f"- {r}")
    evidence = inf.get("evidence") or {}
    if evidence.get("validations"):
        lines.extend(["", "recommended_validation:"])
        for item in evidence.get("validations", []):
            lines.append(f"- {item}")
    return "\n".join(lines)


def format_json_report(payload: dict[str, Any]) -> str:
    """Serialize report payload as pretty JSON."""
    return json.dumps(payload, indent=2, ensure_ascii=True)


def append_audit_event(payload: dict[str, Any], *, audit_path: Path | None = None) -> Path:
    """Append one report payload to the JSONL audit ledger.

    Args:
        payload: Full report payload from :func:`build_report_payload`.
        audit_path: Optional override path for tests or alternate sinks.

    Returns:
        Path: Resolved audit file path.

    Side effects:
        Creates parent directory when missing and appends one JSON line.

    Idempotency:
        Not idempotent by design; each call writes a new event row.
    """
    path = audit_path or (Path(__file__).resolve().parent.parent / "logs" / "proxy_hijack_audit.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path

