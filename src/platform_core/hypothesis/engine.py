"""Hypothesis generation from evidence bundle."""

from __future__ import annotations

import uuid

from src.platform_core.contracts import EvidenceBundle, Hypothesis


def build_hypothesis(bundle: EvidenceBundle, *, incident_type: str, title: str, explanation: str) -> Hypothesis:
    return Hypothesis(
        hypothesis_id=f"hyp-{uuid.uuid4().hex[:12]}",
        event_id=bundle.incident_id,
        title=title,
        explanation=explanation,
        confidence=0.7,
        supporting_evidence_ids=[i.evidence_id for i in bundle.items],
        incident_type=incident_type,
    )
