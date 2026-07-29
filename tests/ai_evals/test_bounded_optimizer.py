from __future__ import annotations

from platform_core.ai_evals.candidate_generator import generate_neighbors
from platform_core.ai_evals.failure_taxonomy import EvalPolicyGate
from platform_core.ai_evals.optimization_schemas import OptimizationCandidate
from platform_core.ai_evals.optimizer import optimize_candidate


def _baseline() -> OptimizationCandidate:
    return OptimizationCandidate(
        candidate_id="baseline",
        parameters={
            "retrieval_top_k": 5,
            "max_response_length": 500,
            "unsupported_claim_threshold": 0.25,
            "require_citations": True,
        },
        generation_reason="Initial governed baseline.",
        iteration=0,
    )


def test_generate_neighbors_changes_one_parameter_at_a_time() -> None:
    baseline = _baseline()
    neighbors = generate_neighbors(baseline)

    assert len(neighbors) == 6
    for candidate in neighbors:
        changed = {
            key
            for key, value in candidate.parameters.items()
            if baseline.parameters.get(key) != value
        }
        assert len(changed) == 1
        assert candidate.parent_id == baseline.candidate_id
        assert candidate.iteration == 1


def test_blocked_candidate_cannot_win_even_with_highest_score() -> None:
    baseline = _baseline()

    def evaluator(candidate: OptimizationCandidate) -> tuple[float, EvalPolicyGate]:
        if candidate.candidate_id == "baseline":
            return 0.50, EvalPolicyGate.ALLOW
        if candidate.parameters["retrieval_top_k"] == 6:
            return 0.99, EvalPolicyGate.BLOCK
        return 0.60, EvalPolicyGate.ALLOW

    run = optimize_candidate(
        baseline,
        evaluator,
        max_iterations=1,
        minimum_improvement=0.01,
        require_human_review=False,
    )

    assert run.selected_score == 0.60
    assert run.selected.parameters["retrieval_top_k"] != 6
    assert any(item.blocked for item in run.evaluations)


def test_review_required_improvement_stops_before_acceptance() -> None:
    baseline = _baseline()

    def evaluator(candidate: OptimizationCandidate) -> tuple[float, EvalPolicyGate]:
        if candidate.candidate_id == "baseline":
            return 0.50, EvalPolicyGate.ALLOW
        return 0.65, EvalPolicyGate.REQUIRE_HUMAN_REVIEW

    run = optimize_candidate(
        baseline,
        evaluator,
        max_iterations=3,
        minimum_improvement=0.01,
        require_human_review=True,
    )

    assert run.selected_score == 0.65
    assert run.iterations_completed == 1
    assert run.stopped_reason == "Improving candidate awaiting human approval."
    assert not any(item.accepted for item in run.evaluations)
