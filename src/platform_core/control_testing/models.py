"""Typed contracts for deterministic, evidence-backed control testing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class TestConclusion(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_TESTED = "NOT_TESTED"


@dataclass(frozen=True)
class EvidenceRequirement:
    """One explicit evidence requirement in a control procedure."""

    evidence_type: str
    required_fields: tuple[str, ...] = ()
    minimum_tier: int = 0
    description: str = ""


@dataclass(frozen=True)
class ControlDefinition:
    """Versioned control objective and deterministic test procedure."""

    control_id: str
    version: str
    name: str
    objective: str
    requirements: tuple[EvidenceRequirement, ...]
    owner: str = "Technology Risk"
    frequency: str = "on_incident"
    limitations: tuple[str, ...] = (
        "A control test evaluates supplied evidence only; it is not a formal audit opinion.",
        "PASS does not authorize remediation or prove endpoint safety outside test scope.",
    )


@dataclass(frozen=True)
class ControlTestResult:
    """Immutable result with evidence lineage and explicit missing evidence."""

    test_id: str
    control_id: str
    control_version: str
    incident_id: str
    conclusion: TestConclusion
    tested_at_utc: str
    evidence_refs: tuple[str, ...]
    satisfied_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    rationale: str
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["conclusion"] = self.conclusion.value
        return payload


def make_test_id(
    *, control_id: str, control_version: str, incident_id: str, evidence_refs: tuple[str, ...]
) -> str:
    """Create a deterministic, retry-safe identifier for a control test."""

    payload = json.dumps(
        {
            "control_id": control_id,
            "control_version": control_version,
            "incident_id": incident_id,
            "evidence_refs": sorted(evidence_refs),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
