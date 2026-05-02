"""Safety boundaries and risk labeling for repair recommendations.

System placement:
    Imported exclusively by ``failure_system.generator`` when composing ``FailureBlock.risk_level``.

Constraints:
    Narrative scans look for destructive toolkit phrases (Winsock resets, firewall restores) to
    escalate severity—the list mirrors README caution language, not exhaustive OS coverage.
"""

from __future__ import annotations

from failure_system.models import RiskLevel

DEFAULT_SAFETY_BOUNDARY = (
    "This Failure Knowledge System runs read-only diagnostics only. "
    "Repairs (.bat scripts, netsh, registry edits, Winsock resets) never run automatically; "
    "operator must confirm each action out-of-band (CLI prompts, manual script execution)."
)


def escalate_if_destructive(description: str, base: RiskLevel) -> RiskLevel:
    """Return ``HIGH`` when ``description`` mentions destructive fixes; otherwise ``base``.

    Args:
        description: Recommended-fix prose assembled by ``generator._recommended_fix``.
        base: Tier derived from rule identifiers prior to textual escalation.

    Returns:
        Possibly escalated ``RiskLevel``.
    """
    lower = description.lower()
    destructive_markers = (
        "winsock",
        "tcp/ip stack",
        "netsh int ip reset",
        "firewall reset",
        "restore firewall",
    )
    if any(m in lower for m in destructive_markers):
        return RiskLevel.HIGH
    return base
