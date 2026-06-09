"""Stop localhost proxy listener preview."""

from __future__ import annotations

from typing import Any


def preview_stop_listener(*, pid: int | None = None, dry_run: bool = True) -> dict[str, Any]:
    from src.proxy_guard.remediation import get_remediation_action

    action = get_remediation_action("stop_proxy_listener")
    return {
        "action_id": action.action_id,
        "dry_run": dry_run,
        "target_pid": pid,
        "risk_level": action.risk_level,
        "required_confirmation": action.required_confirmation,
        "blocked_reason": action.blocked_reason,
        "reversible": action.reversible,
    }
