"""Seed business objectives for endpoint network risk."""

from __future__ import annotations

from src.platform_core.business_objectives.models import BusinessObjective
from src.platform_core.enterprise.enums import Criticality

OBJECTIVES: tuple[BusinessObjective, ...] = (
    BusinessObjective(
        id="BO-001",
        name="Maintain endpoint connectivity",
        description="Ensure corporate endpoints can reach required services reliably.",
        owner="IT Operations",
        criticality=Criticality.HIGH,
        regulatory_mapping=["SOC2-A1.2"],
    ),
    BusinessObjective(
        id="BO-002",
        name="Protect confidential data",
        description="Prevent unauthorized interception of data in transit on endpoints.",
        owner="CISO Office",
        criticality=Criticality.CRITICAL,
        regulatory_mapping=["SOC2-CC6.1", "ISO27001-A.13"],
    ),
    BusinessObjective(
        id="BO-003",
        name="Ensure regulatory compliance",
        description="Demonstrate control effectiveness for technology risk audits.",
        owner="Internal Audit",
        criticality=Criticality.HIGH,
        regulatory_mapping=["ITGC", "SOC2"],
    ),
    BusinessObjective(
        id="BO-004",
        name="Prevent unauthorized traffic interception",
        description="Detect proxy/TLS path anomalies that may indicate interception risk.",
        owner="Security Governance",
        criticality=Criticality.CRITICAL,
        regulatory_mapping=["SOC2-CC6.7"],
    ),
    BusinessObjective(
        id="BO-005",
        name="Maintain service availability",
        description="Reduce MTTR for browser and application connectivity failures.",
        owner="SRE / Endpoint Reliability",
        criticality=Criticality.HIGH,
        regulatory_mapping=["SOC2-A1.2"],
    ),
)


def get_objective(objective_id: str) -> BusinessObjective | None:
    return next((o for o in OBJECTIVES if o.id == objective_id), None)


def list_objectives() -> list[BusinessObjective]:
    return list(OBJECTIVES)
