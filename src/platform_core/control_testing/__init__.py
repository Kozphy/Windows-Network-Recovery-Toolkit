"""Evidence-first control testing primitives.

Control testing evaluates whether available evidence satisfies an explicit
control procedure. A test result never authorizes remediation and never
upgrades observation into proof without referenced evidence.
"""

from .engine import evaluate_control, evaluate_controls
from .models import (
    ControlDefinition,
    ControlTestResult,
    EvidenceRequirement,
    TestConclusion,
)

__all__ = [
    "ControlDefinition",
    "ControlTestResult",
    "EvidenceRequirement",
    "TestConclusion",
    "evaluate_control",
    "evaluate_controls",
]
