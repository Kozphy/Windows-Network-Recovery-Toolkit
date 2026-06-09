"""Incident timeline builder."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.attribution.models import AttributionSnapshot
from src.platform_core.proof.models import ProofResult
from src.platform_core.timeline.builder import IncidentTimelineBuilder

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "erp"


def test_timeline_chronological_order() -> None:
    attr = AttributionSnapshot.model_validate(
        json.loads((FIXTURES / "attribution_dead_proxy.json").read_text(encoding="utf-8"))
    )
    proof = ProofResult.model_validate(
        json.loads((FIXTURES / "proof_local_proxy_failure.json").read_text(encoding="utf-8"))
    )
    builder = IncidentTimelineBuilder(incident_id="inc-test")
    builder.add_proxy_state(attr)
    builder.add_proof_result(proof)
    timeline = builder.build()
    timestamps = [e["timestamp"] for e in timeline]
    assert timestamps == sorted(timestamps)
    assert any(e["event_type"] == "proof_classified" for e in timeline)
    assert any(e["event_type"] == "proxy_state_observed" for e in timeline)


def test_remediation_preview_entry() -> None:
    builder = IncidentTimelineBuilder()
    builder.add_remediation_preview(
        {"previews": [{"action_id": "disable_wininet_proxy", "mutations": []}]},
        timestamp="2026-06-04T11:00:00+00:00",
    )
    timeline = builder.build()
    assert timeline[0]["event_type"] == "remediation_preview"
    assert timeline[0]["limitations"][0].startswith("Preview only")
