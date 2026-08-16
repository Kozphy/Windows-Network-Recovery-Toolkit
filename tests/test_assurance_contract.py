import pytest
from pydantic import ValidationError

from platform_core.assurance import AssuranceConclusion, ReviewDecision, SamplingPlan


def test_random_sampling_requires_seed_for_reproducibility():
    with pytest.raises(ValidationError):
        SamplingPlan(
            population_id="endpoints-2026-08",
            population_size=100,
            method="random",
            sample_size=10,
            rationale="Quarterly operating-effectiveness test",
        )


def test_sample_cannot_exceed_population():
    with pytest.raises(ValidationError):
        SamplingPlan(
            population_id="tiny-population",
            population_size=3,
            method="systematic",
            sample_size=4,
            rationale="Invalid sample",
        )


def test_effective_conclusion_cannot_hide_exceptions():
    with pytest.raises(ValidationError):
        AssuranceConclusion(
            control_id="NET-PROXY-001",
            operating_effectiveness="effective",
            confidence="high",
            basis="Automated reperformance completed.",
            scope="Windows endpoint proxy configuration",
            exception_ids=["EX-001"],
        )


def test_rejected_review_forces_inconclusive_conclusion():
    review = ReviewDecision(
        reviewer="reviewer@example",
        decision="reject",
        rationale="Evidence is incomplete.",
        reviewed_at="2026-08-16T18:00:00+08:00",
    )
    with pytest.raises(ValidationError):
        AssuranceConclusion(
            control_id="NET-PROXY-001",
            operating_effectiveness="effective_with_exceptions",
            confidence="moderate",
            basis="Draft automated conclusion.",
            scope="Windows endpoint proxy configuration",
            exception_ids=["EX-001"],
            review=review,
        )


def test_inconclusive_conclusion_accepts_more_evidence_review():
    conclusion = AssuranceConclusion(
        control_id="NET-PROXY-001",
        operating_effectiveness="inconclusive",
        confidence="low",
        basis="The population snapshot is incomplete.",
        scope="Windows endpoint proxy configuration",
        limitations=["12 endpoints did not return current evidence"],
        review=ReviewDecision(
            reviewer="reviewer@example",
            decision="needs_more_evidence",
            rationale="Complete the missing endpoint population before sign-off.",
            reviewed_at="2026-08-16T18:00:00+08:00",
        ),
    )
    assert conclusion.operating_effectiveness == "inconclusive"
