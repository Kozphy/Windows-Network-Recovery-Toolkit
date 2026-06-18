"""Business impact estimation tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.risk.business_impact import estimate_business_impact

CASE_1 = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "case_studies" / "case_1_dead_wininet_proxy.json"


def test_ordinal_scores_not_probability() -> None:
    est = estimate_business_impact(classification="DEAD_PROXY_CONFIG")
    assert est.confidence_type == "ordinal_not_probability"
    assert 1 <= est.total_business_impact_score <= 5


def test_fixture_context() -> None:
    fixture = json.loads(CASE_1.read_text(encoding="utf-8"))
    est = estimate_business_impact(fixture=fixture)
    assert est.limitations
    assert est.operational_impact_score >= 1


def test_suspicious_proxy_includes_triage_limitation() -> None:
    est = estimate_business_impact(classification="SUSPICIOUS_PROXY")
    assert any("triage" in lim.lower() or "malware" in lim.lower() for lim in est.limitations)
