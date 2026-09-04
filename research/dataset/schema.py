"""Public research dataset sample schema (Pydantic)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

OsCategory = Literal[
    "windows_10",
    "windows_11",
    "windows_server",
    "unspecified_fixture",
]
SplitName = Literal["development", "held_out", "synthetic_generated"]
Severity = Literal["none", "low", "medium", "high", "labeled", "ambiguous"]


class ResearchSample(BaseModel):
    """One research-safe benchmark sample.

    Ground-truth fields are independent of detector predictions.
    """

    sample_id: str
    scenario_id: str
    os_version_category: OsCategory = "unspecified_fixture"
    evidence_features: dict[str, Any] = Field(default_factory=dict)
    ground_truth_failure: str
    ground_truth_incident_class: str
    severity: Severity = "labeled"
    compound_failure: bool = False
    expected_action: str
    repairable: bool = True
    provenance: str
    generation_seed: int | None = None
    split: SplitName = "development"
    limitations: list[str] = Field(default_factory=list)

    @field_validator("ground_truth_failure")
    @classmethod
    def _failure_id(cls, value: str) -> str:
        text = value.strip()
        if not text.startswith("F_"):
            raise ValueError(
                f"ground_truth_failure must be taxonomy id starting with F_: {value!r}"
            )
        return text

    @field_validator("sample_id", "scenario_id", "ground_truth_incident_class", "expected_action")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("field must be non-empty")
        return text
