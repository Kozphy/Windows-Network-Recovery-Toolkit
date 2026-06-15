"""Enterprise control catalog — maps to business objectives."""

from __future__ import annotations

from src.platform_core.controls.models import Control
from src.platform_core.enterprise.enums import ControlType

CONTROLS: tuple[Control, ...] = (
    Control(
        control_id="NET-001",
        control_name="Proxy Baseline Validation",
        objective_id="BO-001",
        objective="Prevent unauthorized proxy modification",
        control_owner="IT Operations",
        control_type=ControlType.DETECTIVE,
        frequency="continuous",
        evidence_requirements=[
            "WinINET proxy registry snapshot",
            "Listener correlation on configured port",
            "Classification with limitations[]",
        ],
    ),
    Control(
        control_id="NET-002",
        control_name="Registry Integrity Validation",
        objective_id="BO-002",
        objective="Detect unauthorized Internet Settings changes",
        control_owner="Security Governance",
        control_type=ControlType.DETECTIVE,
        frequency="daily",
        evidence_requirements=["Registry writer telemetry (Sysmon E13) when available"],
    ),
    Control(
        control_id="NET-003",
        control_name="TLS Trust Path Validation",
        objective_id="BO-004",
        objective="Detect TLS path anomalies",
        control_owner="Security Governance",
        control_type=ControlType.DETECTIVE,
        frequency="on_incident",
        evidence_requirements=["Direct vs proxied certificate contrast", "Documented limitations"],
    ),
    Control(
        control_id="NET-004",
        control_name="Remediation Preview Gate",
        objective_id="BO-003",
        objective="Ensure remediation is policy-gated and auditable",
        control_owner="Internal Audit",
        control_type=ControlType.PREVENTIVE,
        frequency="per_change",
        evidence_requirements=["Dry-run default", "Typed confirmation", "Audit JSONL"],
    ),
    Control(
        control_id="NET-005",
        control_name="Connectivity Recovery Procedure",
        objective_id="BO-005",
        objective="Restore endpoint connectivity with minimal disruption",
        control_owner="SRE",
        control_type=ControlType.CORRECTIVE,
        frequency="on_incident",
        evidence_requirements=["Remediation preview", "Rollback plan", "Post-change validation"],
    ),
)

_CLASSIFICATION_CONTROLS: dict[str, list[str]] = {
    "DEAD_PROXY_CONFIG": ["NET-001", "NET-004", "NET-005"],
    "UNKNOWN_LOCAL_PROXY": ["NET-001", "NET-002", "NET-004"],
    "TLS_PATH_MISMATCH": ["NET-003", "NET-004"],
    "REMEDIATION_NOT_STICKY": ["NET-002", "NET-004"],
    "NO_PROXY": ["NET-001"],
}


def controls_for_classification(classification: str) -> list[Control]:
    ids = _CLASSIFICATION_CONTROLS.get(classification, ["NET-001", "NET-004"])
    id_set = set(ids)
    return [c for c in CONTROLS if c.control_id in id_set]


def get_control(control_id: str) -> Control | None:
    return next((c for c in CONTROLS if c.control_id == control_id), None)


def list_controls() -> list[Control]:
    return list(CONTROLS)
