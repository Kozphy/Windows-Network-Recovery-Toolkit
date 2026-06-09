"""Policy-as-code YAML validation and proxy-policy integration."""

from __future__ import annotations

from pathlib import Path

from platform_core.policy_as_code import (
    load_policy_document,
    resolve_policy_gate,
    validate_policy_document,
)

REPO = Path(__file__).resolve().parents[1]
POLICIES = REPO / "config" / "policies"


def test_validate_default_policy() -> None:
    assert validate_policy_document(POLICIES / "default.yaml") == []


def test_validate_strict_enterprise() -> None:
    assert validate_policy_document(POLICIES / "strict_enterprise.yaml") == []


def test_validate_developer_workstation() -> None:
    assert validate_policy_document(POLICIES / "developer_workstation.yaml") == []


def test_resolve_gate_known_dev() -> None:
    doc = load_policy_document(POLICIES / "developer_workstation.yaml")
    assert resolve_policy_gate(doc, classification="known_dev_tool") == "allow"


def test_resolve_gate_external_strict() -> None:
    doc = load_policy_document(POLICIES / "strict_enterprise.yaml")
    assert resolve_policy_gate(doc, external_proxy=True) == "block"


def test_cli_policy_validate() -> None:
    import argparse

    from src.production_handlers import cmd_policy_validate

    code = cmd_policy_validate(
        argparse.Namespace(policy_path=str(POLICIES / "default.yaml"))
    )
    assert code == 0


def test_proxy_policy_with_yaml_fixture() -> None:
    import argparse

    from src.command_handlers import cmd_proxy_policy

    fixture = REPO / "tests/fixtures/proxy_incidents/cursor_known_proxy.json"
    code = cmd_proxy_policy(
        argparse.Namespace(
            policy_fixture=str(fixture),
            policy_format="json",
            policy_yaml=str(POLICIES / "default.yaml"),
            emit_json=False,
            repo_root=REPO,
        )
    )
    assert code == 0
