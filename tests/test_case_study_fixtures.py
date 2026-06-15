"""Case study fixture contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CASE_DIR = REPO / "tests" / "fixtures" / "case_studies"

REQUIRED_KEYS = (
    "case_id",
    "title",
    "symptom",
    "classification",
    "policy_decision",
    "proof",
    "remediation_preview",
    "audit_trail",
    "dry_run",
)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "case_1_dead_wininet_proxy.json",
        "case_2_proxy_reverter_node.json",
        "case_3_tls_mismatch.json",
    ],
)
def test_case_study_fixture_schema(fixture_name: str) -> None:
    path = CASE_DIR / fixture_name
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in REQUIRED_KEYS:
        assert key in data, f"missing {key} in {fixture_name}"
    assert data["dry_run"] is True
    assert data["remediation_preview"]["dry_run"] is True
    assert data["remediation_preview"]["no_changes_made"] is True
    limitations = data.get("classification", {}).get("limitations") or []
    assert limitations, f"limitations required in {fixture_name}"


def test_case_1_dead_proxy_classification() -> None:
    data = json.loads((CASE_DIR / "case_1_dead_wininet_proxy.json").read_text(encoding="utf-8"))
    assert data["classification"]["primary_classification"] == "DEAD_PROXY_CONFIG"
    assert data["proof"]["conclusion"]["status"] == "supported"


def test_case_2_reverter_observe_policy() -> None:
    data = json.loads((CASE_DIR / "case_2_proxy_reverter_node.json").read_text(encoding="utf-8"))
    assert data["policy_decision"]["outcome"] == "OBSERVE"
    assert "timeline" in data


def test_case_3_tls_defer_policy() -> None:
    data = json.loads((CASE_DIR / "case_3_tls_mismatch.json").read_text(encoding="utf-8"))
    assert data["tls_proof"]["certificate_mismatch"] is True
    assert data["policy_decision"]["outcome"] == "DEFER"
