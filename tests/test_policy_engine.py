from __future__ import annotations

import pytest

from platform_core.models import FailureEvent
from platform_core.policy import (
    ACTION_REGISTRY,
    build_preview,
    evaluate_action,
    require_typed_confirmation,
    validate_confirmation_phrase,
)


@pytest.fixture()
def dns_event() -> FailureEvent:
    return FailureEvent(
        event_id="e1",
        endpoint_id="ep1",
        category="dns",
        confidence=0.8,
        summary="fixture",
        recommended_action_key="reset_dns",
    )


def test_firewall_reset_forbidden_from_api() -> None:
    d = evaluate_action("reset_firewall", "api")
    assert not d.allowed


def test_low_medium_requires_confirmation_via_registry() -> None:
    phrase = require_typed_confirmation("reset_dns")
    assert phrase == "RUN_DNS_RESET"
    assert validate_confirmation_phrase("reset_dns", "RUN_DNS_RESET")
    assert not validate_confirmation_phrase("reset_dns", "wrong")


def test_read_only_allowed() -> None:
    d = evaluate_action("inspect_proxy", "api")
    assert d.allowed


def test_arbitrary_command_forbidden() -> None:
    d = evaluate_action("arbitrary_command", "api")
    assert not d.allowed


def test_proxy_reset_preview_allowed_but_execute_requires_confirmation(dns_event: FailureEvent) -> None:
    p = build_preview(dns_event, "reset_proxy", requested_surface="api")
    assert p.proposed_action == "reset_proxy"
    assert p.allowed_by_policy
    assert p.requires_typed_confirmation
    assert p.confirmation_phrase == ACTION_REGISTRY["reset_proxy"]["phrase"]


def test_low_risk_requires_typed_confirmation_phrase() -> None:
    assert require_typed_confirmation("reset_dns") == "RUN_DNS_RESET"


def test_winsock_preview_medium_risk_confirmation(dns_event: FailureEvent) -> None:
    p = build_preview(dns_event, "winsock_reset", requested_surface="api")
    assert p.risk_level == "medium"
    assert "RUN_WINSOCK_RESET" == p.confirmation_phrase

    p_alias = build_preview(dns_event, "reset_winsock", requested_surface="api")
    assert p_alias.confirmation_phrase == "RUN_WINSOCK_RESET"

