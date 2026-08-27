"""Typed scenario, telemetry, detection, and run-state models for purple_team."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class RunState(StrEnum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AUTHORIZED = "AUTHORIZED"
    SIMULATING = "SIMULATING"
    COLLECTING = "COLLECTING"
    DETECTING = "DETECTING"
    CLASSIFYING = "CLASSIFYING"
    RESPONDING = "RESPONDING"
    VERIFYING = "VERIFYING"
    MEASURING = "MEASURING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    DENIED = "DENIED"


class FailureCategory(StrEnum):
    SIMULATION_FAILURE = "SIMULATION_FAILURE"
    TELEMETRY_MISSING = "TELEMETRY_MISSING"
    COLLECTOR_FAILURE = "COLLECTOR_FAILURE"
    DETECTION_FALSE_NEGATIVE = "DETECTION_FALSE_NEGATIVE"
    DETECTION_FALSE_POSITIVE = "DETECTION_FALSE_POSITIVE"
    CLASSIFICATION_ERROR = "CLASSIFICATION_ERROR"
    REMEDIATION_FAILURE = "REMEDIATION_FAILURE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"
    ROLLBACK_FAILURE = "ROLLBACK_FAILURE"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
    SAFETY_DENIED = "SAFETY_DENIED"
    TELEMETRY_TIMING = "TELEMETRY_TIMING"
    NONE = "NONE"


@dataclass(frozen=True)
class MitreMapping:
    techniques: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"techniques": list(self.techniques), "notes": self.notes}


@dataclass(frozen=True)
class ScenarioSimulation:
    """Fixture-driven simulation contract — never live malware/persistence."""

    action: str
    fixture_path: str
    produces_events: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScenarioVerification:
    post_conditions: tuple[str, ...]
    independent: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_conditions": list(self.post_conditions),
            "independent": self.independent,
        }


@dataclass(frozen=True)
class ScenarioCleanup:
    required: bool
    steps: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"required": self.required, "steps": list(self.steps)}


@dataclass(frozen=True)
class ScenarioDefinition:
    """Strongly typed purple scenario — reject incomplete safety/rollback."""

    id: str
    title: str
    category: str
    risk_level: str
    safe_for_local_execution: bool
    preconditions: tuple[str, ...]
    simulation: ScenarioSimulation
    expected_telemetry: tuple[str, ...]
    expected_detection: str
    expected_response: str
    verification: ScenarioVerification
    cleanup: ScenarioCleanup
    expect_detection: bool = True
    benign_control: bool = False
    authorized_execution_required: bool = True
    allows_remote_target: bool = False
    allows_production_target: bool = False
    mitre: MitreMapping = field(default_factory=MitreMapping)
    description: str = ""
    false_positive_notes: str = ""
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "risk_level": self.risk_level,
            "safe_for_local_execution": self.safe_for_local_execution,
            "preconditions": list(self.preconditions),
            "simulation": self.simulation.to_dict(),
            "expected_telemetry": list(self.expected_telemetry),
            "expected_detection": self.expected_detection,
            "expected_response": self.expected_response,
            "verification": self.verification.to_dict(),
            "cleanup": self.cleanup.to_dict(),
            "expect_detection": self.expect_detection,
            "benign_control": self.benign_control,
            "authorized_execution_required": self.authorized_execution_required,
            "allows_remote_target": self.allows_remote_target,
            "allows_production_target": self.allows_production_target,
            "mitre": self.mitre.to_dict(),
            "description": self.description,
            "false_positive_notes": self.false_positive_notes,
            "limitations": list(self.limitations),
        }


@dataclass
class TelemetryEvent:
    event_id: str
    timestamp: str
    scenario_id: str
    source: str
    event_type: str
    entity: str
    before: dict[str, Any]
    after: dict[str, Any]
    collector_version: str
    confidence: float
    run_id: str = ""
    host: str = "fixture-host"
    evidence_hash: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DetectionResult:
    rule_id: str
    detected: bool
    confidence: float
    severity: str
    evidence: list[dict[str, Any]]
    explanation: str
    what_changed: str = ""
    why_suspicious: str = ""
    benign_alternative: str = ""
    recommended_action: str = ""
    false_positive_notes: str = ""
    mitre: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskScore:
    score: float
    band: str
    components: dict[str, float]
    assumptions: list[str]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    action: str
    dry_run_default: bool
    confirmation_token: str | None
    rationale: str
    requires_human_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RemediationOutcome:
    recommended: bool
    executed: bool
    success: bool
    dry_run: bool
    details: dict[str, Any]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    passed: bool
    post_conditions: list[dict[str, Any]]
    recovered: bool
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Invariant: failed verification cannot claim recovery.
        if not self.passed:
            d["recovered"] = False
        return d


@dataclass
class StageTiming:
    t0_simulation_start: float | None = None
    t1_telemetry_generated: float | None = None
    t2_telemetry_collected: float | None = None
    t3_detection_fires: float | None = None
    t4_classification_complete: float | None = None
    t5_remediation_starts: float | None = None
    t6_remediation_completes: float | None = None
    t7_verification_completes: float | None = None

    def latency(self, start: str, end: str) -> float | None:
        a = getattr(self, start)
        b = getattr(self, end)
        if a is None or b is None:
            return None
        return max(0.0, b - a)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "collection_latency_s": self.latency("t0_simulation_start", "t2_telemetry_collected"),
            "detection_latency_s": self.latency("t0_simulation_start", "t3_detection_fires"),
            "classification_latency_s": self.latency(
                "t0_simulation_start", "t4_classification_complete"
            ),
            "remediation_latency_s": self.latency("t5_remediation_starts", "t6_remediation_completes"),
            "verification_latency_s": self.latency(
                "t6_remediation_completes", "t7_verification_completes"
            ),
            "total_recovery_latency_s": self.latency(
                "t0_simulation_start", "t7_verification_completes"
            ),
            "mttd_s": self.latency("t0_simulation_start", "t3_detection_fires"),
        }


@dataclass
class ScenarioRunResult:
    run_id: str
    scenario_id: str
    state: RunState
    dry_run: bool
    authorized: bool
    transitions: list[dict[str, Any]]
    telemetry: list[TelemetryEvent]
    detections: list[DetectionResult]
    risk: RiskScore | None
    recommendation: Recommendation | None
    remediation: RemediationOutcome | None
    verification: VerificationResult | None
    timing: StageTiming
    failure_category: FailureCategory
    error: str | None
    expected_detection: bool
    detection_matched_expectation: bool
    true_positive: bool
    false_positive: bool
    true_negative: bool
    false_negative: bool
    evidence_bundle_path: str | None
    limitations: list[str]
    ablation: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "state": self.state.value,
            "dry_run": self.dry_run,
            "authorized": self.authorized,
            "transitions": self.transitions,
            "telemetry": [t.to_dict() for t in self.telemetry],
            "detections": [d.to_dict() for d in self.detections],
            "risk": self.risk.to_dict() if self.risk else None,
            "recommendation": self.recommendation.to_dict() if self.recommendation else None,
            "remediation": self.remediation.to_dict() if self.remediation else None,
            "verification": self.verification.to_dict() if self.verification else None,
            "timing": self.timing.to_dict(),
            "failure_category": self.failure_category.value,
            "error": self.error,
            "expected_detection": self.expected_detection,
            "detection_matched_expectation": self.detection_matched_expectation,
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "true_negative": self.true_negative,
            "false_negative": self.false_negative,
            "evidence_bundle_path": self.evidence_bundle_path,
            "limitations": self.limitations,
            "ablation": self.ablation,
        }
