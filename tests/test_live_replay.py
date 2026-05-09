"""Replay: round-trip observations → score parity; append-only audit scan."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import pytest

from src.command_handlers import cmd_diagnose_live, cmd_replay_live_run
from src.decision_engine.hypothesis_decision import build_hypothesis_decisions
from src.decision_engine.live_replay import (
    SCHEMA_VERSION,
    build_replay_report,
    find_decision_run,
    live_network_snapshot_from_observations,
)
from src.decision_engine.live_scoring import ranked_dicts, score_live_snapshot
from tests.scenarios.live_snapshot_fixtures import scenario_dns_failure


def test_snapshot_roundtrip_observations_score_parity() -> None:
    snap = scenario_dns_failure()
    blob = snap.to_dict()
    snap2 = live_network_snapshot_from_observations(blob)
    a = score_live_snapshot(snap)
    b = score_live_snapshot(snap2)
    assert [x.hypothesis for x in a] == [x.hypothesis for x in b]
    for x, y in zip(a, b):
        assert abs(x.confidence - y.confidence) < 1e-9


def test_append_only_audit_replay_verification(tmp_path: Path) -> None:
    repo = tmp_path / "chk"
    (repo / "logs").mkdir(parents=True)
    (repo / "reports").mkdir(parents=True)

    snap = scenario_dns_failure()
    ranked = score_live_snapshot(snap)
    hrows = ranked_dicts(ranked)
    tuples = [(s.hypothesis, s.confidence, s.evidence) for s in ranked]
    decisions = build_hypothesis_decisions(
        ranked=tuples,
        localhost_proxy_proof=None,
        proofs_enabled=False,
        trust_assessment=None,
    )
    run_id = str(uuid.uuid4())
    row = {
        "schema_version": SCHEMA_VERSION,
        "type": "live_run_audit",
        "run_id": run_id,
        "timestamp_utc": snap.generated_at_utc,
        "script_version": "test",
        "machine": {},
        "observations": snap.to_dict(),
        "hypotheses_ranked": hrows,
        "hypothesis_decisions": decisions,
        "proof_engine": {},
        "proof_engine_error": None,
        "proofs_requested": False,
        "uncertainty": {"trust_aggregate": 0.71, "degraded_mode": False},
        "commands_executed": [],
        "live_snapshot_ref": str(repo / "reports" / f"{run_id}.json"),
        "primary_hypothesis": ranked[0].hypothesis,
        "primary_confidence": ranked[0].confidence,
    }
    drift = dict(row)
    drift["hypotheses_ranked"] = list(hrows)
    if drift["hypotheses_ranked"]:
        drift["hypotheses_ranked"][0] = dict(drift["hypotheses_ranked"][0])
        drift["hypotheses_ranked"][0]["confidence"] = float(drift["hypotheses_ranked"][0]["confidence"]) + 0.5
    # ``find_decision_run`` selects the latest line for the same ``run_id`` (append semantics).
    (repo / "logs" / "decision_runs.jsonl").write_text(
        json.dumps(drift, ensure_ascii=False) + "\n" + json.dumps(row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    found = find_decision_run(repo, run_id)
    assert found is not None
    report = build_replay_report(found)
    assert report["verification"]["confidence_numeric_replay_match"] is True
    report_bad = build_replay_report(drift)
    assert report_bad["verification"]["confidence_numeric_replay_match"] is False


def test_cmd_replay_not_found_returns_one(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    (repo / "logs").mkdir(parents=True)
    args = argparse.Namespace(repo_root=repo, replay_run_id=str(uuid.uuid4()), emit_json=False)
    code = cmd_replay_live_run(args)
    assert code == 1


def test_cmd_diagnose_live_replay_dispatches(monkeypatch, tmp_path: Path) -> None:
    """``diagnose-live`` routes ``--replay`` before Windows gate."""

    import src.command_handlers as ch

    def fake_replay(_args):
        return 42

    monkeypatch.setattr(ch, "cmd_replay_live_run", fake_replay)

    class A:
        repo_root = tmp_path
        replay_run_id = "some-uuid"
        emit_json = False
        emit_both = False
        live_proofs = False

    assert cmd_diagnose_live(A()) == 42


def test_replay_does_not_reprobe_or_mutate(monkeypatch, tmp_path: Path) -> None:
    """Replay reads stored observations only; proxy mutation/read helpers must not be called."""

    import src.command_handlers as ch

    repo = tmp_path / "r"
    (repo / "logs").mkdir(parents=True)
    snap = scenario_dns_failure()
    ranked = score_live_snapshot(snap)
    decisions = build_hypothesis_decisions(
        ranked=[(s.hypothesis, s.confidence, s.evidence) for s in ranked],
        localhost_proxy_proof=None,
        proofs_enabled=False,
        trust_assessment=None,
    )
    run_id = str(uuid.uuid4())
    row = {
        "schema_version": SCHEMA_VERSION,
        "type": "live_run_audit",
        "run_id": run_id,
        "timestamp_utc": snap.generated_at_utc,
        "script_version": "test",
        "machine": {},
        "observations": snap.to_dict(),
        "hypotheses_ranked": ranked_dicts(ranked),
        "hypothesis_decisions": decisions,
        "proof_engine": {},
        "proof_engine_error": None,
        "proofs_requested": False,
        "uncertainty": {"trust_aggregate": 0.71, "degraded_mode": False},
        "commands_executed": [],
        "live_snapshot_ref": "",
        "primary_hypothesis": ranked[0].hypothesis,
        "primary_confidence": ranked[0].confidence,
    }
    (repo / "logs" / "decision_runs.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    monkeypatch.setattr(ch, "read_proxy_registry", lambda **_: pytest.fail("replay must not read registry"))
    monkeypatch.setattr(ch, "apply_mutations", lambda *_a, **_k: pytest.fail("replay must not mutate"))

    args = argparse.Namespace(repo_root=repo, replay_run_id=run_id, emit_json=True, emit_both=False)
    assert cmd_replay_live_run(args) == 0
