"""Baseline prediction result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaselinePrediction:
    """Unified prediction record across B0–B3."""

    case_id: str
    baseline: str
    predicted_incident_class: str
    proof_tier: str = "T0_OBSERVATION_ONLY"
    policy_posture: str = "PREVIEW_ONLY"
    remediation_posture: str = "PREVIEW_ONLY"
    supporting_evidence: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    abstained: bool = False
    unsupported: bool = False
    unsafe_action_proposed: bool = False
    audit_verified: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)
