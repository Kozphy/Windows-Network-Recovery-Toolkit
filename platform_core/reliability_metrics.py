"""Compute reliability metrics from append-only JSONL fixtures."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from platform_core.slo_model import ReliabilityMetrics
from platform_core.storage import iter_jsonl, platform_data_dir


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    text = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _signals_path(root: Path | None) -> Path:
    base = root if root is not None else platform_data_dir()
    return base / "platform_signals.jsonl"


def compute_reliability_metrics(*, data_root: Path | None = None) -> ReliabilityMetrics:
    """Derive portfolio reliability KPIs from local JSONL streams."""
    signals_path = _signals_path(data_root)
    browser_ok = 0
    browser_total = 0
    proxy_drift = 0
    false_positive = 0
    fp_denominator = 0
    recover_deltas: list[float] = []
    detect_deltas: list[float] = []
    stickiness_success = 0
    stickiness_total = 0

    for row in iter_jsonl(signals_path):
        kind = str(row.get("kind") or row.get("signal") or "")
        if kind in ("browser_path_ok", "browser_https_ok"):
            browser_ok += 1
            browser_total += 1
        elif kind in ("browser_path_failed", "browser_https_failed"):
            browser_total += 1
        elif kind in ("proxy_registry_change", "proxy_change", "proxy_enable_transition"):
            proxy_drift += 1
        elif kind == "incident_false_positive":
            false_positive += 1
            fp_denominator += 1
        elif kind == "incident_opened":
            fp_denominator += 1
        elif kind == "remediation_stickiness_ok":
            stickiness_success += 1
            stickiness_total += 1
        elif kind == "remediation_stickiness_failed":
            stickiness_total += 1

        detected_at = _parse_iso(row.get("detected_at"))
        occurred_at = _parse_iso(row.get("occurred_at"))
        recovered_at = _parse_iso(row.get("recovered_at"))
        if detected_at and occurred_at:
            detect_deltas.append(max(0.0, (detected_at - occurred_at).total_seconds()))
        if recovered_at and detected_at:
            recover_deltas.append(max(0.0, (recovered_at - detected_at).total_seconds()))

    browser_rate = (browser_ok / browser_total) if browser_total else 0.0
    fp_rate = (false_positive / fp_denominator) if fp_denominator else 0.0
    stickiness = (stickiness_success / stickiness_total) if stickiness_total else 0.0

    return ReliabilityMetrics(
        browser_path_success_rate=round(browser_rate, 4),
        proxy_drift_events_per_day=float(proxy_drift),
        mean_time_to_detect_seconds=(
            round(sum(detect_deltas) / len(detect_deltas), 2) if detect_deltas else None
        ),
        mean_time_to_recover_seconds=(
            round(sum(recover_deltas) / len(recover_deltas), 2) if recover_deltas else None
        ),
        remediation_stickiness_rate=round(stickiness, 4),
        false_positive_rate=round(fp_rate, 4),
    )


def reliability_metrics_dict(*, data_root: Path | None = None) -> dict[str, Any]:
    return compute_reliability_metrics(data_root=data_root).model_dump(mode="json")
