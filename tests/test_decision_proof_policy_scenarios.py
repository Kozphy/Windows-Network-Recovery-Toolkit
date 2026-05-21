"""Proof Engine × hypothesis decision policy — all subprocess/registry paths mocked.

Scenario matrix (deterministic, no network):

┌──────────────────────────────┬──────────────┬───────────────────────────────┐
│ proof.proxy_detected_causal │ CONFIRMED    │ ALLOW for proxy hypotheses    │
│ proof.proxy_detected_flat   │ REJECTED     │ BLOCK for proxy hypotheses    │
│ proof.inconclusive_both_fail│ INCONCLUSIVE │ PREVIEW when conf high        │
│ policy.dns_preview_operator│ (platform)   │ preview_allowed, exec denied  │
│ policy.firewall_blocked     │ (platform)    │ structured execution blocked │
└──────────────────────────────┴──────────────┴───────────────────────────────┘
"""

from __future__ import annotations

from unittest.mock import patch

from src.core.models import ProxyRegistrySnapshot
from src.decision_engine.hypothesis_decision import PolicyDecision, build_hypothesis_decisions
from src.proof.contracts import ProofStatus
from src.proof.proxy_https import run_localhost_proxy_https_proof
from tests.scenarios.live_snapshot_fixtures import scenario_dns_failure
from tests.scenarios.mock_proof_subprocess import localhost_proxy_proof_subprocess


def _baseline_proxy_snap() -> ProxyRegistrySnapshot:
    return ProxyRegistrySnapshot(
        proxy_enable=1,
        proxy_server="127.0.0.1:9999",
        auto_config_url=None,
        auto_detect=0,
    )


def test_proof_proxy_detected_and_causal_yields_allow_for_proxy_hypothesis() -> None:
    """Contrast failure via `-x`, success with `--noproxy` ⇒ CONFIRMED ⇒ ALLOW."""
    snap = _baseline_proxy_snap()
    sub = localhost_proxy_proof_subprocess(
        proxy_curl_rc=7,
        proxy_curl_out="",
        bypass_curl_rc=0,
        bypass_curl_out="302",
    )
    with patch("src.proof.proxy_https.read_proxy_registry", return_value=snap):
        proof = run_localhost_proxy_https_proof(subprocess_run=sub, curl_timeout=3.0)
    assert proof.status == ProofStatus.CONFIRMED

    ranked = [
        ("unexpected_user_proxy", 0.92, ("scorer says localhost proxy oddity",)),
    ]
    rows = build_hypothesis_decisions(
        ranked=ranked,
        localhost_proxy_proof=proof,
        proofs_enabled=True,
    )
    assert rows[0]["proof_status"] == "CONFIRMED"
    assert rows[0]["decision"] == PolicyDecision.ALLOW.value
    assert "CONFIRMED_SAFE_TIER_WITH_CONFIRMATION" in rows[0].get("reason_codes", [])
    assert any("safe-tier" in w.lower() for w in rows[0]["why"])


def test_proof_proxy_detected_not_causal_yields_block() -> None:
    """Both curl paths succeed ⇒ REJECTED ⇒ BLOCK (do not treat as intercept failure)."""
    snap = _baseline_proxy_snap()
    sub = localhost_proxy_proof_subprocess(
        proxy_curl_rc=0,
        proxy_curl_out="200",
        bypass_curl_rc=0,
        bypass_curl_out="200",
    )
    with patch("src.proof.proxy_https.read_proxy_registry", return_value=snap):
        proof = run_localhost_proxy_https_proof(subprocess_run=sub, curl_timeout=3.0)
    assert proof.status == ProofStatus.REJECTED

    rows = build_hypothesis_decisions(
        ranked=[("browser_proxy_path_issue", 0.88, ("ev1",))],
        localhost_proxy_proof=proof,
        proofs_enabled=True,
    )
    assert rows[0]["proof_status"] == "REJECTED"
    assert rows[0]["decision"] == PolicyDecision.BLOCK.value


def test_proof_inconclusive_both_paths_fail_high_conf_preview_only() -> None:
    """INCONCLUSIVE + high heuristic confidence ⇒ PREVIEW (unsafe to allow auto fix)."""
    snap = _baseline_proxy_snap()
    sub = localhost_proxy_proof_subprocess(
        proxy_curl_rc=28,
        proxy_curl_out="",
        bypass_curl_rc=6,
        bypass_curl_out="",
    )
    with patch("src.proof.proxy_https.read_proxy_registry", return_value=snap):
        proof = run_localhost_proxy_https_proof(subprocess_run=sub, curl_timeout=3.0)
    assert proof.status == ProofStatus.INCONCLUSIVE

    rows = build_hypothesis_decisions(
        ranked=[("winhttp_proxy_issue", 0.72, ("winhttp textual hint",))],
        localhost_proxy_proof=proof,
        proofs_enabled=True,
    )
    assert rows[0]["proof_status"] == "INCONCLUSIVE"
    assert rows[0]["decision"] == PolicyDecision.PREVIEW.value
    assert "HIGH_CONFIDENCE_UNPROVEN" in rows[0].get("reason_codes", [])


def test_conflicting_signals_dns_high_unproven_preview_not_allow() -> None:
    """DNS hypothesis never receives localhost-proxy proof token ⇒ UNPROVEN ⇒ PREVIEW if conf high."""
    snap = scenario_dns_failure()
    from src.decision_engine.live_scoring import score_live_snapshot

    ranked_tuples = [(s.hypothesis, s.confidence, s.evidence) for s in score_live_snapshot(snap)]

    rows = build_hypothesis_decisions(
        ranked=ranked_tuples,
        localhost_proxy_proof=None,
        proofs_enabled=True,
    )
    dns_rows = [r for r in rows if "DNS resolution" in r["hypothesis"]]
    assert dns_rows
    assert dns_rows[0]["proof_status"] == "UNPROVEN"
    assert dns_rows[0]["decision"] in {PolicyDecision.PREVIEW.value, PolicyDecision.BLOCK.value}
    assert dns_rows[0]["decision"] == PolicyDecision.PREVIEW.value


def test_hypothesis_allow_text_blocks_destructive_autorun_claim() -> None:
    """ALLOW row still carries language forbidding destructive auto-run."""
    from src.proof.contracts import ProofResult, ProofStatus

    pr = ProofResult(
        proof_id="localhost_proxy_https_contrast",
        status=ProofStatus.CONFIRMED,
        hypothesis="fixture",
        summary="CONFIRMED",
    )
    rows = build_hypothesis_decisions(
        ranked=[("unexpected_user_proxy", 0.9, ("fixture",))],
        localhost_proxy_proof=pr,
        proofs_enabled=True,
    )
    joined = "\n".join(rows[0]["why"]).lower()
    assert "confirmation" in joined or "destructive" in joined
