"""Safety constants and blocked-action registry.

Module responsibility:
    Centralize blocked destructive actions and default safety notes referenced by policy gates
    and remediation preview paths.

System placement:
    Imported by remediation and policy modules; documents non-negotiable toolkit boundaries.

Key invariants:
    * ``BLOCKED_ACTIONS`` includes process kill, firewall reset, adapter disable, WinHTTP modify.
    * Dry-run is the default posture for state-changing commands (enforced in callers).

Audit Notes:
    * Policy ALLOW does not imply safety — operators must still confirm typed tokens for apply.
"""

from __future__ import annotations

import os

BLOCKED_ACTIONS = frozenset(
    {
        "KILL_PROXY_PROCESS",
        "FIREWALL_RESET",
        "ADAPTER_DISABLE",
        "WINHTTP_MODIFY",
    }
)

CONFIRMATION_TOKENS = {
    "DISABLE_WININET_PROXY": "DISABLE_WININET_PROXY",
}

DEFAULT_SAFETY_NOTES = [
    "Observation is not proof; correlation is not causation.",
    "Dry-run is default for all state-changing commands.",
    "No silent process kill, firewall reset, adapter disable, or WinHTTP modification.",
    "Policy permission is not a safety guarantee.",
]

POLICY_DISCLAIMER = (
    "This toolkit provides evidence-based endpoint diagnosis — not antivirus or EDR replacement."
)


def safety_checks_for(action: str) -> list[str]:
    """Return safety check labels applied before evaluating an action.

    Args:
        action: Requested action identifier (e.g. ``KILL_PROXY_PROCESS``).

    Returns:
        List of check tokens; includes ``blocked_action:<name>`` when action is blocked.
    """
    checks = [
        "no_process_kill",
        "no_firewall_reset",
        "no_adapter_disable",
        "no_winhttp_modification_unless_explicit",
    ]
    if action in BLOCKED_ACTIONS:
        checks.append(f"blocked_action:{action}")
    return checks


def is_demo_mode() -> bool:
    """Return True when DEMO_MODE env enables reviewer demo safety gates."""
    return os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")


def is_blocked_action(action: str) -> bool:
    """Return whether an action is in the blocked destructive registry.

    Args:
        action: Action identifier (case-insensitive).

    Returns:
        True when action is in ``BLOCKED_ACTIONS`` or ``DEMO_MODE`` is active.

    Side effects:
        None.
    """
    if is_demo_mode():
        return True
    return action.upper() in BLOCKED_ACTIONS
