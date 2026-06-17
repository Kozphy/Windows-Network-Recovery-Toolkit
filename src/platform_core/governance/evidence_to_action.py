"""Evidence-to-Action Governance Model — formal epistemic envelope for decision outputs."""

from __future__ import annotations

from typing import Any

GOVERNANCE_MODEL = "evidence_to_action.v1"
CONFIDENCE_TYPE = "ordinal_not_probability"

_ACCUSATORY_CLASSIFICATIONS = frozenset(
    {
        "SUSPICIOUS_PROXY",
        "POSSIBLE_MITM_RISK",
        "UNKNOWN_LOCAL_PROXY",
        "REVERTER_SUSPECTED",
    }
)

_CAUSAL_LANGUAGE_TIERS = frozenset({"attribution", "final_causation"})

_PROHIBITED_CAUSAL_PHRASES = (
    "caused by",
    "prove malware",
    "proved malware",
    "proves malware",
    "confirmed mitm",
    "confirms mitm",
    "prove mitm",
    "attacker",
    "compromised",
    "safe to execute automatically",
)

_ALLOWED_LANGUAGE_EXAMPLES = (
    "evidence is consistent with",
    "correlated with",
    "supports the hypothesis",
    "requires further attribution",
    "possible MITM risk",
    "preview only",
    "requires typed confirmation",
)


def resolve_claim_strength(
    *,
    evidence_tier: str | None = None,
    proof_conclusion: str | None = None,
) -> str:
    if evidence_tier:
        normalized = evidence_tier.lower().replace("observed_only", "observation")
        return normalized
    if proof_conclusion == "supported":
        return "proof"
    if proof_conclusion in ("weakened", "inconclusive"):
        return "correlation"
    return "observation"


def causal_language_allowed(*, claim_strength: str) -> bool:
    return claim_strength.lower() in _CAUSAL_LANGUAGE_TIERS


def classification_is_accusation(*, primary_classification: str | None) -> bool:
    """Always False in outputs — classifications are triage labels, not accusations."""
    _ = primary_classification
    return False


def resolve_execution_authority(
    *,
    policy_outcome: str | None = None,
    dry_run: bool = True,
    requires_confirmation: bool = True,
    executed: bool = False,
) -> str:
    outcome = (policy_outcome or "").upper()
    if outcome == "BLOCK" or outcome == "DENY":
        return "blocked"
    if executed and not dry_run and not requires_confirmation:
        return "automated_forbidden"
    if dry_run or outcome in ("PREVIEW_ONLY", "PREVIEW"):
        return "preview_only"
    if outcome == "REQUIRE_TYPED_CONFIRMATION":
        return "human_required"
    return "human_required"


def build_governance_envelope(
    *,
    primary_classification: str | None = None,
    evidence_tier: str | None = None,
    proof_conclusion: str | None = None,
    policy_outcome: str | None = None,
    dry_run: bool = True,
    requires_confirmation: bool = True,
    executed: bool = False,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    claim_strength = resolve_claim_strength(
        evidence_tier=evidence_tier,
        proof_conclusion=proof_conclusion,
    )
    base_limitations = [
        "Observation is not proof; correlation is not causation.",
        "Confidence is ordinal, not a statistical probability.",
        "Classification is not accusation.",
        "Policy permission is not a safety guarantee.",
        "Recommendation is not execution authority.",
    ]
    merged_limits = base_limitations + list(limitations or [])
    if primary_classification in _ACCUSATORY_CLASSIFICATIONS:
        merged_limits.append(
            f"{primary_classification} is an investigative label — not a confirmed threat verdict."
        )

    return {
        "governance_model": GOVERNANCE_MODEL,
        "claim_strength": claim_strength,
        "confidence_type": CONFIDENCE_TYPE,
        "causal_language_allowed": causal_language_allowed(claim_strength=claim_strength),
        "classification_is_accusation": classification_is_accusation(
            primary_classification=primary_classification
        ),
        "execution_authority": resolve_execution_authority(
            policy_outcome=policy_outcome,
            dry_run=dry_run,
            requires_confirmation=requires_confirmation,
            executed=executed,
        ),
        "limitations": merged_limits,
    }


def attach_governance_envelope(payload: dict[str, Any], **context: Any) -> dict[str, Any]:
    """Return a shallow copy of payload with nested governance envelope (backward compatible)."""
    envelope = build_governance_envelope(
        primary_classification=context.get("primary_classification")
        or _extract_classification(payload),
        evidence_tier=context.get("evidence_tier") or _extract_evidence_tier(payload),
        proof_conclusion=context.get("proof_conclusion") or _extract_proof_conclusion(payload),
        policy_outcome=context.get("policy_outcome") or _extract_policy_outcome(payload),
        dry_run=bool(context.get("dry_run", _extract_dry_run(payload, default=True))),
        requires_confirmation=bool(
            context.get("requires_confirmation", _extract_requires_confirmation(payload, default=True))
        ),
        executed=bool(context.get("executed", False)),
        limitations=list(context.get("limitations") or payload.get("limitations") or []),
    )
    out = dict(payload)
    out["governance"] = envelope
    return out


def narrative_passes_governance_language(
    text: str,
    *,
    claim_strength: str,
    primary_classification: str | None = None,
) -> bool:
    """Return False if text uses prohibited causal/accusatory language for the claim tier."""
    lower = text.lower()
    if not causal_language_allowed(claim_strength=claim_strength):
        for phrase in _PROHIBITED_CAUSAL_PHRASES:
            if phrase in lower and not _negated(lower, phrase):
                return False
    if primary_classification == "SUSPICIOUS_PROXY":
        if any(p in lower for p in ("prove malware", "proved malware", "malware confirmed")):
            return False
    if primary_classification == "POSSIBLE_MITM_RISK":
        if any(p in lower for p in ("confirmed mitm", "confirms mitm", "prove mitm", "proven mitm")):
            return False
    return True


def _negated(text: str, phrase: str) -> bool:
    idx = text.find(phrase)
    if idx == -1:
        return False
    prefix = text[max(0, idx - 24) : idx]
    return any(neg in prefix for neg in ("does not ", "do not ", "not ", "never ", "without "))


def _extract_classification(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("classification"), str):
        return payload["classification"]
    cls = payload.get("classification")
    if isinstance(cls, dict):
        return cls.get("primary_classification")
    cr = payload.get("classification_result")
    if isinstance(cr, dict):
        return cr.get("primary_classification")
    finding = payload.get("findings")
    if isinstance(finding, list) and finding:
        return finding[0].get("classification")
    return None


def _extract_evidence_tier(payload: dict[str, Any]) -> str | None:
    for key in ("evidence_tier", "evidence_level", "claim_strength"):
        if payload.get(key):
            return str(payload[key])
    gov = payload.get("governance")
    if isinstance(gov, dict) and gov.get("claim_strength"):
        return str(gov["claim_strength"])
    return None


def _extract_proof_conclusion(payload: dict[str, Any]) -> str | None:
    conclusion = payload.get("conclusion")
    if isinstance(conclusion, dict):
        return conclusion.get("status")
    proof = payload.get("proof") or payload.get("proof_status")
    if isinstance(proof, dict):
        c = proof.get("conclusion")
        if isinstance(c, dict):
            return c.get("status")
        return proof.get("conclusion_status")
    return payload.get("conclusion_status")


def _extract_policy_outcome(payload: dict[str, Any]) -> str | None:
    policy = payload.get("policy_decision") or payload.get("policy") or {}
    if isinstance(policy, dict):
        return policy.get("outcome") or policy.get("decision")
    return None


def _extract_dry_run(payload: dict[str, Any], *, default: bool) -> bool:
    if "dry_run" in payload:
        return bool(payload["dry_run"])
    policy = payload.get("policy_decision") or payload.get("policy") or {}
    if isinstance(policy, dict) and "dry_run" in policy:
        return bool(policy["dry_run"])
    return default


def _extract_requires_confirmation(payload: dict[str, Any], *, default: bool) -> bool:
    policy = payload.get("policy_decision") or payload.get("policy") or {}
    if isinstance(policy, dict) and "requires_confirmation" in policy:
        return bool(policy["requires_confirmation"])
    return default
