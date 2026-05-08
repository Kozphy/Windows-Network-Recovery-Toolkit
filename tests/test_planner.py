from __future__ import annotations

from pathlib import Path

from agent.classifier import classify_with_primary
from agent.collector import load_evidence_from_json
from agent.planner import plan

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_planner_dns_low_risk_no_confirmation() -> None:
    ev = load_evidence_from_json(FIXTURES / "dns_failure.json")
    primary, _ = classify_with_primary(ev)
    p = plan(primary, ev)
    assert len(p.steps) == 1
    assert "reset_dns.bat" in p.steps[0].script_relative_path
    assert p.steps[0].requires_confirmation is False


def test_planner_no_firewall_in_https_case() -> None:
    ev = load_evidence_from_json(FIXTURES / "https_failure.json")
    primary, _ = classify_with_primary(ev)
    p = plan(primary, ev)
    scripts = [s.script_relative_path for s in p.steps]
    assert not any("reset_firewall.bat" in s for s in scripts)


def test_planner_winsock_requires_confirmation() -> None:
    ev = load_evidence_from_json(FIXTURES / "tcp_failure.json")
    primary, _ = classify_with_primary(ev)
    p = plan(primary, ev)
    destructive = [s for s in p.steps if s.destructive]
    assert destructive
    assert all(s.requires_confirmation for s in destructive)
