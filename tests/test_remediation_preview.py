from __future__ import annotations

from platform_core.models import FailureEvent
from platform_core.policy import build_preview


def test_preview_includes_rollack_copy() -> None:
    fe = FailureEvent(
        event_id="e-p",
        endpoint_id="ep-p",
        category="proxy",
        confidence=0.7,
        summary="fixture",
        recommended_action_key="reset_proxy",
    )
    prev = build_preview(fe, "reset_proxy")
    assert "rollback" in (prev.rollback_plan or "").lower() or prev.rollback_plan
    assert prev.rollback_preview is not None
    assert prev.rollback_preview.dry_run is True
