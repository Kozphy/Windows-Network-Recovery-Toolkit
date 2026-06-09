"""In-memory session store for latest pipeline results (demo/API)."""

from __future__ import annotations

from typing import Any

_latest: dict[str, Any] = {}


def set_latest(result: Any) -> None:
    global _latest
    _latest = {
        "incident_id": result.bundle.incident_id,
        "timeline": result.timeline,
        "decision": result.decision.model_dump(),
        "policy": result.policy,
        "remediation": result.remediation,
        "audit": result.audit_record,
    }


def get_latest() -> dict[str, Any]:
    return dict(_latest)


def get_timeline() -> list[dict[str, Any]]:
    return list(_latest.get("timeline") or [])
