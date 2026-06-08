from __future__ import annotations

from platform_core.decision_platform.models import Evidence, PlatformDomain
from platform_core.decision_platform.reasoning import run_shared_reasoning


def test_shared_reasoning_maps_engine_output() -> None:
    evidence = [
        Evidence(
            evidence_id="e1",
            domain="security",
            label="High severity alert",
            weight=0.8,
            supports_decision=True,
        )
    ]
    specs = [
        {
            "decision_id": "a",
            "label": "Isolate",
            "base_benefit": 60.0,
            "base_risk": 30.0,
            "evidence_relevance": {"e1": 1.0},
        },
        {
            "decision_id": "b",
            "label": "Monitor",
            "base_benefit": 40.0,
            "base_risk": 10.0,
        },
    ]
    result = run_shared_reasoning(
        domain=PlatformDomain.SECURITY,
        observations=[],
        evidence=evidence,
        candidate_specs=specs,
    )
    assert result.decision.domain == "security"
    assert len(result.alternatives) == 2
    assert result.engine_digest == result.decision.content_digest
