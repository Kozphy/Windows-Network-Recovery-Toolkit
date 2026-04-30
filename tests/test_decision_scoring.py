from __future__ import annotations

from pathlib import Path

from src.diagnostics.collector import load_features_json
from src.decision_engine.scoring import explain_primary, score_root_causes

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_dns_issue_scores_highest_fixture() -> None:
    feats = load_features_json(FIXTURES / "features_dns_issue.json")
    decision = score_root_causes(feats)
    primary = decision.primary()
    assert primary.cause == "dns_issue"
    assert primary.confidence >= 0.7
    text = explain_primary(primary, feats)
    assert "confidence" in text.lower()
    assert "dns" in text.lower()


def test_proxy_issue_fixture() -> None:
    feats = load_features_json(FIXTURES / "features_proxy_issue.json")
    decision = score_root_causes(feats)
    ranked = decision.ranked()
    top_three = [c.cause for c in ranked[:3]]
    assert "proxy_issue" in top_three


def test_healthy_signals_favor_browser_or_benign_primary() -> None:
    feats = load_features_json(FIXTURES / "features_healthy_signals.json")
    decision = score_root_causes(feats)
    primary = decision.primary()
    assert primary.cause == "browser_only_issue"
    assert primary.confidence >= 0.45


def test_adapter_down_prioritizes_network_adapter() -> None:
    feats = load_features_json(FIXTURES / "features_adapter_down.json")
    decision = score_root_causes(feats)
    primary = decision.primary()
    assert primary.cause == "network_adapter_issue"
    scores = decision.scores_by_cause
    assert scores["network_adapter_issue"].confidence >= scores["dns_issue"].confidence


def test_confidences_are_clamped() -> None:
    feats = load_features_json(FIXTURES / "features_dns_issue.json")
    decision = score_root_causes(feats)
    for cs in decision.ranked():
        assert 0.0 <= cs.confidence <= 1.0


def test_fixture_loader_accepts_plain_object() -> None:
    feats = load_features_json(FIXTURES / "features_dns_issue.json")
    assert feats.ping_ip_ok is True  # sanity
