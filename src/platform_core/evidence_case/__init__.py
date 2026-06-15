"""Evidence Case — end-to-end pipeline model and tooling."""

from __future__ import annotations

from .builder import (
    build_evidence_case_from_dict,
    build_evidence_case_from_fixture,
    load_evidence_case,
    save_evidence_case,
)
from .models import EVIDENCE_CASE_SCHEMA_VERSION, EvidenceCase, PipelineStage
from .report import generate_case_report
from .schema import export_json_schema, write_json_schema
from .validator import EvidenceCaseValidationResult, validate_evidence_case

__all__ = [
    "EVIDENCE_CASE_SCHEMA_VERSION",
    "EvidenceCase",
    "EvidenceCaseValidationResult",
    "PipelineStage",
    "build_evidence_case_from_dict",
    "build_evidence_case_from_fixture",
    "export_json_schema",
    "generate_case_report",
    "load_evidence_case",
    "save_evidence_case",
    "validate_evidence_case",
    "write_json_schema",
]
