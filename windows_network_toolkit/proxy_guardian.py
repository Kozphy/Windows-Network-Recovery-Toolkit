"""Auto-remediate dead localhost WinINET proxy only (no listener on configured port).

Module responsibility:
    Scheduled guardian entry point: classify live proxy state and apply gated
    ``proxy-disable`` only when ``DEAD_PROXY_CONFIG`` is detected.

System placement:
    Invoked by ``cli.cmd_proxy_guardian`` and ``scripts/install-dead-proxy-guardian.ps1``.

Key invariants:
    * Never mutates registry when classification is not ``DEAD_PROXY_CONFIG``.
    * Never disables proxy when a localhost listener is still bound (active dev proxy).
    * Live apply reuses ``run_proxy_disable`` confirmation phrase for audit parity.

Side effects:
    * May append guardian and proxy-disable audit JSONL rows on apply.
"""

from __future__ import annotations

import platform
from typing import Any

from src.proxy_guard.remediation import CONFIRMATION_PHRASE
from windows_network_toolkit.diagnostics.proxy import run_proxy_status
from windows_network_toolkit.proxy_remediation import run_proxy_disable


def run_proxy_guardian_once(*, dry_run: bool = False) -> dict[str, Any]:
    """Check proxy state and clear dead localhost WinINET proxy when safe.

    Args:
        dry_run: When True, report intended action without registry mutation.

    Returns:
        JSON-serializable guardian result with ``action_taken`` and nested status.
    """
    if platform.system() != "Windows":
        return {
            "unsupported_platform": True,
            "platform": platform.system(),
            "action_taken": "none",
        }

    status = run_proxy_status()
    classification = str(status.get("classification") or "")
    result: dict[str, Any] = {
        "timestamp_utc": status.get("timestamp_utc"),
        "classification": classification,
        "localhost_port": status.get("localhost_port"),
        "action_taken": "none",
        "dry_run": dry_run,
    }

    if classification != "DEAD_PROXY_CONFIG":
        result["gate_reason"] = "classification_not_dead_proxy"
        result["reason"] = "No dead localhost proxy detected; guardian left settings unchanged."
        result["operator_next_steps"] = [
            "Run proxy-health and proxy-watch for path evidence before live remediation.",
            "If browsers fail but classification is NO_PROXY: see diagnostic_hints on proxy-status.",
        ]
        return result

    disable = run_proxy_disable(
        dry_run=dry_run,
        confirm=CONFIRMATION_PHRASE if not dry_run else "",
    )
    result["remediation"] = disable
    if disable.get("unsupported_platform"):
        result["action_taken"] = "blocked"
        result["gate_reason"] = "unsupported_platform"
        return result

    if dry_run:
        result["action_taken"] = "would_remediate"
        result["gate_reason"] = "dry_run_preview"
        result["reason"] = "Dead localhost proxy detected; dry-run preview only."
        result["operator_next_steps"] = [
            "Review remediation preview in remediation field.",
            "Live apply: proxy-disable --dry-run false --confirm DISABLE_WININET_PROXY",
        ]
        return result

    if disable.get("action_allowed"):
        result["action_taken"] = "remediated"
        result["gate_reason"] = "remediation_applied"
        result["reason"] = "Dead localhost proxy cleared with typed confirmation."
    else:
        result["action_taken"] = "blocked"
        result["gate_reason"] = disable.get("policy_reason") or "policy_or_confirmation_blocked"
        result["reason"] = disable.get("policy_reason") or "Remediation blocked by policy or confirmation."
        result["operator_next_steps"] = [
            "Run proxy-disable --dry-run true to inspect policy gate output.",
            "Ensure DISABLE_WININET_PROXY confirmation for live apply.",
        ]
    return result
