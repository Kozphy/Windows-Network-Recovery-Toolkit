"""Incident review generator tests — deterministic case studies."""

from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.incident_review import (
    generate_incident_review,
    list_case_study_ids,
    render_incident_review_markdown,
)


def test_list_case_studies() -> None:
    ids = list_case_study_ids()
    assert "001_proxy_drift_cursor_node" in ids
    assert len(ids) >= 3


def test_generate_case_study_001() -> None:
    review = generate_incident_review("001_proxy_drift_cursor_node")
    assert review.incident_id == "001_proxy_drift_cursor_node"
    assert review.policy_gate.lower() in ("observe", "preview", "allow")
    assert review.timeline
    md = render_incident_review_markdown(review)
    assert "Incident review" in md
    assert "Epistemic notes" in md


def test_generate_case_study_002_proof_unavailable() -> None:
    review = generate_incident_review("002_browser_fails_ping_ok")
    assert review.proof_status == "unavailable"
    assert "browser" in review.root_cause.lower() or "proxy" in review.root_cause.lower()


def test_unknown_incident_raises() -> None:
    with pytest.raises(FileNotFoundError):
        generate_incident_review("does-not-exist-xyz")


def test_cli_incident_review_markdown() -> None:
    import argparse

    from src.production_handlers import cmd_incident_review

    code = cmd_incident_review(
        argparse.Namespace(
            incident_id="003_remediation_not_sticky",
            review_format="markdown",
            repo_root=str(Path(__file__).resolve().parents[1]),
        )
    )
    assert code == 0
