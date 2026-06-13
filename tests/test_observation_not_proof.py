"""Principle: observation is not proof — raw observations cannot trigger remediation."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.principles.validator import validate_principles

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_cs1_fixture_passes_observation_not_proof() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    result = validate_principles(data, remediation_requested=False)
    check = next(c for c in result.checks if c.principle_id == "observation_not_proof")
    assert check.passed


def test_observation_only_remediation_fails_principle() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    stripped = dict(data)
    stripped.pop("proof", None)
    result = validate_principles(stripped, remediation_requested=True)
    check = next(c for c in result.checks if c.principle_id == "observation_not_proof")
    assert not check.passed
    assert any("observation" in v.lower() for v in check.violations)


def test_structured_proof_allows_remediation_preview() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    data["remediation_requested"] = True
    result = validate_principles(data, remediation_requested=True)
    check = next(c for c in result.checks if c.principle_id == "observation_not_proof")
    assert check.passed
