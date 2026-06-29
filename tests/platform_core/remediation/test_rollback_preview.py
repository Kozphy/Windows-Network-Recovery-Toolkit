"""Preview-first rollback strategy — no live mutation tests."""

from __future__ import annotations

import json
from pathlib import Path

from platform_core.models import FailureEvent
from platform_core.policy import build_preview
from src.platform_core.policy.approval import generate_approval_token
from src.platform_core.remediation.planner import plan_proxy_drift_remediation
from src.platform_core.remediation.rollback import (
    ROLLBACK_CONFIRMATION_PHRASE,
    ROLLBACK_LIMITATIONS,
    append_rollback_audit_record,
    attempt_rollback_execute,
    build_rollback_preview_package,
    build_rollback_audit_record,
    can_execute_rollback,
    capture_pre_change_snapshot,
)


def _sample_package(*, dry_run: bool = True, token: str = "") -> dict:
    token = token or generate_approval_token()
    snapshot = capture_pre_change_snapshot(
        endpoint_id="ep-1",
        incident_id="inc-1",
        proxy_enable=1,
        proxy_server="127.0.0.1:8080",
    )
    from src.platform_core.remediation.rollback import build_proposed_mutation_preview

    mutation = build_proposed_mutation_preview(action_id="disable_wininet_proxy", endpoint_id="ep-1")
    return build_rollback_preview_package(
        endpoint_id="ep-1",
        incident_id="inc-1",
        action_id="disable_wininet_proxy",
        pre_change_snapshot=snapshot,
        proposed_mutation=mutation,
        dry_run=dry_run,
        approval_token=token,
    )


def test_rollback_preview_package_has_six_model_parts() -> None:
    pkg = _sample_package()
    assert pkg["pre_change_snapshot"]["snapshot_id"]
    assert pkg["proposed_mutation_preview"]["dry_run"] is True
    assert pkg["human_approval_token"]["required"] is True
    assert pkg["reversible_action_record"]["reversible"] is True
    assert pkg["rollback_preview"]["steps"]
    assert pkg["rollback_audit_record"]["event_kind"] == "rollback_preview_generated"
    assert pkg["can_execute_rollback"] is False
    assert pkg["limitations"] == ROLLBACK_LIMITATIONS


def test_rollback_preview_limitations_are_explicit() -> None:
    pkg = _sample_package()
    assert any("not a guarantee" in lim.lower() for lim in pkg["limitations"])
    assert any("preview" in lim.lower() for lim in pkg["limitations"])


def test_remediation_preview_includes_structured_rollback_preview() -> None:
    fe = FailureEvent(
        event_id="e-rb",
        endpoint_id="ep-rb",
        category="proxy",
        confidence=0.7,
        summary="fixture",
        recommended_action_key="reset_proxy",
    )
    prev = build_preview(fe, "reset_proxy")
    assert prev.rollback_preview is not None
    assert prev.rollback_preview.rollback_preview_id
    assert prev.rollback_preview.pre_change_snapshot
    assert prev.rollback_preview.rollback_steps
    assert prev.rollback_preview.dry_run is True


def test_planner_includes_rollback_preview_package() -> None:
    plan = plan_proxy_drift_remediation(
        incident_id="inc-planner",
        signals={"evidence_tier": "OBSERVED_ONLY", "endpoint_id": "ep-planner"},
        dry_run=True,
    )
    rb = plan["rollback_preview"]
    assert rb["rollback_audit_record"]["dry_run"] is True
    assert rb["rollback_preview"]["dry_run"] is True
    assert plan["rollback_plan"]["steps"]


def test_rollback_does_not_execute_without_confirmation() -> None:
    token = generate_approval_token()
    pkg = _sample_package(dry_run=True, token=token)
    result = attempt_rollback_execute(pkg, dry_run=True)
    assert result["executed"] is False
    assert result["can_execute"] is False
    assert "dry_run" in result["reason"]


def test_rollback_does_not_execute_with_token_but_no_typed_phrase() -> None:
    token = generate_approval_token()
    pkg = _sample_package(dry_run=False, token=token)
    result = attempt_rollback_execute(
        pkg,
        confirmation_token=token,
        typed_confirmation="",
        dry_run=False,
    )
    assert result["executed"] is False
    assert result["can_execute"] is False
    assert result["reason"] == "typed_confirmation_required"


def test_rollback_executor_disabled_even_with_full_confirmation() -> None:
    token = generate_approval_token()
    pkg = _sample_package(dry_run=False, token=token)
    can, reason = can_execute_rollback(
        dry_run=False,
        confirmation_token=token,
        expected_token=token,
        typed_confirmation=ROLLBACK_CONFIRMATION_PHRASE,
    )
    assert can is False
    assert reason == "live_rollback_executor_disabled_preview_only"

    result = attempt_rollback_execute(
        pkg,
        confirmation_token=token,
        typed_confirmation=ROLLBACK_CONFIRMATION_PHRASE,
        dry_run=False,
    )
    assert result["executed"] is False
    assert result["can_execute"] is False


def test_append_rollback_audit_record_writes_jsonl(tmp_path: Path) -> None:
    record = build_rollback_audit_record(
        rollback_preview_id="rbprev-test",
        endpoint_id="ep-audit",
        incident_id="inc-audit",
        action_id="disable_wininet_proxy",
        event_kind="rollback_preview_generated",
    )
    path = append_rollback_audit_record(record, path=tmp_path / "rollback_audit.jsonl")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["rollback_preview_id"] == "rbprev-test"
    assert row["executed"] is False
    assert row["read_only"] is True
