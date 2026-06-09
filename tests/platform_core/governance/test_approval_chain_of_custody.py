"""Approval chain of custody."""

from __future__ import annotations

from src.platform_core.policy.approval import generate_approval_token, validate_approval_token


def test_approval_token_roundtrip() -> None:
    token = generate_approval_token()
    assert validate_approval_token(token, token) is True
    assert validate_approval_token("wrong", token) is False
