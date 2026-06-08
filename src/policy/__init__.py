"""Policy gates: hypothesis gates + proxy incident policy engine."""

from __future__ import annotations

from .proxy_policy_engine import evaluate_proxy_policy, evaluate_proxy_policy_input, load_proxy_policy_config
from .models import PolicyDecisionKind, PolicySeverity, ProxyPolicyDecision, ProxyPolicyInput

from .hypothesis_gates import (
    HYPOTHESIS_DISPLAY_NAME,
    PROOF_LOCALHOST_PROXY_HYPOTHESES,
    HypothesisDecisionRow,
    PolicyDecision,
    build_hypothesis_decisions,
    build_why,
    decide_policy,
    hypothesis_display_name,
    proof_status_token,
)

__all__ = [
    "HYPOTHESIS_DISPLAY_NAME",
    "PROOF_LOCALHOST_PROXY_HYPOTHESES",
    "HypothesisDecisionRow",
    "PolicyDecision",
    "build_hypothesis_decisions",
    "build_why",
    "decide_policy",
    "hypothesis_display_name",
    "proof_status_token",
]
