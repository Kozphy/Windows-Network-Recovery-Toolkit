"""Tests for analytics-summary CLI and core summarizer."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.platform_core.analytics import build_analytics_summary, format_analytics_markdown
from windows_network_toolkit import cli
from windows_network_toolkit.safety import BLOCKED_ACTIONS

REPO = Path(__file__).resolve().parents[1]
SAMPLE_AUDIT = REPO / "tests" / "fixtures" / "analytics" / "audit_sample"
EMPTY_DIR = REPO / "tests" / "fixtures" / "analytics" / "empty_audit"


def _run(args: list[str]) -> tuple[int, str]:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(args)
    return rc, cap.getvalue()


@pytest.fixture(scope="module", autouse=True)
def _ensure_empty_audit_dir() -> None:
    EMPTY_DIR.mkdir(parents=True, exist_ok=True)


def test_empty_audit_directory_returns_zero_counts() -> None:
    payload = build_analytics_summary(EMPTY_DIR)
    assert payload["schema_version"] == "analytics_summary.v1"
    assert payload["summary"]["total_audit_records"] == 0
    assert payload["counts"]["remediation_preview_count"] == 0
    assert payload["limitations"]


def test_sample_audit_classification_counts() -> None:
    payload = build_analytics_summary(SAMPLE_AUDIT)
    by_class = payload["counts"]["incidents_by_classification"]
    assert by_class.get("DEAD_PROXY_CONFIG") == 2
    assert by_class.get("UNKNOWN_LOCAL_PROXY") == 1
    assert payload["counts"]["remediation_preview_count"] >= 1
    assert payload["counts"]["destructive_action_blocked_count"] >= 1


def test_malformed_jsonl_reported_in_limitations() -> None:
    payload = build_analytics_summary(SAMPLE_AUDIT)
    joined = " ".join(payload["limitations"]).lower()
    assert "malformed" in joined or "skipped" in joined


def test_markdown_output_sections() -> None:
    payload = build_analytics_summary(SAMPLE_AUDIT)
    md = format_analytics_markdown(payload)
    assert "# Endpoint Risk Analytics Summary" in md
    assert "## Limitations" in md
    assert "DEAD_PROXY_CONFIG" in md


def test_cli_json_cross_platform() -> None:
    rc, out = _run([
        "analytics-summary",
        "--legacy-platform",
        "--audit-dir",
        str(SAMPLE_AUDIT),
        "--format",
        "json",
    ])
    assert rc == 0
    payload = json.loads(out)
    assert payload["schema_version"] == "analytics_summary.v1"
    assert "counts" in payload


def test_cli_markdown_cross_platform() -> None:
    rc, out = _run([
        "analytics-summary",
        "--legacy-platform",
        "--audit-dir",
        str(EMPTY_DIR),
        "--format",
        "markdown",
    ])
    assert rc == 0
    assert "Endpoint Risk Analytics Summary" in out


def test_no_destructive_action_performed() -> None:
    """Summarizer is read-only; blocked actions remain policy-blocked constants only."""
    before = set(BLOCKED_ACTIONS)
    _run(["analytics-summary", "--legacy-platform", "--audit-dir", str(SAMPLE_AUDIT)])
    after = set(BLOCKED_ACTIONS)
    assert before == after
