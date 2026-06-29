"""Cross-platform evidence normalization tests (fixture-driven)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.evidence_collection.normalize import (
    WINDOWS_ONLY_SIGNALS,
    assert_honest_platform_labels,
    normalize_evidence_bundle,
    normalize_observation_row,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "cross_platform"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("fixture_name", "os_family", "level"),
    [
        ("windows_evidence.json", "windows", "FULL"),
        ("linux_evidence.json", "linux", "PARTIAL"),
        ("darwin_evidence.json", "darwin", "PARTIAL"),
    ],
)
def test_fixture_normalization_shape(
    fixture_name: str,
    os_family: str,
    level: str,
) -> None:
    raw = _load_fixture(fixture_name)
    normalized = normalize_evidence_bundle(raw)
    assert normalized["os_family"] == os_family
    assert normalized["platform_support_level"] == level
    assert normalized["observations"]
    for row in normalized["observations"]:
        assert "signal_name" in row
        assert "value" in row
        assert row["source"]
        assert row["evidence_level"] == "observation"
        assert isinstance(row["limitations"], list)
    ok, errors = assert_honest_platform_labels(normalized)
    assert ok is True, errors


def test_linux_and_darwin_fixtures_exclude_windows_only_signals() -> None:
    for fixture_name in ("linux_evidence.json", "darwin_evidence.json"):
        normalized = normalize_evidence_bundle(_load_fixture(fixture_name))
        signals = {row["signal_name"] for row in normalized["observations"]}
        assert not signals.intersection(WINDOWS_ONLY_SIGNALS), fixture_name


def test_windows_fixture_may_include_wininet_signals() -> None:
    normalized = normalize_evidence_bundle(_load_fixture("windows_evidence.json"))
    signals = {row["signal_name"] for row in normalized["observations"]}
    assert "proxy_enable" in signals
    assert "winhttp_proxy_state" in signals


def test_normalize_observation_row_defaults() -> None:
    row = normalize_observation_row({"signal_name": "dns_resolves", "value": True, "source": "test"})
    assert row["evidence_level"] == "observation"
    assert row["limitations"] == []


def test_non_windows_limitations_required_in_normalize() -> None:
    bare = {
        "os_family": "linux",
        "platform_support_level": "PARTIAL",
        "collector_id": "test",
        "observations": [],
        "limitations": [],
    }
    normalized = normalize_evidence_bundle(bare)
    assert normalized["limitations"]
