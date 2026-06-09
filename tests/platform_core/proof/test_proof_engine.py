"""Direct vs proxied proof engine."""

from __future__ import annotations

import json
from pathlib import Path

from src.platform_core.proof.engine import classify_proof_outcome, run_proof_engine
from src.platform_core.proof.models import ProofObservation, ProofOutcome

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "erp"


def test_local_proxy_upstream_failure() -> None:
    observations = [
        ProofObservation(probe_id="dns", probe_type="dns", observed_value="1.2.3.4", success=True),
        ProofObservation(probe_id="tcp", probe_type="tcp", observed_value="ok", success=True),
        ProofObservation(probe_id="http_direct", probe_type="http_direct", observed_value="200", success=True),
        ProofObservation(probe_id="http_system", probe_type="http_system", observed_value="502", success=False),
    ]
    outcome, rationale, confidence, is_proof = classify_proof_outcome(observations)
    assert outcome == ProofOutcome.LOCAL_PROXY_UPSTREAM_FAILURE
    assert is_proof is True
    assert confidence == "high"
    assert "502" in rationale or "Direct" in rationale


def test_dns_failure() -> None:
    observations = [
        ProofObservation(probe_id="dns", probe_type="dns", observed_value="fail", success=False),
    ]
    outcome, _, _, is_proof = classify_proof_outcome(observations)
    assert outcome == ProofOutcome.DNS_FAILURE
    assert is_proof is True


def test_dead_localhost_proxy_flag() -> None:
    outcome, _, _, _ = classify_proof_outcome([], dead_localhost_proxy=True)
    assert outcome == ProofOutcome.DEAD_LOCALHOST_PROXY


def test_inject_fixture_deterministic() -> None:
    data = json.loads((FIXTURES / "proof_local_proxy_failure.json").read_text(encoding="utf-8"))
    proof = run_proof_engine("https://example.com/", inject=data)
    assert proof.outcome == ProofOutcome.LOCAL_PROXY_UPSTREAM_FAILURE
    assert proof.is_proof is True
    assert len(proof.observations) == 4
