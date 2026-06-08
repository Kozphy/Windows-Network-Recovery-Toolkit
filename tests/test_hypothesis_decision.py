from __future__ import annotations

from src.decision_engine.hypothesis_decision import (
    PolicyDecision,
    build_hypothesis_decisions,
    build_why,
    decide_policy,
    proof_status_token,
)
from src.proof.contracts import ProofResult, ProofStatus


def test_decide_confirmed_always_allow() -> None:
    assert decide_policy(confidence=0.10, proof_status="CONFIRMED") == PolicyDecision.ALLOW


def test_decide_rejected_blocks() -> None:
    assert decide_policy(confidence=0.95, proof_status="REJECTED") == PolicyDecision.BLOCK


def test_decide_unproven_high_preview() -> None:
    assert decide_policy(confidence=0.72, proof_status="UNPROVEN") == PolicyDecision.PREVIEW


def test_decide_unproven_low_block() -> None:
    assert decide_policy(confidence=0.22, proof_status="UNPROVEN") == PolicyDecision.BLOCK


def test_decide_inconclusive_middle_preview() -> None:
    assert decide_policy(confidence=0.42, proof_status="INCONCLUSIVE") == PolicyDecision.PREVIEW


def test_proof_status_proxy_family_only() -> None:
    proof = ProofResult(
        proof_id="localhost_proxy_https_contrast",
        status=ProofStatus.CONFIRMED,
        hypothesis="unit",
        summary="ok",
    )
    assert (
        proof_status_token(
            hypothesis="dns_resolution_issue",
            localhost_proxy_proof=proof,
            proofs_enabled=True,
        )
        == "UNPROVEN"
    )
    assert (
        proof_status_token(
            hypothesis="unexpected_user_proxy",
            localhost_proxy_proof=proof,
            proofs_enabled=True,
        )
        == "CONFIRMED"
    )


def test_build_hypothesis_decisions_shape() -> None:
    proof = ProofResult(
        proof_id="localhost_proxy_https_contrast",
        status=ProofStatus.INCONCLUSIVE,
        hypothesis="h",
        summary="inconclusive",
    )
    rows = build_hypothesis_decisions(
        ranked=[
            ("unexpected_user_proxy", 0.82, ("evidence a",)),
            ("dns_resolution_issue", 0.35, ("evidence b",)),
        ],
        localhost_proxy_proof=proof,
        proofs_enabled=True,
    )
    assert len(rows) == 2
    required = {"hypothesis", "confidence", "proof_status", "why", "decision", "risk_score"}
    assert required.issubset(rows[0].keys())
    assert rows[0]["proof_status"] == "INCONCLUSIVE"
    assert rows[0]["decision"] in {"ALLOW", "PREVIEW", "BLOCK"}
    assert rows[1]["proof_status"] == "UNPROVEN"


def test_build_why_includes_policy() -> None:
    why = build_why(
        decision=PolicyDecision.PREVIEW,
        confidence=0.5,
        proof_status="UNPROVEN",
        evidence=["e1"],
        proof_summary=None,
    )
    assert any("confidence=" in line for line in why)
    assert any("preview" in line.lower() for line in why)
