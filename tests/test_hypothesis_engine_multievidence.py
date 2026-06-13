"""Hypothesis engine — multievidence detection tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.platform_core.hypothesis import (
    MultievidenceInput,
    evaluate_hypotheses,
    multievidence_from_fixture,
)
from src.platform_core.hypothesis.models import (
    NetworkEvidence,
    ProcessEvidence,
    RegistryEvidence,
    TimelineEvent,
    TimelineEvidence,
)
from src.platform_core.hypothesis.scorer import format_confidence_display

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_confidence_display_never_claims_probability() -> None:
    display = format_confidence_display(0.92)
    assert "ordinal" in display
    assert "not probability" in display
    assert "certain" not in display.lower() or "not" in display.lower()


def test_cs1_dead_proxy_primary_hypothesis() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    data = multievidence_from_fixture(payload, incident_id="cs1-test")
    result = evaluate_hypotheses(data)

    assert result.primary.incident_type == "DEAD_PROXY_CONFIG"
    assert result.primary.confidence <= 0.98
    assert "not probability" in result.primary.confidence_display
    assert len(result.primary.supporting_evidence) >= 1
    assert result.primary.missing_evidence  # writer telemetry missing
    assert len(result.alternatives) >= 1


def test_always_provides_competing_hypotheses() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    assert len(result.alternatives) >= 1
    assert result.primary.alternative_explanations
    titles = {result.primary.title} | {a.title for a in result.alternatives}
    assert len(titles) >= 2


def test_observation_separated_from_proof_in_supporting_evidence() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    tiers = {e.tier for e in result.primary.supporting_evidence}
    assert "OBSERVED_ONLY" in tiers or "CORRELATED" in tiers
    assert "FINAL_CAUSATION" not in tiers
    for ref in result.primary.supporting_evidence:
        if ref.tier == "OBSERVED_ONLY":
            assert ref.is_proof is False


def test_unknown_listener_competing_hypothesis() -> None:
    data = MultievidenceInput(
        incident_id="unknown-listener",
        registry=RegistryEvidence(
            evidence_id="ev-reg",
            proxy_enable=1,
            proxy_server="127.0.0.1:61526",
        ),
        process=ProcessEvidence(
            evidence_id="ev-proc",
            listener_found=True,
            process_name="unknown_svc.exe",
            localhost_port=61526,
        ),
        network=NetworkEvidence(evidence_id="ev-net", browser_https_ok=False),
    )
    result = evaluate_hypotheses(data)
    all_types = {result.primary.incident_type} | {a.incident_type for a in result.alternatives}
    assert "UNKNOWN_LOCAL_PROXY" in all_types
    primary_or_alt = result.primary if result.primary.incident_type == "UNKNOWN_LOCAL_PROXY" else next(
        a for a in result.alternatives if a.incident_type == "UNKNOWN_LOCAL_PROXY"
    )
    assert any("writer" in m.lower() or "telemetry" in m.lower() for m in primary_or_alt.missing_evidence)


def test_never_claims_certainty_in_limitations() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    blob = json.dumps(result.to_dict()).lower()
    assert "100% certain" not in blob
    assert "confirmed malware" not in blob
    assert "proven malware" not in blob
    assert "guaranteed" not in blob


def test_confidence_explanation_present() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    assert result.primary.confidence_explanation
    assert "ordinal" in result.primary.confidence_explanation.lower() or "heuristic" in result.primary.confidence_explanation.lower()


def test_recommended_actions_are_preview_not_execute() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    actions = " ".join(result.primary.recommended_actions).lower()
    assert "preview" in actions or "observe" in actions or "collect" in actions
    assert "auto-kill" not in actions
    assert "execute" not in actions


def test_timeline_signals_influence_hypothesis() -> None:
    data = MultievidenceInput(
        incident_id="tl-test",
        registry=RegistryEvidence(
            evidence_id="ev-reg",
            proxy_enable=1,
            proxy_server="127.0.0.1:59081",
            winhttp_direct=True,
        ),
        process=ProcessEvidence(evidence_id="ev-proc", listener_found=False, localhost_port=59081),
        timeline=TimelineEvidence(
            evidence_id="ev-tl",
            events=[
                TimelineEvent(timestamp_utc="2026-01-01T00:00:00Z", signal="browser_https_failed", observed_value="true"),
                TimelineEvent(timestamp_utc="2026-01-01T00:00:05Z", signal="direct_path_success", observed_value="true"),
            ],
        ),
        network=NetworkEvidence(evidence_id="ev-net"),
    )
    result = evaluate_hypotheses(data)
    assert result.primary.incident_type == "DEAD_PROXY_CONFIG"


def test_insufficient_data_fallback_when_no_signals() -> None:
    data = MultievidenceInput(incident_id="empty")
    result = evaluate_hypotheses(data)
    assert result.primary.incident_type == "ERROR_INSUFFICIENT_DATA"


@pytest.mark.parametrize("phrase", ["probability", "percent chance", "100%"])
def test_epistemic_notice_on_result(phrase: str) -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_hypotheses(multievidence_from_fixture(payload))
    assert phrase not in result.epistemic_notice.lower() or "not" in result.primary.confidence_display
