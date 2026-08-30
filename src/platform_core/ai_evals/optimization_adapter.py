"""Adapter between optimization candidates and the deterministic eval suite."""

from __future__ import annotations

from copy import deepcopy

from .evaluator import run_eval_suite
from .failure_taxonomy import EvalPolicyGate
from .optimization_schemas import OptimizationCandidate
from .schemas import EvalCase
from .scoring import score_report

_GATE_PRIORITY: dict[EvalPolicyGate, int] = {
    EvalPolicyGate.ALLOW: 0,
    EvalPolicyGate.PREVIEW: 1,
    EvalPolicyGate.REQUIRE_HUMAN_REVIEW: 2,
    EvalPolicyGate.INSUFFICIENT_EVIDENCE: 3,
    EvalPolicyGate.BLOCK: 4,
}


def evaluate_candidate(
    candidate: OptimizationCandidate,
    baseline_cases: list[EvalCase],
) -> tuple[float, EvalPolicyGate]:
    """Apply supported candidate parameters and return score plus strictest gate.

    Unsupported parameters remain candidate metadata until the runtime/evaluator gains a
    deterministic implementation for them. This prevents the optimizer from pretending a
    parameter affected results when it did not.
    """
    cases = deepcopy(baseline_cases)

    for case in cases:
        if "require_citations" in candidate.parameters:
            case.require_citations = bool(candidate.parameters["require_citations"])

    report = run_eval_suite(cases)
    score = score_report(report)
    strictest_gate = max(
        (result.policy_decision.gate for result in report.results),
        key=_GATE_PRIORITY.__getitem__,
        default=EvalPolicyGate.INSUFFICIENT_EVIDENCE,
    )
    return score, strictest_gate
