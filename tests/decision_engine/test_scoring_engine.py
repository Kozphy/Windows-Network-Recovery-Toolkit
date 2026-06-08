from __future__ import annotations

from src.decision_engine import (
    CandidateDecision,
    EvidenceItem,
    engine_summary,
    run_decision_engine,
    score_candidate,
)
from src.decision_engine.ranking import rank_scored_decisions
from src.decision_engine.scoring import score_candidates


def _proxy_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            evidence_id="proxy_enabled",
            label="ProxyEnable=1",
            weight=0.8,
            supports_decision=True,
        ),
        EvidenceItem(
            evidence_id="listener_match",
            label="Listener on proxy port",
            weight=0.6,
            supports_decision=True,
        ),
        EvidenceItem(
            evidence_id="no_writer_proof",
            label="No registry writer proof",
            weight=0.5,
            supports_decision=False,
        ),
    ]


def _candidates() -> list[CandidateDecision]:
    return [
        CandidateDecision(
            decision_id="preview_disable_proxy",
            label="Preview disable WinINET proxy",
            base_benefit=55.0,
            base_risk=20.0,
            evidence_relevance={
                "proxy_enabled": 1.0,
                "listener_match": 0.8,
                "no_writer_proof": 0.5,
            },
            risk_factors={"registry_mutation": 10.0},
        ),
        CandidateDecision(
            decision_id="monitor_only",
            label="Continue monitoring",
            base_benefit=35.0,
            base_risk=8.0,
            evidence_relevance={
                "proxy_enabled": 0.4,
                "listener_match": 0.3,
            },
        ),
    ]


def test_score_candidate_has_breakdown() -> None:
    scored = score_candidate(_proxy_evidence(), _candidates()[0])
    assert 0 <= scored.benefit <= 100
    assert 0 <= scored.risk <= 100
    assert 0.0 <= scored.confidence <= 1.0
    assert scored.breakdown.benefit_components["base_benefit"] == 55.0
    assert "evidence:proxy_enabled" in scored.breakdown.benefit_components
    assert "final_score" in scored.breakdown.formulas


def test_final_score_formula_transparent() -> None:
    scored = score_candidate(_proxy_evidence(), _candidates()[0])
    expected = max(
        0,
        min(
            100,
            round(scored.benefit * scored.confidence - scored.risk * 0.35),
        ),
    )
    assert scored.final_score == expected


def test_ranking_deterministic_tiebreak() -> None:
    scored = score_candidates(_proxy_evidence(), _candidates())
    ranked_a = rank_scored_decisions(scored)
    ranked_b = rank_scored_decisions(scored)
    assert [r.decision_id for r in ranked_a] == [r.decision_id for r in ranked_b]
    assert ranked_a[0].rank == 1


def test_run_decision_engine_output_contract() -> None:
    result = run_decision_engine(_proxy_evidence(), _candidates())
    summary = engine_summary(result)
    assert summary["decision"]
    assert 0.0 <= summary["confidence"] <= 1.0
    assert isinstance(summary["benefit"], int)
    assert isinstance(summary["risk"], int)
    assert isinstance(summary["final_score"], int)
    assert summary["breakdown"]["benefit_components"]
    assert len(summary["content_digest"]) == 64


def test_engine_replay_digest_stable() -> None:
    result_a = run_decision_engine(_proxy_evidence(), _candidates())
    result_b = run_decision_engine(_proxy_evidence(), _candidates())
    assert result_a.content_digest == result_b.content_digest


def test_preview_disable_beats_monitor_for_proxy_fixture() -> None:
    result = run_decision_engine(_proxy_evidence(), _candidates())
    assert result.recommendation["decision_id"] == "preview_disable_proxy"
