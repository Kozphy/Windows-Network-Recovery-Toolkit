"""Bounded hill-climbing orchestration for offline AI-eval experiments.

The optimizer ranks candidates but never deploys them. Policy gates are authoritative,
and human review remains required by default.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .candidate_generator import generate_neighbors
from .failure_taxonomy import EvalPolicyGate
from .optimization_schemas import CandidateEvaluation, OptimizationCandidate


@dataclass
class OptimizationRun:
    baseline: OptimizationCandidate
    selected: OptimizationCandidate
    baseline_score: float
    selected_score: float
    iterations_completed: int
    stopped_reason: str
    evaluations: list[CandidateEvaluation] = field(default_factory=list)


CandidateEvaluator = Callable[[OptimizationCandidate], tuple[float, EvalPolicyGate]]


def optimize_candidate(
    initial: OptimizationCandidate,
    evaluator: CandidateEvaluator,
    *,
    max_iterations: int = 5,
    minimum_improvement: float = 0.01,
    require_human_review: bool = True,
) -> OptimizationRun:
    """Run bounded local search while enforcing policy and review constraints."""
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")
    if minimum_improvement < 0:
        raise ValueError("minimum_improvement cannot be negative")

    current = initial
    current_score, _current_gate = evaluator(current)
    baseline_score = current_score
    evaluations: list[CandidateEvaluation] = []

    for iteration in range(max_iterations):
        eligible: list[CandidateEvaluation] = []

        for candidate in generate_neighbors(current):
            score, gate = evaluator(candidate)
            improvement = round(score - current_score, 4)
            blocked = gate in {
                EvalPolicyGate.BLOCK,
                EvalPolicyGate.INSUFFICIENT_EVIDENCE,
            }

            evaluation = CandidateEvaluation(
                candidate=candidate,
                fitness_score=score,
                blocked=blocked,
                requires_human_review=require_human_review
                or gate == EvalPolicyGate.REQUIRE_HUMAN_REVIEW,
                policy_gate=gate,
                improvement_over_baseline=improvement,
            )

            if blocked:
                evaluation.rejection_reason = f"Candidate rejected by policy gate: {gate.value}"
            elif improvement < minimum_improvement:
                evaluation.rejection_reason = "Candidate did not meet minimum improvement."
            else:
                eligible.append(evaluation)

            evaluations.append(evaluation)

        if not eligible:
            return OptimizationRun(
                baseline=initial,
                selected=current,
                baseline_score=baseline_score,
                selected_score=current_score,
                iterations_completed=iteration,
                stopped_reason="No eligible improving neighbor.",
                evaluations=evaluations,
            )

        best = max(eligible, key=lambda item: item.fitness_score)
        current = best.candidate
        current_score = best.fitness_score

        if best.requires_human_review:
            return OptimizationRun(
                baseline=initial,
                selected=current,
                baseline_score=baseline_score,
                selected_score=current_score,
                iterations_completed=iteration + 1,
                stopped_reason="Improving candidate awaiting human approval.",
                evaluations=evaluations,
            )

        best.accepted = True

    return OptimizationRun(
        baseline=initial,
        selected=current,
        baseline_score=baseline_score,
        selected_score=current_score,
        iterations_completed=max_iterations,
        stopped_reason="Maximum iteration limit reached.",
        evaluations=evaluations,
    )
