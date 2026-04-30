from __future__ import annotations

"""Safety policy and preview contract for repair actions.

This module defines the policy boundary between diagnosis and remediation.
It is consumed by CLI and API layers to enforce "preview first" behavior and to
prevent unauthorized or dangerous action categories.

Key invariants:
- Unknown actions are denied.
- Firewall reset actions are denied by policy.
- Allowed actions require explicit user confirmation in caller workflow.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairAction:
    """Describe a repair action and its safety classification.

    Attributes:
        action: Stable action identifier used across decision and API layers.
        preview_commands: Ordered shell commands shown/executed when approved.
        destructive: Whether the action can modify critical network state.
        firewall_reset: Whether action implies firewall reset (policy-forbidden).

    Interaction:
        Instances are stored in `REPAIR_PREVIEWS` and queried by `get_preview`.
    """

    action: str
    preview_commands: tuple[str, ...]
    destructive: bool = False
    firewall_reset: bool = False


REPAIR_PREVIEWS: dict[str, RepairAction] = {
    "flush_dns_cache": RepairAction(
        action="flush_dns_cache",
        preview_commands=("ipconfig /flushdns",),
    ),
    "reset_proxy_settings": RepairAction(
        action="reset_proxy_settings",
        preview_commands=(
            "netsh winhttp reset proxy",
            'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f',
        ),
    ),
    "renew_ip_and_check_gateway": RepairAction(
        action="renew_ip_and_check_gateway",
        preview_commands=("ipconfig /release", "ipconfig /renew"),
    ),
    "review_certificate_chain_and_ssl_inspection": RepairAction(
        action="review_certificate_chain_and_ssl_inspection",
        preview_commands=("certmgr.msc",),
    ),
    "review_firewall_rules_manually": RepairAction(
        action="review_firewall_rules_manually",
        preview_commands=("netsh advfirewall show allprofiles",),
    ),
    "winsock_reset_preview": RepairAction(
        action="winsock_reset_preview",
        preview_commands=("netsh winsock reset",),
        destructive=True,
    ),
}


def get_preview(action: str) -> dict[str, object]:
    """Resolve a repair action into a policy-validated preview payload.

    Decision intent:
        Provide a minimal, auditable contract for UI/API clients that must
        preview actions before execution.

    Output guarantees:
        - Returns a dict with `allowed` boolean.
        - For allowed actions, includes `requires_confirmation=True`.
        - For denied actions, includes machine-readable `reason`.

    Side effects:
        None. Pure lookup logic with deterministic output.

    Idempotency:
        Fully idempotent for the same `action` input.

    Known failure modes:
        - Stale action names from upstream decision engine return denial.
        - Misconfigured catalog entries can expose unexpected commands.

    Args:
        action: Action key requested by a caller (API/UI/CLI).

    Returns:
        dict[str, object]: Policy decision payload with command preview data.

    Raises:
        None.

    Example:
        >>> get_preview("flush_dns_cache")["allowed"]
        True
    """
    repair = REPAIR_PREVIEWS.get(action)
    if repair is None:
        return {"action": action, "allowed": False, "reason": "unknown_action"}
    if repair.firewall_reset:
        return {"action": action, "allowed": False, "reason": "firewall_reset_forbidden"}
    return {
        "action": action,
        "allowed": True,
        "requires_confirmation": True,
        "destructive": repair.destructive,
        "commands": list(repair.preview_commands),
    }
