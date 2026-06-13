"""Principle: correlation is not causation — listener/dead port ≠ malicious writer."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.principles.validator import validate_principles

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_cs1_dead_port_does_not_claim_malicious_writer() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    result = validate_principles(data)
    check = next(c for c in result.checks if c.principle_id == "correlation_not_causation")
    assert check.passed


def test_malware_overclaim_without_telemetry_fails() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    data["executive_summary"] = "This confirms malware on the endpoint."
    result = validate_principles(data)
    check = next(c for c in result.checks if c.principle_id == "correlation_not_causation")
    assert not check.passed


def test_malware_claim_allowed_with_sysmon_writer_proof() -> None:
    data = json.loads(CS1.read_text(encoding="utf-8"))
    data["writer_attribution"] = {
        "registry_writer_confirmed": True,
        "telemetry_sources": ["sysmon_e13"],
        "classification": "SUSPICIOUS_PROXY",
    }
    data["executive_summary"] = "Writer attribution supported by Sysmon E13."
    result = validate_principles(data)
    check = next(c for c in result.checks if c.principle_id == "correlation_not_causation")
    assert check.passed
