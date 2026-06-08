from __future__ import annotations

import tempfile
from pathlib import Path

from platform_core.diagnosis_text import render_reasoning_summary
from platform_core.reasoning_audit import (
    append_reasoning_run,
    iter_reasoning_records,
    replay_reasoning_record,
    to_audit_record,
)
from platform_core.reasoning_engine import observation, run_reasoning
from platform_core.reasoning_models import ProofResult


def _observations():
    return [
        observation("ping_ok"),
        observation("dns_ok"),
        observation("tcp443_ok"),
        observation("browser_https_failed"),
        observation("wininet_proxy_enabled"),
        observation("localhost_proxy_detected"),
        observation("proxy_bypass_succeeded"),
        observation("proxied_path_failed"),
    ]


def test_replay_produces_same_decision_from_audit_record() -> None:
    proof = ProofResult(hypothesis="browser_proxy_path_regression", status="CONFIRMED", confidence=0.95)
    run = run_reasoning(_observations(), proof_result=proof, requested_action="restore_proxy")
    replayed = replay_reasoning_record(to_audit_record(run))
    assert replayed.accepted_hypothesis == run.accepted_hypothesis
    assert replayed.policy_decision.outcome == run.policy_decision.outcome
    assert replayed.evidence_tree.state_path == run.evidence_tree.state_path


def test_append_only_reasoning_audit_record_can_be_replayed() -> None:
    proof = ProofResult(hypothesis="browser_proxy_path_regression", status="CONFIRMED", confidence=0.95)
    run = run_reasoning(_observations(), proof_result=proof, requested_action="restore_proxy")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "reasoning_runs.jsonl"
        append_reasoning_run(run, path=path)
        records = list(iter_reasoning_records(path))
    assert len(records) == 1
    replayed = replay_reasoning_record(records[0])
    assert replayed.policy_decision.outcome == "PREVIEW"


def test_diagnosis_text_uses_structured_evidence_only() -> None:
    run = run_reasoning(_observations(), requested_action="restore_proxy")
    text = render_reasoning_summary(run)
    assert "browser_proxy_path_regression" in str(text["short_diagnosis"])
    assert "Accepted evidence:" in str(text["evidence_summary"])
    assert text["proof_status"] == "NOT_RUN"
    assert text["safe_next_action"]
