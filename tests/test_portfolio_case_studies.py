"""Portfolio case-study integration tests — fixture-safe, no host mutation."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from windows_network_toolkit import cli
from windows_network_toolkit.safety import BLOCKED_ACTIONS, is_blocked_action

REPO_ROOT = Path(__file__).resolve().parents[1]
ENERT = REPO_ROOT / "tests" / "fixtures" / "enert"
DOCS = REPO_ROOT / "docs"


def _run_cli(args: list[str]) -> tuple[int, dict]:
    cap = StringIO()
    with patch("sys.stdout", cap):
        rc = cli.main(args)
    return rc, json.loads(cap.getvalue())


@pytest.mark.parametrize(
    "fixture,expected_classification",
    [
        ("dead_proxy_59081.json", "DEAD_PROXY_CONFIG"),
        ("unknown_localhost_proxy.json", "UNKNOWN_LOCAL_PROXY"),
    ],
)
def test_case_study_fixtures_classify(fixture: str, expected_classification: str) -> None:
    if fixture == "dead_proxy_59081.json":
        rc, payload = _run_cli(["proxy-status", "--fixture", fixture])
        assert rc == 0
        assert payload["classification"] == expected_classification
    else:
        rc, payload = _run_cli(["proxy-writer-attribution", "--fixture", fixture])
        assert rc == 0
        assert payload["classification"] == expected_classification


def test_case_study_1_proof_envelope_supported() -> None:
    rc, payload = _run_cli(["diagnose", "--proof", "--fixture", "dead_proxy_59081.json"])
    assert rc == 0
    assert payload["conclusion"]["status"] == "supported"
    limitations = " ".join(payload.get("limitations", [])).lower()
    assert "malware" in limitations or "mitm" in limitations


def test_case_study_1_dead_proxy_has_no_listener() -> None:
    rc, payload = _run_cli(["proxy-owner", "--fixture", "dead_proxy_59081.json"])
    assert rc == 0
    assert payload["listener_found"] is False


def test_case_study_2_unknown_listener_low_confidence() -> None:
    rc, payload = _run_cli(["proxy-writer-attribution", "--fixture", "unknown_localhost_proxy.json"])
    assert rc == 0
    assert payload["registry_writer_confirmed"] is False
    assert payload["confidence_score"] < 0.5


def test_proxy_disable_defaults_to_dry_run(capsys) -> None:
    with patch("windows_network_toolkit.proxy_remediation.platform.system", return_value="Linux"):
        rc = cli.main(["proxy-disable"])
        out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload.get("unsupported_platform") or payload.get("dry_run") is True
    assert payload.get("no_changes_made") is True or payload.get("unsupported_platform")


def test_destructive_actions_blocked() -> None:
    for action in BLOCKED_ACTIONS:
        assert is_blocked_action(action)


def test_portfolio_documentation_files_exist() -> None:
    required = [
        "case-study-1-proxy-drift.md",
        "case-study-2-unknown-local-proxy-listener.md",
        "case-study-3-endpoint-reliability-decision-engine.md",
        "demo-video-script.md",
        "consulting-report.md",
        "portfolio-summary.md",
        "screenshots/README.md",
    ]
    for name in required:
        assert (DOCS / name).is_file(), f"missing portfolio doc: {name}"


def test_golden_fixture_file_on_disk() -> None:
    fixture = ENERT / "dead_proxy_59081.json"
    assert fixture.is_file()
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data["classification"]["primary_classification"] == "DEAD_PROXY_CONFIG"


def test_proxy_drift_replay_fixture_readable() -> None:
    replay = REPO_ROOT / "windows_network_toolkit" / "examples" / "proxy_drift_incident.jsonl"
    lines = replay.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3
    events = [json.loads(line) for line in lines]
    signals = {e["signal"] for e in events}
    assert "browser_https_failed" in signals
    assert "direct_path_success" in signals
