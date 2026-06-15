"""Evidence Case model tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.evidence_case import (
    EvidenceCase,
    build_evidence_case_from_fixture,
    export_json_schema,
    generate_case_report,
    load_evidence_case,
    save_evidence_case,
    validate_evidence_case,
    write_json_schema,
)
from src.platform_core.evidence_case.models import ExecutionStage
from windows_network_toolkit.cli import main

REPO = Path(__file__).resolve().parents[1]
CASE1 = REPO / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def test_build_case_from_fixture_has_all_stages() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    names = case.stage_names()
    assert len(names) == 10
    assert case.observation.symptom
    assert case.evidence.bundle.items
    assert case.hypothesis.hypothesis.incident_type == "DEAD_PROXY_CONFIG"
    assert case.validation.status in {"passed", "not_run", "inconclusive", "failed"}
    assert case.execution.dry_run is True
    assert case.execution.registry_modified is False


def test_validate_fixture_built_case() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    result = validate_evidence_case(case)
    assert result.valid is True
    assert result.case_id == case.case_id
    assert len(result.stages_present) == 10


def test_registry_modified_without_confirmation_fails_validation() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    bad = case.model_copy(
        update={
            "execution": case.execution.model_copy(
                update={
                    "registry_modified": True,
                    "dry_run": False,
                    "confirmation_token": "",
                }
            )
        }
    )
    with pytest.raises(ValueError):
        ExecutionStage.model_validate(bad.execution.model_dump())


def test_registry_modified_with_wrong_token_fails() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    bad = case.model_copy(
        update={
            "execution": ExecutionStage(
                execution_id="exe-test",
                timestamp_utc=case.created_at,
                registry_modified=True,
                dry_run=False,
                confirmation_token="WRONG_TOKEN",
            )
        }
    )
    result = validate_evidence_case(bad)
    assert result.valid is False
    assert any(i.code == "registry_invalid_confirmation" for i in result.issues)


def test_registry_modified_dry_run_fails_model() -> None:
    with pytest.raises(ValueError):
        ExecutionStage(
            execution_id="exe-test",
            timestamp_utc="2026-01-01T00:00:00Z",
            registry_modified=True,
            dry_run=True,
            confirmation_token="DISABLE_WININET_PROXY",
        )


def test_json_schema_export() -> None:
    schema = export_json_schema()
    assert schema.get("title") == "EvidenceCase"
    assert "properties" in schema
    assert "case_id" in schema["properties"]


def test_write_schema_file(tmp_path: Path) -> None:
    path = write_json_schema(tmp_path / "evidence_case.schema.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["title"] == "EvidenceCase"


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    case = build_evidence_case_from_fixture(CASE1)
    out = tmp_path / "case.json"
    save_evidence_case(case, out)
    loaded = load_evidence_case(out)
    assert loaded.case_id == case.case_id
    assert loaded.schema_version == "evidence_case.v1"


def test_markdown_report() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    text = generate_case_report(case, fmt="markdown")
    assert "Evidence Case" in text
    assert "DEAD_PROXY_CONFIG" in text or "Proxy" in text
    assert "dry_run=True" in text


def test_cli_create_validate_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "case.json"
    code = main(
        [
            "evidence-case",
            "create",
            "--fixture",
            str(CASE1.relative_to(REPO)).replace("\\", "/"),
            "--out",
            str(out),
            "--json",
        ],
        prog="windows_network_toolkit",
    )
    assert code == 0
    assert out.is_file()
    capsys.readouterr()

    code = main(["evidence-case", "validate", str(out)], prog="windows_network_toolkit")
    assert code == 0
    validate_out = json.loads(capsys.readouterr().out)
    assert validate_out["valid"] is True

    capsys.readouterr()
    code = main(
        ["evidence-case", "report", str(out), "--format", "markdown"],
        prog="windows_network_toolkit",
    )
    assert code == 0
    assert "Observation" in capsys.readouterr().out


def test_cli_schema_export(tmp_path: Path) -> None:
    schema_path = tmp_path / "schema.json"
    code = main(
        ["evidence-case", "schema", "--out", str(schema_path), "--json"],
        prog="windows_network_toolkit",
    )
    assert code == 0
    assert schema_path.is_file()


def test_evidence_case_pydantic_roundtrip() -> None:
    case = build_evidence_case_from_fixture(CASE1)
    roundtrip = EvidenceCase.model_validate(case.to_dict())
    assert roundtrip.case_id == case.case_id
