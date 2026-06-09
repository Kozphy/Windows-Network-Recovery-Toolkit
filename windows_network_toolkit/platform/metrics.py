"""Platform metrics facade."""

from __future__ import annotations

from typing import Any


def compute_erp_metrics() -> dict[str, Any]:
    try:
        from platform_core.metrics import compute_platform_metrics

        base = compute_platform_metrics()
    except Exception:  # noqa: BLE001
        base = {}
    return {
        "service": "endpoint-reliability-decision-platform",
        "platform_metrics": base,
        "dry_run_default": True,
    }
