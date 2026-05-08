from __future__ import annotations

from platform_core.reasoning_engine import observation, run_reasoning
from platform_core.reasoning_models import Observation, ProofResult


def test_reasoning_models_are_replayable_dicts() -> None:
    obs = Observation(source="fixture", signal_name="dns_ok", value=True)
    assert obs.id.startswith("obs_")
    assert obs.evidence_level == "observed"

    run = run_reasoning([obs], proof_result=ProofResult(status="NOT_RUN"))
    dumped = run.model_dump(mode="json")
    assert dumped["raw_observations"][0]["signal_name"] == "dns_ok"
    assert dumped["policy_decision"]["outcome"] == "PREVIEW"
    assert dumped["version_metadata"]["reasoning_schema"] == "reasoning.v1"


def test_confidence_is_ordinal_not_probability_copy() -> None:
    run = run_reasoning(
        [
            observation("ping_ok"),
            observation("dns_ok"),
            observation("tcp443_ok"),
            observation("browser_https_failed"),
            observation("wininet_proxy_enabled"),
        ]
    )
    assert 0.0 <= run.policy_decision.confidence <= 1.0
    assert any("heuristic" in item.lower() for item in run.limitations)
