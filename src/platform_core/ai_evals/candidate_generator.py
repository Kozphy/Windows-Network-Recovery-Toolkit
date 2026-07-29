"""Generate small, bounded configuration changes for offline local search."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .optimization_schemas import OptimizationCandidate


def generate_neighbors(current: OptimizationCandidate) -> list[OptimizationCandidate]:
    """Generate candidates that each change exactly one safe configuration value."""
    parameters = current.parameters
    top_k = int(parameters.get("retrieval_top_k", 5))
    max_length = int(parameters.get("max_response_length", 500))
    threshold = float(parameters.get("unsupported_claim_threshold", 0.25))

    modifications: list[tuple[str, Any, str]] = [
        ("retrieval_top_k", max(1, top_k - 1), "Test reduced retrieval breadth."),
        ("retrieval_top_k", min(20, top_k + 1), "Test increased retrieval breadth."),
        ("max_response_length", max(100, max_length - 100), "Test a more concise response limit."),
        ("max_response_length", min(2_000, max_length + 100), "Test a broader response limit."),
        (
            "unsupported_claim_threshold",
            round(max(0.05, threshold - 0.05), 2),
            "Test stricter grounding sensitivity.",
        ),
        (
            "unsupported_claim_threshold",
            round(min(0.95, threshold + 0.05), 2),
            "Test looser grounding sensitivity.",
        ),
    ]

    neighbors: list[OptimizationCandidate] = []
    for index, (key, value, reason) in enumerate(modifications, start=1):
        if parameters.get(key) == value:
            continue
        candidate_parameters = deepcopy(parameters)
        candidate_parameters[key] = value
        neighbors.append(
            OptimizationCandidate(
                candidate_id=f"{current.candidate_id}-n{index}",
                parent_id=current.candidate_id,
                parameters=candidate_parameters,
                generation_reason=reason,
                iteration=current.iteration + 1,
            )
        )
    return neighbors
