"""CTRL-001–010 regression anchors."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CTRL_TESTS = [
    ("CTRL-001", "tests/platform_core/classification/test_classification_matrix.py"),
    ("CTRL-002", "tests/test_proxy_state_transitions.py"),
    ("CTRL-003", "tests/windows_network_toolkit/test_proxy_health.py"),
    ("CTRL-004", "tests/platform_core/attribution/test_listener_classification.py"),
    ("CTRL-005", "tests/test_proxy_state_transitions.py"),
    ("CTRL-006", "tests/test_proxy_classifier_safety_contract.py"),
    ("CTRL-007", "tests/windows_network_toolkit/test_proxy_state_machine.py"),
    ("CTRL-008", "tests/platform_core/proof/test_proof_engine.py"),
    ("CTRL-009", "tests/test_policy_safety_contract.py"),
    ("CTRL-010", "tests/platform_core/governance/test_hash_chained_audit.py"),
]


@pytest.mark.parametrize("ctrl_id,test_path", CTRL_TESTS)
def test_control_matrix_test_file_exists(ctrl_id: str, test_path: str) -> None:
    path = ROOT / test_path
    assert path.is_file(), f"{ctrl_id} anchor missing: {test_path}"


def test_chained_audit_fixture_exists() -> None:
    path = ROOT / "tests/fixtures/risk_analytics/audit_sample_chained/incidents.jsonl"
    assert path.is_file()
