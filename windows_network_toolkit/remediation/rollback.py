"""Rollback preview facade."""

from __future__ import annotations

from typing import Any


def preview_rollback(*, snapshot_path: str | None = None, dry_run: bool = True) -> dict[str, Any]:
    from src.proxy_guard.remediation import get_remediation_action

    action = get_remediation_action("restore_wininet_proxy_from_lkg")
    return {
        "action_id": action.action_id,
        "dry_run": dry_run,
        "snapshot_path": snapshot_path,
        "risk_level": action.risk_level,
        "required_confirmation": action.required_confirmation,
        "reversible": action.reversible,
        "rollback_plan": "Restore HKCU WinINET fields from last-known-good snapshot.",
    }
