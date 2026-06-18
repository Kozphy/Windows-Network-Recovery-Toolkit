"""Policy decision engine — classification + proof + action → PolicyDecision."""

from __future__ import annotations

from typing import Any

from windows_network_toolkit.models import ClassificationResult, ProofResult
from windows_network_toolkit.platform.policy import evaluate_policy
from windows_network_toolkit.platform.risk_scoring import score_risk
from windows_network_toolkit.proof import run_diagnose_proof
from windows_network_toolkit.proxy_classification import classify_from_live


def decide(
    action: str,
    *,
    classification: ClassificationResult | None = None,
    proof: ProofResult | None = None,
    dry_run: bool = True,
    confirmation: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    cls = classification or classify_from_live(**kwargs)
    pr = proof or run_diagnose_proof(**kwargs)
    decision = evaluate_policy(action, cls, pr, dry_run=dry_run, confirmation=confirmation)
    risk = score_risk(cls, pr)
    return {
        "policy_decision": decision.to_dict(),
        "classification": cls.to_dict(),
        "proof": pr.to_dict(),
        "risk_assessment": risk,
    }
