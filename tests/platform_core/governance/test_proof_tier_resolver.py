"""Proof tier resolver T0–T7 tests."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.governance.proof_tier import (
    ProofTier,
    map_proof_tier_to_evidence_tier,
    resolve_proof_tier,
)

ROOT = Path(__file__).resolve().parents[3]
DEAD = json.loads((ROOT / "fixtures/dead_proxy_config/raw_signals.json").read_text(encoding="utf-8"))


def _t5_fixture() -> dict:
    return {
        **DEAD,
        "governance_proof": True,
        "policy_decision": {
            "executed": True,
            "dry_run": False,
            "confirmation_token_used": "DISABLE_WININET_PROXY",
        },
        "audit_chain_verification": {"verified": True},
    }


def _t6_fixture() -> dict:
    return {
        **_t5_fixture(),
        "controlled_validation": {
            "isolated_or_fixture_based": True,
            "change_applied": True,
            "failure_reproduced": True,
            "rollback_applied": True,
            "recovery_verified": True,
            "repeatable": True,
        },
    }


def test_dead_proxy_tier_at_least_t1() -> None:
    result = resolve_proof_tier(DEAD)
    assert result.proof_tier in (
        ProofTier.T1_LOCAL_CONFIG_EVIDENCE,
        ProofTier.T2_RUNTIME_CORROBORATION,
    )
    assert result.limitations


def test_t5_governance_proof() -> None:
    result = resolve_proof_tier(_t5_fixture())
    assert result.proof_tier == ProofTier.T5_GOVERNANCE_PROOF


def test_t6_requires_complete_controlled_validation() -> None:
    result = resolve_proof_tier(_t6_fixture())
    assert result.proof_tier == ProofTier.T6_CONTROLLED_VALIDATION
    assert "causal" in result.proof_tier_label.lower()


def test_incomplete_t6_stays_t5() -> None:
    fixture = _t6_fixture()
    fixture["controlled_validation"]["recovery_verified"] = False
    result = resolve_proof_tier(fixture)
    assert result.proof_tier == ProofTier.T5_GOVERNANCE_PROOF


def test_t7_requires_independent_verification() -> None:
    fixture = {
        **_t6_fixture(),
        "independent_verification": {
            "independent_verifier": True,
            "evidence_bundle_verified": True,
            "hash_chain_verified": True,
            "deterministic_replay_verified": True,
            "classification_reproduced": True,
        },
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier == ProofTier.T7_INDEPENDENT_VERIFICATION


def test_incomplete_t7_stays_t6() -> None:
    fixture = {
        **_t6_fixture(),
        "independent_verification": {
            "independent_verifier": True,
            "evidence_bundle_verified": True,
            "hash_chain_verified": True,
            "deterministic_replay_verified": False,
            "classification_reproduced": True,
        },
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier == ProofTier.T6_CONTROLLED_VALIDATION


def test_map_proof_tier_to_evidence_tier() -> None:
    assert map_proof_tier_to_evidence_tier(ProofTier.T0_OBSERVATION_ONLY) == "OBSERVED_ONLY"
    assert map_proof_tier_to_evidence_tier(ProofTier.T5_GOVERNANCE_PROOF) == "GOVERNANCE_VERIFIED"
    assert map_proof_tier_to_evidence_tier(ProofTier.T6_CONTROLLED_VALIDATION) == "CONTROLLED_VALIDATION"
    assert map_proof_tier_to_evidence_tier(ProofTier.T7_INDEPENDENT_VERIFICATION) == "INDEPENDENTLY_VERIFIED"


def test_mitm_capped_at_t2_even_with_high_assurance_metadata() -> None:
    fixture = {
        **_t6_fixture(),
        "classification": {"primary_classification": "POSSIBLE_MITM_RISK"},
        "independent_verification": {
            "independent_verifier": True,
            "evidence_bundle_verified": True,
            "hash_chain_verified": True,
            "deterministic_replay_verified": True,
            "classification_reproduced": True,
        },
    }
    result = resolve_proof_tier(fixture)
    assert result.proof_tier == ProofTier.T2_RUNTIME_CORROBORATION
    assert any("not confirmed interception" in item for item in result.limitations)
