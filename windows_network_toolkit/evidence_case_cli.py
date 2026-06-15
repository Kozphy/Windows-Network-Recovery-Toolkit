"""CLI facade for Evidence Case operations."""

from __future__ import annotations

from typing import Any

from src.platform_core.evidence_case import (
    build_evidence_case_from_fixture,
    export_json_schema,
    generate_case_report,
    load_evidence_case,
    save_evidence_case,
    validate_evidence_case,
    write_json_schema,
)


def create_case(
    *,
    fixture: str,
    out: str,
    title: str = "",
) -> dict[str, Any]:
    case = build_evidence_case_from_fixture(fixture, title=title)
    save_evidence_case(case, out)
    return case.to_dict()


def report_case(
    case_path: str,
    *,
    fmt: str = "markdown",
) -> str:
    case = load_evidence_case(case_path)
    return generate_case_report(case, fmt=fmt)  # type: ignore[arg-type]


def validate_case_file(case_path: str) -> dict[str, Any]:
    case = load_evidence_case(case_path)
    return validate_evidence_case(case).to_dict()


def export_schema(out: str = "schemas/evidence_case.schema.json") -> dict[str, Any]:
    path = write_json_schema(out)
    return {"schema_path": str(path), "schema": export_json_schema()}
