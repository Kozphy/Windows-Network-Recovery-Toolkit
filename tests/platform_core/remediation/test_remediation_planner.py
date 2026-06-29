"""Policy-gated remediation preview."""

from __future__ import annotations

from src.platform_core.policy.approval import generate_approval_token, validate_approval_token
from src.platform_core.remediation.planner import plan_proxy_drift_remediation
from src.platform_core.remediation.rollback import build_rollback_plan


def test_remediation_dry_run_default() -> None:
    plan = plan_proxy_drift_remediation(
        incident_id="inc-1",
        signals={"wininet_proxy_enabled": True, "evidence_tier": "OBSERVED_ONLY"},
        dry_run=True,
    )
    assert plan["dry_run"] is True
    assert plan["approval"]["can_execute"] is False
    assert plan["previews"]


def test_policy_blocks_weak_proof() -> None:
    plan = plan_proxy_drift_remediation(
        incident_id="inc-2",
        signals={"evidence_tier": "OBSERVED_ONLY"},
        dry_run=True,
    )
    assert plan["policy_gate"]["outcome"] in {"PREVIEW_ONLY", "BLOCK", "REQUIRE_HUMAN_APPROVAL"}


def test_rollback_plan_required_fields() -> None:
    rb = build_rollback_plan(action_id="disable_wininet_proxy", prior_proxy_server="127.0.0.1:8080")
    assert rb["dry_run"] is True
    assert rb["steps"]
    assert any(s["operation"] == "registry_restore" for s in rb["steps"])


def test_approval_token_gate() -> None:
    token = generate_approval_token()
    assert validate_approval_token(token, token) is True
    assert validate_approval_token("wrong", token) is False
    plan = plan_proxy_drift_remediation(
        incident_id="inc-3",
        signals={"evidence_tier": "FINAL_CAUSATION", "path_validated": True},
        expected_token=token,
        confirmation_token=token,
        dry_run=False,
    )
    assert plan["approval"]["approved"] is True


def test_invalid_preview_row_when_module_returns_non_dict() -> None:
    import sys
    from unittest.mock import MagicMock

    module_name = "windows_network_toolkit.remediation.proxy_disable"
    mock_mod = MagicMock()
    mock_mod.preview_proxy_disable.return_value = MagicMock()
    snapshot = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = mock_mod
        plan = plan_proxy_drift_remediation(
            incident_id="inc-invalid-preview",
            signals={"evidence_tier": "FINAL_CAUSATION", "path_validated": True},
            dry_run=True,
        )
    finally:
        if snapshot is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = snapshot

    assert plan["previews"][0]["type"] == "invalid_preview_row"
    assert plan["previews"][0]["reason"] == "non_dict_row:MagicMock"
    assert plan["approval"]["can_execute"] is False
