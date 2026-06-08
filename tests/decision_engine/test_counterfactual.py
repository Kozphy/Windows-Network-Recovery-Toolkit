from __future__ import annotations

from src.decision_engine import (
    CandidateDecision,
    EvidenceItem,
    counterfactual_payload,
    simulate_counterfactuals,
    simulate_decision_paths,
    verify_simulation_determinism,
)


def _evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(evidence_id="proxy_on", label="Proxy enabled", weight=0.8, supports_decision=True),
        EvidenceItem(evidence_id="dns_ok", label="DNS resolves", weight=0.4, supports_decision=True),
        EvidenceItem(evidence_id="no_proof", label="No writer proof", weight=0.5, supports_decision=False),
    ]


def _decision_a() -> CandidateDecision:
    return CandidateDecision(
        decision_id="decision_a",
        label="Decision A — Preview disable proxy",
        base_benefit=60.0,
        base_risk=22.0,
        evidence_relevance={"proxy_on": 1.0, "dns_ok": 0.3, "no_proof": 0.6},
        risk_factors={"registry_change": 12.0},
    )


def _decision_b() -> CandidateDecision:
    return CandidateDecision(
        decision_id="decision_b",
        label="Decision B — Continue monitoring",
        base_benefit=30.0,
        base_risk=8.0,
        evidence_relevance={"proxy_on": 0.5, "dns_ok": 0.2},
    )


def _decision_c() -> CandidateDecision:
    return CandidateDecision(
        decision_id="decision_c",
        label="Decision C — Escalate to manual runbook",
        base_benefit=45.0,
        base_risk=15.0,
        evidence_relevance={"proxy_on": 0.7, "no_proof": 1.0},
        risk_factors={"operator_time": 20.0},
    )


def test_simulate_abc_counterfactual_output_contract() -> None:
    result = simulate_decision_paths(_evidence(), _decision_a(), _decision_b(), _decision_c())
    payload = counterfactual_payload(result)
    assert payload["chosen_decision"].startswith("Decision")
    assert len(payload["alternatives"]) == 2
    for alt in payload["alternatives"]:
        assert "expected_benefit" in alt
        assert "expected_risk" in alt
        assert "confidence" in alt
        assert alt["assumptions"]


def test_chosen_has_highest_final_score() -> None:
    result = simulate_counterfactuals(_evidence(), [_decision_a(), _decision_b(), _decision_c()])
    for alt in result.alternatives:
        assert alt.final_score <= result.final_score


def test_assumptions_documented() -> None:
    result = simulate_counterfactuals(_evidence(), [_decision_a(), _decision_b(), _decision_c()])
    statements = " ".join(a.statement for a in result.assumptions)
    assert "No machine learning" in statements
    assert "base benefit" in statements
    assert "Evidence" in statements


def test_deterministic_replay() -> None:
    candidates = [_decision_a(), _decision_b(), _decision_c()]
    ok, d1, d2 = verify_simulation_determinism(_evidence(), candidates)
    assert ok is True
    assert d1 == d2
    assert len(d1) == 64


def test_requires_at_least_two_candidates() -> None:
    try:
        simulate_counterfactuals(_evidence(), [_decision_a()])
    except ValueError as exc:
        assert "at least two" in str(exc)
    else:
        raise AssertionError("expected ValueError")
