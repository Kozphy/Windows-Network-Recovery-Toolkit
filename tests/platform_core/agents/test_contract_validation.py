"""Agent contract validation tests."""

from __future__ import annotations

from src.platform_core.agents.contracts import (
    ClassificationAgentOutput,
    EvidenceAgentOutput,
    RiskAssessmentAgentOutput,
)
from src.platform_core.agents.orchestrator import run_deterministic_orchestration


def test_evidence_contract_validates():
    out = EvidenceAgentOutput(
        event_id="e1",
        endpoint_id="ep-1",
        evidence_type="proxy_state",
        raw_snapshot={"wininet_proxy_enabled": True},
    )
    assert out.endpoint_id == "ep-1"


def test_orchestrator_returns_contract_bundle():
    fixture = {
        "proxy_state": {
            "wininet_proxy_enabled": True,
            "wininet_proxy_server": "127.0.0.1:59081",
            "winhttp_direct_access": True,
            "localhost_port": 59081,
        },
        "endpoint_id": "ep-orch-1",
    }
    bundle = run_deterministic_orchestration(fixture)
    assert "classification" in bundle
    cls = ClassificationAgentOutput.model_validate(bundle["classification"])
    assert cls.primary_classification
    risk = RiskAssessmentAgentOutput.model_validate(bundle["risk"])
    assert risk.risk_score <= 100
