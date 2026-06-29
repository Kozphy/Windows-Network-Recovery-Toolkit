"""Regression tests for reviewer-proof stability (mock pollution, serialization, planner)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from src.platform_core.remediation.planner import plan_proxy_drift_remediation
from windows_network_toolkit.audit.report_generator import generate_erp_report, generate_report
from windows_network_toolkit.tests.test_proxy_cli import (
    _attr_fixture,
    _proof_fixture,
)
from windows_network_toolkit.diagnostics.proxy.runner import run_full_incident_report

_MOCK_ARTIFACTS = ("<Mock", "mock.")


def test_report_survives_non_serializable_mock_in_remediation() -> None:
    mock_preview = MagicMock()
    text = generate_report(
        timeline=[],
        decision={"incident_type": "WININET_PROXY_DRIFT", "confidence": 0.5, "risk_level": "medium"},
        policy={"outcome": "PREVIEW_ONLY", "dry_run": True},
        remediation={"previews": [mock_preview], "rollback_plan": {}},
        fmt="markdown",
    )
    assert "[non-serializable-test-mock:MagicMock]" in text
    for artifact in _MOCK_ARTIFACTS:
        assert artifact not in text
    assert "MagicMock id=" not in text


def test_erp_report_after_full_incident_does_not_contain_raw_mock_artifacts() -> None:
    package = run_full_incident_report(
        "https://example.com/",
        inject_attribution=_attr_fixture(),
        inject_proof=_proof_fixture(),
    )
    md = generate_erp_report(package, fmt="markdown")
    json_text = generate_erp_report(package, fmt="json")
    for artifact in _MOCK_ARTIFACTS:
        assert artifact not in md
        assert artifact not in json_text
    assert "MagicMock id=" not in md
    assert "MagicMock id=" not in json_text


def test_planner_surfaces_invalid_preview_row_instead_of_dropping() -> None:
    mock_mod = MagicMock()
    mock_mod.preview_proxy_disable.return_value = MagicMock()
    module_name = "windows_network_toolkit.remediation.proxy_disable"
    snapshot = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = mock_mod
        plan = plan_proxy_drift_remediation(
            incident_id="regression-invalid-preview",
            signals={"evidence_tier": "FINAL_CAUSATION", "path_validated": True},
            dry_run=True,
        )
    finally:
        if snapshot is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = snapshot

    assert plan["dry_run"] is True
    assert plan["approval"]["can_execute"] is False
    assert len(plan["previews"]) == 1
    row = plan["previews"][0]
    assert row["type"] == "invalid_preview_row"
    assert row["reason"] == "non_dict_row:MagicMock"


def test_planner_order_after_mocked_module_does_not_crash_reports() -> None:
    """Simulate test-order pollution: planner invalid row + report generation still works."""
    mock_mod = MagicMock()
    mock_mod.preview_proxy_disable.return_value = MagicMock()
    module_name = "windows_network_toolkit.remediation.proxy_disable"
    snapshot = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = mock_mod
        plan = plan_proxy_drift_remediation(
            incident_id="order-pollution",
            signals={"evidence_tier": "FINAL_CAUSATION", "path_validated": True},
            dry_run=True,
        )
        text = generate_report(
            timeline=[],
            decision=plan["decision"],
            policy=plan["policy_gate"],
            remediation={"previews": plan["previews"], "rollback_plan": plan["rollback_plan"]},
            fmt="json",
        )
    finally:
        if snapshot is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = snapshot

    assert "invalid_preview_row" in text
    assert "MagicMock id=" not in text
