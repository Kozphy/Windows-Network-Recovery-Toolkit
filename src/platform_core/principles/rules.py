"""Rule definitions loaded from principles.yaml."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.platform_core.principles.models import (
    Attribution,
    Observation,
    PolicyDecision,
    PrincipleCheck,
    ProofEnvelope,
    RiskDecision,
)

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_RULES_PATH = Path(__file__).with_name("principles.yaml")

_DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": "1.0",
    "principles": {
        "observation_not_proof": {
            "id": "observation_not_proof",
            "title": "Observation is not proof",
            "summary": "Registry reads and netstat snapshots are observations until structured proof checks pass.",
            "rule": "Raw observations cannot directly trigger remediation.",
        },
        "correlation_not_causation": {
            "id": "correlation_not_causation",
            "title": "Correlation is not causation",
            "summary": "Listener/process correlation does not prove registry-writer causation without telemetry.",
            "rule": "Dead localhost port cannot imply malicious writer without Sysmon E13 or equivalent.",
        },
        "confidence_not_certainty": {
            "id": "confidence_not_certainty",
            "title": "Confidence is not certainty",
            "summary": "Scores are ordinal/heuristic rankings — not probabilities of compromise.",
            "rule": "Confidence must be rendered as ordinal or heuristic, never as probability.",
        },
        "policy_not_safety": {
            "id": "policy_not_safety",
            "title": "Policy permission is not a safety guarantee",
            "summary": "ALLOW outcomes still require dry-run preview, confirmation, rollback, monitoring, and audit.",
            "rule": "Policy ALLOW must not bypass dry-run, typed confirmation, rollback plan, monitoring, or audit.",
        },
    },
    "telemetry_writer_sources": ["sysmon_e13", "procmon", "etw_registry"],
    "blocked_overclaim_terms": [
        "confirmed malware",
        "confirms malware",
        "prove malware",
        "proves malware",
        "proven malware",
        "confirmed mitm",
        "confirms mitm",
        "prove mitm",
        "proves mitm",
        "proven mitm",
        "100% certain",
        "probability of compromise",
    ],
    "probability_phrases": ["% chance", "percent chance", "probability of"],
    "required_policy_controls": [
        "dry_run_default",
        "typed_confirmation",
        "rollback_plan",
        "post_change_monitoring",
        "audit_logging",
    ],
}


@lru_cache(maxsize=1)
def load_principles_config() -> dict[str, Any]:
    if not _RULES_PATH.is_file():
        return _DEFAULT_CONFIG
    raw = _RULES_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(raw)
        return loaded if isinstance(loaded, dict) else _DEFAULT_CONFIG
    if raw.strip().startswith("{"):
        return json.loads(raw)
    return _DEFAULT_CONFIG


def format_confidence_display(score: float) -> str:
    """Render confidence as ordinal/heuristic — never as probability."""
    rounded = round(score, 3)
    return f"ordinal {rounded} (heuristic score, not probability)"


def check_observation_not_proof(
    *,
    observations: list[Observation],
    proof: ProofEnvelope | None,
    remediation_requested: bool,
    policy: PolicyDecision | None,
) -> PrincipleCheck:
    cfg = load_principles_config()["principles"]["observation_not_proof"]
    violations: list[str] = []
    guidance: list[str] = []

    if remediation_requested:
        if proof is None or not proof.has_structured_proof:
            violations.append(
                "Remediation requested without structured proof envelope (observation-only path)."
            )
        if policy and policy.allowed and not policy.dry_run and (proof is None or not proof.has_structured_proof):
            violations.append("Policy ALLOW would execute from observations alone.")

    if observations and (proof is None or not proof.has_structured_proof) and remediation_requested:
        guidance.append("Run diagnose --proof before previewing remediation.")

    return PrincipleCheck(
        principle_id=cfg["id"],
        title=cfg["title"],
        passed=not violations,
        violations=violations,
        guidance=guidance or [cfg["summary"]],
    )


def _contains_blocked_overclaim(text: str, term: str) -> bool:
    lower = text.lower()
    needle = term.lower()
    start = 0
    while True:
        idx = lower.find(needle, start)
        if idx == -1:
            return False
        prefix = lower[max(0, idx - 24) : idx]
        if not any(neg in prefix for neg in ("does not ", "do not ", "not ", "never ", "without ")):
            return True
        start = idx + len(needle)
    return False


def check_correlation_not_causation(
    *,
    attribution: Attribution | None,
    risk: RiskDecision | None,
    proof: ProofEnvelope | None,
    narrative_text: str = "",
) -> PrincipleCheck:
    cfg = load_principles_config()["principles"]["correlation_not_causation"]
    violations: list[str] = []
    guidance: list[str] = []
    blocked = {t.lower() for t in load_principles_config().get("blocked_overclaim_terms", [])}

    combined = " ".join(
        filter(
            None,
            [
                narrative_text,
                risk.narrative if risk else "",
                " ".join(risk.limitations if risk else []),
                " ".join(proof.limitations if proof else []),
            ],
        )
    ).lower()

    for term in blocked:
        if _contains_blocked_overclaim(combined, term) and not (
            attribution and attribution.has_writer_telemetry
        ):
            violations.append(f"Overclaim blocked: '{term}' without writer telemetry proof.")

    if attribution and not attribution.listener_found:
        if "malicious writer" in combined or "malware writer" in combined:
            violations.append("Dead localhost port cannot imply malicious writer without telemetry.")

    if risk and risk.primary_classification == "DEAD_PROXY_CONFIG":
        if "malicious" in combined and not (attribution and attribution.has_writer_telemetry):
            violations.append("DEAD_PROXY_CONFIG must not be narrated as malicious without writer proof.")

    if attribution and not attribution.has_writer_telemetry and attribution.registry_writer_confirmed:
        violations.append("registry_writer_confirmed=true without telemetry source.")

    return PrincipleCheck(
        principle_id=cfg["id"],
        title=cfg["title"],
        passed=not violations,
        violations=violations,
        guidance=guidance or [cfg["summary"]],
    )


def check_confidence_not_certainty(
    *,
    risk: RiskDecision | None,
    proof: ProofEnvelope | None,
    narrative_text: str = "",
) -> PrincipleCheck:
    cfg = load_principles_config()["principles"]["confidence_not_certainty"]
    violations: list[str] = []
    phrases = load_principles_config().get("probability_phrases", [])

    texts = [narrative_text]
    if risk:
        texts.append(risk.narrative)
    if proof:
        texts.append(proof.hypothesis)

    blob = " ".join(texts).lower()
    for phrase in phrases:
        if phrase.lower() in blob:
            violations.append(f"Probability language detected: '{phrase}'.")

    if "%" in blob and "ordinal" not in blob and "heuristic" not in blob:
        if any(p in blob for p in ("chance", "probability", "certain")):
            violations.append("Percent phrasing must not describe confidence as probability.")

    return PrincipleCheck(
        principle_id=cfg["id"],
        title=cfg["title"],
        passed=not violations,
        violations=violations,
        guidance=[cfg["summary"]],
    )


def check_policy_not_safety(*, policy: PolicyDecision | None) -> PrincipleCheck:
    cfg = load_principles_config()["principles"]["policy_not_safety"]
    violations: list[str] = []
    required = load_principles_config().get("required_policy_controls", [])

    if policy is None:
        return PrincipleCheck(
            principle_id=cfg["id"],
            title=cfg["title"],
            passed=True,
            violations=[],
            guidance=[cfg["summary"]],
        )

    outcome = policy.outcome.upper()
    if outcome == "ALLOW" or policy.allowed:
        control_map = {
            "dry_run_default": policy.dry_run is True or policy.requires_confirmation,
            "typed_confirmation": policy.requires_confirmation and bool(policy.confirmation_token),
            "rollback_plan": policy.rollback_plan_present,
            "post_change_monitoring": policy.monitoring_recommended,
            "audit_logging": policy.audit_logging,
        }
        for name in required:
            if not control_map.get(name, False):
                violations.append(f"Policy ALLOW missing required control: {name}.")

        if not policy.dry_run and not policy.confirmation_token:
            violations.append("Non-dry-run ALLOW without typed confirmation token.")

    return PrincipleCheck(
        principle_id=cfg["id"],
        title=cfg["title"],
        passed=not violations,
        violations=violations,
        guidance=[cfg["summary"]],
    )


def dry_run_applies(policy: PolicyDecision | None) -> bool:
    if policy is None:
        return True
    return policy.dry_run
