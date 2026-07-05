"""Proof tier resolver T0–T5 tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.governance.proof_tier import (
    ProofTier,
    map_proof_tier_to_evidence_tier,
    resolve_proof_tier,
)

ROOT = Path(__file__).resolve().parents[3]
DEAD = json.loads(
    (ROOT / "fixtures/dead_proxy_config/raw_signals.json").read_text(encoding="utf-8")
)


def test_dead_proxy_tier_at_least_t1() -> None:
    result = resolve_proof_tier(DEAD)
    assert result.proof_tier in (
        ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
        ProofTier.T2_RUNTIME_CORROBORATION,
    )
    assert result.limitations


def test_t5_governance_proof() -> None:
    fixture = {
        **DEAD,
        "governance_proof": True,
        "policy_decision": {"executed": True, "dry_run": False, "confirmation_token_used": "DISABLE_WININET_PROXY"},
        "audit_chain_verification": {"verified": True},
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier == ProofTier.T5_GOVERNANCE_PROOF


def test_map_proof_tier_to_evidence_tier() -> None:
    assert map_proof_tier_to_evidence_tier(ProofTier.T0_OBSERVATION_ONLY) == "OBSERVED_ONLY"
    assert map_proof_tier_to_evidence_tier(ProofTier.T5_GOVERNANCE_PROOF) == "FINAL_CAUSATION"


def test_mitm_capped_at_t2() -> None:
    fixture = {
        "classification": {"primary_classification": "POSSIBLE_MITM_RISK"},
        "proof": {"conclusion": {"status": "supported"}, "proof_attempts": [{"name": "direct_https_probe", "status": "supported"}]},
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier in (
        ProofTier.T0_OBSERVATION_ONLY,
        ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
        ProofTier.T2_RUNTIME_CORROBORATION,
    )
