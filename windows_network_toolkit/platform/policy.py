"""Policy evaluation facade."""

from __future__ import annotations

from windows_network_toolkit.models import ClassificationResult, PolicyDecision, ProofResult
from windows_network_toolkit.safety import CONFIRMATION_TOKENS, is_blocked_action, safety_checks_for


def evaluate_policy(
    action: str,
    classification: ClassificationResult,
    proof: ProofResult | None = None,
    *,
    dry_run: bool = True,
    confirmation: str = "",
) -> PolicyDecision:
    action_upper = action.upper()

    if is_blocked_action(action_upper):
        return PolicyDecision(
            action=action_upper,
            allowed=False,
            requires_confirmation=True,
            confirmation_token="",
            risk_level="high",
            rationale=f"Action {action_upper} is blocked by safety policy.",
            safety_checks=safety_checks_for(action_upper),
        )

    token = CONFIRMATION_TOKENS.get(action_upper, action_upper)
    primary = classification.primary_classification

    if action_upper == "DISABLE_WININET_PROXY":
        if primary in {"DEAD_PROXY_CONFIG", "WININET_WINHTTP_MISMATCH"}:
            allowed = not dry_run and confirmation == token
            return PolicyDecision(
                action=action_upper,
                allowed=allowed,
                requires_confirmation=True,
                confirmation_token=token,
                risk_level="medium",
                rationale="Dead or mismatched localhost proxy can be disabled only with user confirmation.",
                safety_checks=safety_checks_for(action_upper),
            )
        return PolicyDecision(
            action=action_upper,
            allowed=False,
            requires_confirmation=True,
            confirmation_token=token,
            risk_level="medium",
            rationale=f"Classification {primary} does not meet safe-disable criteria without review.",
            safety_checks=safety_checks_for(action_upper),
        )

    if action_upper == "KILL_PROXY_PROCESS":
        return PolicyDecision(
            action=action_upper,
            allowed=False,
            requires_confirmation=True,
            confirmation_token="",
            risk_level="high",
            rationale="No silent process killing — action unsupported.",
            safety_checks=safety_checks_for(action_upper),
        )

    return PolicyDecision(
        action=action_upper,
        allowed=False,
        requires_confirmation=True,
        confirmation_token=token,
        risk_level="low",
        rationale="Unknown action — default deny.",
        safety_checks=safety_checks_for(action_upper),
    )
