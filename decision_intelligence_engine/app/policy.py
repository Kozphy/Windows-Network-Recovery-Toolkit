from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import Recommendation


@dataclass(frozen=True)
class GovernancePolicy:
    version: str
    min_evidence_coverage: float
    min_confidence: float
    high_risk_threshold: float
    max_unknowns_without_flag: int
    blocking_flags: frozenset[str]

    def evaluate(self, recommendation: Recommendation) -> list[str]:
        flags: list[str] = []
        if recommendation.evidence_coverage < self.min_evidence_coverage:
            flags.append("LOW_EVIDENCE_COVERAGE")
        if recommendation.confidence < self.min_confidence:
            flags.append("LOW_CONFIDENCE")
        if len(recommendation.unknowns) > self.max_unknowns_without_flag:
            flags.append("MATERIAL_UNKNOWNS")
        selected = next(
            item for item in recommendation.assessments
            if item.option == recommendation.recommended_option
        )
        if selected.risk >= self.high_risk_threshold:
            flags.append("HIGH_RISK_RECOMMENDATION")
        return flags


def load_policy(path: str | Path | None = None) -> GovernancePolicy:
    configured = path or os.getenv("DI_POLICY_PATH", "policies/v1.json")
    policy_path = Path(configured)
    if not policy_path.exists():
        package_root = Path(__file__).resolve().parent.parent
        policy_path = package_root / configured
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    thresholds = payload["thresholds"]
    return GovernancePolicy(
        version=str(payload["version"]),
        min_evidence_coverage=float(thresholds["min_evidence_coverage"]),
        min_confidence=float(thresholds["min_confidence"]),
        high_risk_threshold=float(thresholds["high_risk_threshold"]),
        max_unknowns_without_flag=int(thresholds["max_unknowns_without_flag"]),
        blocking_flags=frozenset(map(str, payload["blocking_flags"])),
    )


def approval_allowed(
    recommendation: Recommendation,
    policy: GovernancePolicy | None = None,
) -> tuple[bool, str | None]:
    active = policy or load_policy()
    hit = active.blocking_flags.intersection(recommendation.policy_flags)
    if hit:
        return False, f"policy {active.version} blocks approval: {', '.join(sorted(hit))}"
    return True, None
