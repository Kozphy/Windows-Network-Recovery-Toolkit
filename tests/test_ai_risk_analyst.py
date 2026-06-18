"""AI risk analyst — guardrails, safety, deterministic mock output."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.ai_risk_analyst import (
    AnalystEvidenceBundle,
    LocalRuleBasedAnalyst,
    MockAnalyst,
    apply_guardrails,
    recommendation_passes_safety,
)
from src.platform_core.ai_risk_analyst.models import FORBIDDEN_ACTIONS

REPO = Path(__file__).resolve().parents[1]
DEAD_PROXY = REPO / "examples" / "evidence" / "DEAD_PROXY_CONFIG.json"


def test_forbidden_actions_include_destructive_verbs() -> None:
    assert "kill_process" in FORBIDDEN_ACTIONS
    assert "disable_proxy" in FORBIDDEN_ACTIONS
    assert "firewall_reset" in FORBIDDEN_ACTIONS


def test_incomplete_evidence_downgrades_confidence() -> None:
    bundle = AnalystEvidenceBundle(incident_id="inc-empty")
    rec = apply_guardrails(LocalRuleBasedAnalyst().analyze(bundle), bundle)
    assert rec.confidence_level in {"very_low", "low", "medium"}
    assert rec.missing_evidence


def test_mock_analyst_same_input_same_output() -> None:
    data = json.loads(DEAD_PROXY.read_text(encoding="utf-8"))
    bundle = AnalystEvidenceBundle(
        incident_id=data["incident_id"],
        classification=data["classification"],
        listener_info=data["listener_info"],
    )
    assert MockAnalyst().analyze(bundle).model_dump() == MockAnalyst().analyze(bundle).model_dump()


def test_ai_cannot_recommend_autonomous_kill() -> None:
    bundle = AnalystEvidenceBundle(
        incident_id="inc-kill",
        classification={"primary_classification": "UNKNOWN_LOCAL_PROXY"},
    )
    rec = apply_guardrails(
        LocalRuleBasedAnalyst().analyze(bundle).model_copy(
            update={"recommended_action": "Kill process now and disable proxy immediately."}
        ),
        bundle,
    )
    assert (
        "preview" in rec.recommended_action.lower()
        or "investigation" in rec.recommended_action.lower()
        or "remediation" in rec.recommended_action.lower()
        or "attribution" in rec.recommended_action.lower()
    )
    assert recommendation_passes_safety(rec)


def test_mitm_missing_tls_adds_missing_evidence() -> None:
    bundle = AnalystEvidenceBundle(
        incident_id="inc-mitm",
        classification={"primary_classification": "POSSIBLE_MITM_RISK"},
    )
    rec = apply_guardrails(LocalRuleBasedAnalyst().analyze(bundle), bundle)
    assert "tls_proof" in rec.missing_evidence
