"""Unified evidence fusion and hypothesis ranking (all domains)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.platform.models import EvidenceItem, Hypothesis, NormalizedEvent


@dataclass
class EvidenceTreeNode:
    evidence_id: str
    description: str
    type: str
    confidence_delta: float
    supports: list[str]
    contradicts: list[str]


@dataclass
class EvidenceEngineResult:
    ranked_hypotheses: list[Hypothesis]
    confidence_score: float
    evidence_tree: list[EvidenceTreeNode]
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def rank_hypotheses(
    event: NormalizedEvent,
    evidence: list[EvidenceItem],
    hypotheses: list[Hypothesis],
) -> EvidenceEngineResult:
    by_id = {e.evidence_id: e for e in evidence}
    tree = [
        EvidenceTreeNode(
            evidence_id=e.evidence_id,
            description=e.description,
            type=e.type,
            confidence_delta=e.confidence_delta,
            supports=list(e.supports),
            contradicts=list(e.contradicts),
        )
        for e in evidence
    ]
    ranked: list[Hypothesis] = []
    notes: list[str] = []
    supporting: set[str] = set()
    contradicting: set[str] = set()

    for hyp in hypotheses:
        support_delta = 0.0
        contra_delta = 0.0
        for eid in hyp.supporting_evidence:
            item = by_id.get(eid)
            if item:
                support_delta += max(0.0, item.confidence_delta)
                supporting.add(eid)
        for eid in hyp.contradicting_evidence:
            item = by_id.get(eid)
            if item:
                contra_delta += abs(item.confidence_delta)
                contradicting.add(eid)
        missing = sum(1 for eid in hyp.supporting_evidence if eid not in by_id)
        adjusted = _clamp(hyp.confidence + support_delta - contra_delta - 0.05 * missing)
        notes.append(f"{hyp.hypothesis_id}=>{adjusted:.2f}")
        ranked.append(hyp.model_copy(update={"confidence": adjusted}))

    ranked.sort(key=lambda h: (-h.confidence, h.hypothesis_id))
    top = ranked[0].confidence if ranked else 0.3
    if not evidence:
        top = _clamp(top - 0.15)

    return EvidenceEngineResult(
        ranked_hypotheses=ranked,
        confidence_score=top,
        evidence_tree=tree,
        supporting_evidence=sorted(supporting),
        contradicting_evidence=sorted(contradicting),
        explanation=f"Event {event.event_id}: {'; '.join(notes[:3])}",
        metadata={"event_id": event.event_id, "domain": event.domain},
    )
