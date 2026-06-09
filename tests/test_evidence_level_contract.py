"""Evidence level upgrade contract — correlation cannot become proof without telemetry."""

from __future__ import annotations

import pytest

from platform_core.evidence_model import (
    can_upgrade_evidence,
    resolve_evidence_level,
)


def test_listener_only_stays_correlated() -> None:
    level = resolve_evidence_level({"registry_changed": True, "listener_correlation": True})
    assert level == "CORRELATED"
    assert not can_upgrade_evidence(
        "CORRELATED",
        "PROVEN_REGISTRY_WRITER",
        has_listener_correlation_only=True,
    )


def test_no_sysmon_no_proven_writer() -> None:
    assert not can_upgrade_evidence("CORRELATED", "PROVEN_REGISTRY_WRITER", has_writer_telemetry=False)


def test_sysmon_allows_proven_writer() -> None:
    level = resolve_evidence_level({"registry_changed": True, "sysmon_event_13": True, "writer_telemetry": True})
    assert level == "PROVEN_REGISTRY_WRITER"


def test_final_causation_requires_writer_and_port_or_network() -> None:
    level = resolve_evidence_level(
        {
            "sysmon_event_13": True,
            "writer_telemetry": True,
            "port_owner_match": True,
            "browser_path_failed": True,
            "network_impact_proof": True,
        }
    )
    assert level == "FINAL_CAUSATION"
    assert not can_upgrade_evidence(
        "CORRELATED",
        "FINAL_CAUSATION",
        has_writer_telemetry=False,
        has_port_owner_match=True,
    )


@pytest.mark.parametrize("fixture", ["healthy", "proxy-drift", "final-causation", "suspicious-external"])
def test_demo_fixtures_match_expected(fixture: str) -> None:
    from src.demo_handlers import run_demo_scenario
    from pathlib import Path

    report = run_demo_scenario(fixture, repo_root=Path(__file__).resolve().parents[1])
    assert report["evidence_level"] == report["expected_evidence_level"]
    assert (report["policy"] or {}).get("decision") == report["expected_policy"]
