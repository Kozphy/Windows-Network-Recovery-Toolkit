"""Principle: confidence is not certainty — ordinal scores, not probabilities."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.principles.rules import format_confidence_display
from src.platform_core.principles.validator import validate_principles
from windows_network_toolkit.proof import run_diagnose_proof

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_confidence_display_is_ordinal_not_probability() -> None:
    display = format_confidence_display(0.92)
    assert "ordinal" in display
    assert "not probability" in display
    assert "%" not in display


def test_probability_language_fails_principle() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    data["executive_summary"] = "92% chance this is malware."
    result = validate_principles(data)
    check = next(c for c in result.checks if c.principle_id == "confidence_not_certainty")
    assert not check.passed


def test_diagnose_proof_json_includes_confidence_display() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    proof = run_diagnose_proof(inject=data.get("proof"))
    payload = proof.to_dict()
    assert "confidence_display" in payload
    assert "not probability" in payload["confidence_display"]
    assert "not probability" in payload["conclusion"]["confidence_display"]
