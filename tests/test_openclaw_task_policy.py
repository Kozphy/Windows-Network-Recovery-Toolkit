"""OpenClaw task-policy safety contract — reject prohibited automation requests."""

from __future__ import annotations

import pytest

from src.platform_core.openclaw import (
    evaluate_task_policy,
    expected_branch_name,
    task_from_mapping,
    validate_changed_paths,
)


def _valid_task(**overrides: object) -> dict:
    base: dict = {
        "task_id": "123",
        "title": "Add proxy evidence export validation",
        "description": "Clear acceptance criteria: validate export schema against fixtures.",
        "approved": True,
        "risk_level": "low",
        "allowed_paths": ["windows_network_toolkit/", "tests/", "docs/"],
        "forbidden_paths": [
            ".github/workflows/deploy.yml",
            ".env",
            "platform_data/",
            ".audit/",
        ],
    }
    base.update(overrides)
    return base


def test_valid_low_risk_task_is_allowed() -> None:
    task = task_from_mapping(_valid_task())
    result = evaluate_task_policy(task)
    assert result.allowed is True
    assert result.decision == "ALLOW"
    assert expected_branch_name(task).startswith("agent/openclaw/123-")


def test_valid_medium_risk_docs_task_is_allowed() -> None:
    task = task_from_mapping(
        _valid_task(
            risk_level="medium",
            title="Clarify dry-run docs",
            description="Update docs/openclaw-coding-agent.md with emergency stop steps.",
            allowed_paths=["docs/"],
        )
    )
    assert evaluate_task_policy(task).allowed is True


def test_unapproved_task_is_blocked() -> None:
    task = task_from_mapping(_valid_task(approved=False))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "not_approved" in result.reasons


def test_empty_acceptance_criteria_blocked() -> None:
    task = task_from_mapping(_valid_task(description="   "))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "empty_acceptance_criteria" in result.reasons


@pytest.mark.parametrize("risk", ["high", "critical"])
def test_high_and_critical_risk_require_manual_execution(risk: str) -> None:
    task = task_from_mapping(_valid_task(risk_level=risk))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "risk_requires_manual_execution" in result.reasons


@pytest.mark.parametrize(
    "branch",
    [
        "main",
        "master",
        "Multi_Domain_Decision_Platform",
    ],
)
def test_default_branch_modification_blocked(branch: str) -> None:
    task = task_from_mapping(_valid_task(requested_branch=branch))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "default_branch_forbidden" in result.reasons


def test_non_agent_prefix_branch_blocked() -> None:
    task = task_from_mapping(_valid_task(requested_branch="feature/openclaw-123"))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "branch_must_use_agent_openclaw_prefix" in result.reasons


def test_env_path_in_allowlist_blocked() -> None:
    task = task_from_mapping(_valid_task(allowed_paths=[".env", "docs/"]))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert any(r.startswith("forbidden_path_requested:") for r in result.reasons)


def test_deploy_workflow_path_in_allowlist_blocked() -> None:
    task = task_from_mapping(
        _valid_task(allowed_paths=[".github/workflows/deploy.yml", "docs/"])
    )
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert any("deploy.yml" in r for r in result.reasons)


@pytest.mark.parametrize(
    "phrase",
    [
        "perform live registry mutation on WinINET",
        "run a firewall reset on the endpoint",
        "adapter disable for the Wi-Fi NIC",
        "process kill of the proxy helper",
        "access .env and read secrets from the host",
        "enable auto-merge on the pull request",
        "merge pull request without review",
        "deploy the application to production",
        "collect api token and credential material",
    ],
)
def test_forbidden_action_phrases_blocked(phrase: str) -> None:
    task = task_from_mapping(_valid_task(description=f"Acceptance: {phrase}"))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert any(r.startswith("forbidden_action:") for r in result.reasons)


def test_changed_paths_block_env_and_deploy() -> None:
    task = task_from_mapping(_valid_task())
    result = validate_changed_paths(
        [".env", "docs/readme-note.md"],
        task,
        max_files=20,
        max_changed_lines=1500,
        changed_line_count=10,
    )
    assert result.allowed is False
    assert any("prohibited_file_modified:.env" in r for r in result.reasons)


def test_changed_paths_size_limits() -> None:
    task = task_from_mapping(_valid_task())
    files = [f"docs/file_{i}.md" for i in range(25)]
    result = validate_changed_paths(
        files,
        task,
        max_files=20,
        max_changed_lines=100,
        changed_line_count=5000,
    )
    assert result.allowed is False
    assert any(r.startswith("too_many_files:") for r in result.reasons)
    assert any(r.startswith("too_many_lines:") for r in result.reasons)


def test_changed_paths_outside_allowlist_blocked() -> None:
    task = task_from_mapping(_valid_task(allowed_paths=["docs/"]))
    result = validate_changed_paths(
        ["windows_network_toolkit/cli.py"],
        task,
        max_files=20,
    )
    assert result.allowed is False
    assert any(r.startswith("path_outside_allowlist:") for r in result.reasons)


def test_github_issue_labels_require_agent_ready() -> None:
    task = task_from_mapping(_valid_task(labels=["bug"]))
    result = evaluate_task_policy(task)
    assert result.allowed is False
    assert "missing_agent_ready_label" in result.reasons


def test_github_issue_with_agent_ready_allowed() -> None:
    task = task_from_mapping(_valid_task(labels=["agent-ready"]))
    assert evaluate_task_policy(task).allowed is True
