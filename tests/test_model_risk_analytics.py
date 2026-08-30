from __future__ import annotations

import pytest

from src.platform_core.model_risk.contracts import RiskFeatures
from src.platform_core.model_risk.scoring import deterministic_recurrence_score
from src.platform_core.model_risk.torch_model import RecurrenceRiskMLP, torch_available


def test_feature_vector_is_stable_and_bounded() -> None:
    features = RiskFeatures(
        proxy_enabled=True,
        listener_found=False,
        direct_probe_ok=True,
        proxy_probe_ok=False,
        proof_tier=2,
        failed_control_count=3,
        partial_control_count=1,
        recurrence_count=2,
        previous_restoration_verified=False,
        time_to_restore_seconds=7200,
    )
    vector = features.as_vector()
    assert len(vector) == 10
    assert all(-1.0 <= value <= 1.0 for value in vector)


def test_deterministic_score_preserves_governance_boundary() -> None:
    recommendation = deterministic_recurrence_score(
        "incident-001",
        RiskFeatures(
            proxy_enabled=True,
            listener_found=False,
            direct_probe_ok=True,
            proxy_probe_ok=False,
            proof_tier=1,
            failed_control_count=2,
            partial_control_count=1,
            recurrence_count=3,
            previous_restoration_verified=False,
        ),
        evidence_refs=["evidence-001"],
    )
    assert recommendation.review_priority == "HIGH"
    assert recommendation.execution_authority == "NONE"
    assert recommendation.human_review_required is True
    assert recommendation.risk_score <= 1.0
    assert "evidence-001" in recommendation.evidence_refs


def test_missing_pytorch_fails_with_install_instruction() -> None:
    if torch_available():
        pytest.skip("PyTorch optional dependency is installed in this environment")
    with pytest.raises(RuntimeError, match="\[ml\]"):
        RecurrenceRiskMLP()
