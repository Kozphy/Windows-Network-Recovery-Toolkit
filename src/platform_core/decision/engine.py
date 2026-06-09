"""Decision engine from hypothesis + evidence tier."""

from __future__ import annotations

import uuid

from src.platform_core.contracts import Decision, EvidenceBundle, Hypothesis


def build_decision(
    bundle: EvidenceBundle,
    hypothesis: Hypothesis,
    *,
    recommended_action: str,
    risk_level: str = "medium",
    requires_human_review: bool = False,
) -> Decision:
    from platform_core.models import utc_now_iso

    return Decision(
        decision_id=f"dec-{uuid.uuid4().hex[:12]}",
        incident_id=bundle.incident_id,
        trace_id=bundle.incident_id,
        timestamp_utc=utc_now_iso(),
        incident_type=hypothesis.incident_type,
        recommended_action=recommended_action,
        confidence=hypothesis.confidence,
        risk_level=risk_level,  # type: ignore[arg-type]
        evidence_tier=bundle.tier,
        evidence_refs=hypothesis.supporting_evidence_ids,
        reasoning=hypothesis.explanation,
        requires_human_review=requires_human_review,
    )
