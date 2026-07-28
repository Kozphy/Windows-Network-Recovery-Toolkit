"""Policy-gated orchestration for read-only incident investigations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence


class Decision(str, Enum):
    """Allowed outcomes for an agent-assisted investigation."""

    EXPLAIN_ONLY = "EXPLAIN_ONLY"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class InvestigationResult:
    """Immutable result emitted by the governed investigation workflow."""

    decision: Decision
    evidence: Mapping[str, Any]
    classification: Mapping[str, Any]
    explanation: str
    limitations: tuple[str, ...] = field(default_factory=tuple)
    remediation_preview: Mapping[str, Any] | None = None
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.execution_authorized:
            raise ValueError("Agent workflows cannot authorize execution")


class GovernedInvestigation:
    """Run evidence collection, deterministic classification and explanation.

    The supplied callbacks remain intentionally narrow. The orchestrator never
    receives an execution callback, so an LLM or agent cannot cross the human
    approval boundary by construction.
    """

    def __init__(
        self,
        *,
        collect_evidence: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        classify: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        explain: Callable[[Mapping[str, Any], Mapping[str, Any]], str],
        preview_remediation: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self._collect_evidence = collect_evidence
        self._classify = classify
        self._explain = explain
        self._preview_remediation = preview_remediation

    def run(
        self,
        incident: Mapping[str, Any],
        *,
        request_remediation_preview: bool = False,
    ) -> InvestigationResult:
        evidence = dict(self._collect_evidence(incident))
        classification = dict(self._classify(evidence))
        explanation = self._explain(evidence, classification)
        limitations = tuple(_normalise_limitations(classification.get("limitations")))

        if classification.get("blocked") is True:
            return InvestigationResult(
                decision=Decision.BLOCKED,
                evidence=evidence,
                classification=classification,
                explanation=explanation,
                limitations=limitations,
            )

        preview = None
        decision = Decision.EXPLAIN_ONLY
        if request_remediation_preview:
            if self._preview_remediation is None:
                limitations = (*limitations, "remediation preview unavailable")
            else:
                preview = dict(self._preview_remediation(classification))
                decision = Decision.HUMAN_REVIEW_REQUIRED

        return InvestigationResult(
            decision=decision,
            evidence=evidence,
            classification=classification,
            explanation=explanation,
            limitations=limitations,
            remediation_preview=preview,
        )


def _normalise_limitations(value: Any) -> Sequence[str]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value)
    return (str(value),)
