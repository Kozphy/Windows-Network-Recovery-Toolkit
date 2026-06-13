"""Federated Decision Intelligence Platform tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.decision_intelligence import (
    DecisionDomain,
    build_evidence_input_from_fixture,
    evaluate_federated,
    replay_verify,
)

REPO = Path(__file__).resolve().parents[1]
CS1 = REPO / "case_studies" / "cs1_wininet_proxy_drift" / "fixture.json"


def test_five_domain_recommendations() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload, incident_id="cs1-dip"))

    domains = {r.domain for r in result.recommendations}
    assert domains == {
        DecisionDomain.IT_OPERATIONS,
        DecisionDomain.SECURITY,
        DecisionDomain.RISK,
        DecisionDomain.BUSINESS,
        DecisionDomain.COMPLIANCE,
    }


def test_it_operations_recommends_preview_disable() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    it = next(r for r in result.recommendations if r.domain == DecisionDomain.IT_OPERATIONS)
    assert it.policy_posture == "PREVIEW"
    assert "disable" in it.recommendation.lower() or "preview" in it.recommendation.lower()


def test_security_recommends_monitor() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    sec = next(r for r in result.recommendations if r.domain == DecisionDomain.SECURITY)
    assert sec.policy_posture == "OBSERVE"
    assert "monitor" in sec.recommendation.lower() or "collect" in sec.recommendation.lower()


def test_risk_defers_and_lists_missing_evidence() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    risk = next(r for r in result.recommendations if r.domain == DecisionDomain.RISK)
    assert risk.policy_posture == "DEFER"
    assert risk.missing_evidence


def test_business_minimize_downtime() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    biz = next(r for r in result.recommendations if r.domain == DecisionDomain.BUSINESS)
    assert "downtime" in biz.title.lower() or "surgical" in biz.recommendation.lower()


def test_compliance_audit_recommendation() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    cmp = next(r for r in result.recommendations if r.domain == DecisionDomain.COMPLIANCE)
    assert "audit" in cmp.recommendation.lower()


def test_explainable_score_breakdown() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    for rec in result.recommendations:
        assert rec.explain.formulas
        assert rec.explain.final_score >= 0
        assert "not probability" in rec.confidence_display


def test_evidence_traceability() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    assert result.explainability.nodes
    assert result.explainability.edges
    for rec in result.recommendations:
        assert rec.evidence_trace or rec.missing_evidence


def test_audit_digest_and_replay() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    assert result.audit.content_digest
    assert len(result.audit.content_digest) == 64
    assert result.audit.replay_anchor
    assert len(result.audit.domains_evaluated) == 5


def test_deterministic_digest() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    ev = build_evidence_input_from_fixture(payload, incident_id="deterministic-test")
    a = evaluate_federated(ev)
    b = evaluate_federated(ev)
    assert a.audit.content_digest == b.audit.content_digest


def test_never_implies_certainty() -> None:
    payload = json.loads(CS1.read_text(encoding="utf-8"))
    result = evaluate_federated(build_evidence_input_from_fixture(payload))
    blob = json.dumps(result.to_dict()).lower()
    assert "100% certain" not in blob
    assert "guaranteed safe" not in blob
