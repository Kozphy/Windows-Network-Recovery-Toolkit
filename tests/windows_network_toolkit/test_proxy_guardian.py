"""Tests for dead-proxy guardian (fixture-safe)."""

from __future__ import annotations

from unittest.mock import patch

from windows_network_toolkit.proxy_guardian import run_proxy_guardian_once


def test_guardian_skips_when_no_dead_proxy() -> None:
    with patch(
        "windows_network_toolkit.proxy_guardian.run_proxy_status",
        return_value={"classification": "NO_PROXY", "timestamp_utc": "t"},
    ):
        out = run_proxy_guardian_once(dry_run=False)
    assert out["action_taken"] == "none"
    assert "remediation" not in out


def test_guardian_dry_run_dead_proxy() -> None:
    with (
        patch(
            "windows_network_toolkit.proxy_guardian.run_proxy_status",
            return_value={
                "classification": "DEAD_PROXY_CONFIG",
                "timestamp_utc": "t",
                "localhost_port": 62285,
            },
        ),
        patch(
            "windows_network_toolkit.proxy_guardian.run_proxy_disable",
            return_value={"action_allowed": True, "dry_run": True},
        ) as disable,
    ):
        out = run_proxy_guardian_once(dry_run=True)
    disable.assert_called_once_with(dry_run=True, confirm="")
    assert out["action_taken"] == "would_remediate"


def test_guardian_skips_active_localhost_proxy() -> None:
    """Active dev proxy with listener must not be classified as DEAD_PROXY_CONFIG."""
    with patch(
        "windows_network_toolkit.proxy_guardian.run_proxy_status",
        return_value={
            "classification": "KNOWN_DEV_TOOL",
            "timestamp_utc": "t",
            "localhost_port": 62285,
        },
    ):
        out = run_proxy_guardian_once(dry_run=False)
    assert out["action_taken"] == "none"
    assert "remediation" not in out


def test_guardian_applies_dead_proxy() -> None:
    with (
        patch(
            "windows_network_toolkit.proxy_guardian.run_proxy_status",
            return_value={
                "classification": "DEAD_PROXY_CONFIG",
                "timestamp_utc": "t",
                "localhost_port": 62285,
            },
        ),
        patch(
            "windows_network_toolkit.proxy_guardian.run_proxy_disable",
            return_value={"action_allowed": True, "dry_run": False},
        ) as disable,
    ):
        out = run_proxy_guardian_once(dry_run=False)
    disable.assert_called_once_with(dry_run=False, confirm="DISABLE_WININET_PROXY")
    assert out["action_taken"] == "remediated"
