from __future__ import annotations

from platform_core.models import EndpointSnapshot, FailureEvent


def test_failure_event_roundtrip() -> None:
    fe = FailureEvent(
        event_id="evt-1",
        endpoint_id="ep-aaaa",
        category="dns",
        confidence=0.5,
        summary="fixture",
        recommended_action_key="reset_dns",
    )
    d = fe.model_dump()
    assert FailureEvent.model_validate(d).event_id == "evt-1"


def test_endpoint_snapshot_optional_blocks() -> None:
    snap = EndpointSnapshot(endpoint_id="ep-1")
    assert snap.browser_path_state == {}
