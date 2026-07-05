"""Auto-remediate dead localhost WinINET proxy only (no listener on configured port).

Delegates to ``src.proxy_drift.guardian`` while preserving legacy classification labels
for ``windows_network_toolkit`` consumers.
"""

from __future__ import annotations

import platform
from typing import Any

from src.proxy_drift.guardian import CONFIRM_CLEAR_DEAD
from src.proxy_drift.guardian import run_dead_proxy_guardian_once as _run_once
from src.proxy_guard.remediation import CONFIRMATION_PHRASE

_LEGACY_DEAD = frozenset({"STALE_LOCALHOST_PROXY", "STALE_PROXY_AFTER_PROCESS_EXIT"})


def _map_legacy(result: dict[str, Any]) -> dict[str, Any]:
    cls = str(result.get("classification") or "")
    if cls in _LEGACY_DEAD:
        result = dict(result)
        result["classification"] = "DEAD_PROXY_CONFIG"
    if result.get("dead_localhost_proxy") and result.get("action_taken") == "preview_only":
        result = dict(result)
        result["action_taken"] = "would_remediate"
    return result


def run_proxy_guardian_once(*, dry_run: bool = False) -> dict[str, Any]:
    """Check proxy state and clear dead localhost WinINET proxy when safe."""
    if platform.system() != "Windows":
        return {
            "unsupported_platform": True,
            "platform": platform.system(),
            "action_taken": "none",
        }

    confirm = CONFIRM_CLEAR_DEAD if not dry_run else ""
    result = _run_once(dry_run=dry_run, confirm=confirm)
    mapped = _map_legacy(result)

    if mapped.get("action_taken") == "remediated":
        mapped["reason"] = mapped.get("reason") or "Dead localhost proxy cleared automatically."
    elif mapped.get("dead_localhost_proxy") and dry_run:
        mapped["action_taken"] = "would_remediate"
        mapped["reason"] = "Dead localhost proxy detected; dry-run preview only."

    # Backward compat: nested remediation shape expected by some scripts
    if mapped.get("action_taken") == "remediated" and "remediation" not in mapped:
        mapped["remediation"] = {"action_allowed": True, "confirm": CONFIRMATION_PHRASE}

    return mapped
