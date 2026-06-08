"""CLI handlers for the simulated AI-edge reliability layer.

Module responsibility:
    Implement ``edge-diagnose`` (fixture or live-simulated) and ``edge-replay`` for the
    ``python -m src`` CLI, reusing the deterministic engine in :mod:`edge_device.reasoning`
    and the append-only audit in :mod:`edge_device.audit`.

System placement:
    Imported and registered by :mod:`src.cli`. Handlers take an ``argparse.Namespace`` and
    return an ``int`` exit code, matching every other toolkit subcommand.

Side effects:
    ``edge-diagnose`` appends one row to ``logs/edge_runs.jsonl``. ``edge-replay`` is
    read-only.

Failure modes:
    Missing/invalid fixture -> exit 1 with a stderr message; unknown run id on replay ->
    exit 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from edge_device.audit import append_edge_run, load_edge_run
from edge_device.reasoning import run_edge_reasoning
from edge_device.simulator import SIM_PROFILES, simulate_edge_observations, simulated_device_profile
from platform_core.reasoning_models import ProofResult


def _repo_root(cli: Path | None) -> Path:
    """Resolve checkout root (``--repo-root`` or parent of ``src/``)."""
    if cli:
        return cli.resolve()
    return Path(__file__).resolve().parent.parent


def _proof_from_fixture(blob: dict[str, Any]) -> ProofResult | None:
    """Build an optional :class:`ProofResult` from a fixture ``proof`` block."""
    proof = blob.get("proof")
    if not isinstance(proof, dict):
        return None
    return ProofResult(
        source="edge_proof_engine",
        hypothesis=str(proof.get("hypothesis") or ""),
        status=str(proof.get("status") or "NOT_RUN"),  # type: ignore[arg-type]
        checks_run=list(proof.get("checks_run") or []),
        evidence=list(proof.get("evidence") or []),
    )


def _emit(run_output: dict[str, Any], *, emit_json: bool) -> None:
    """Print either the JSON contract or a concise human summary."""
    if emit_json:
        print(json.dumps(run_output, indent=2, ensure_ascii=False, default=str))
        return
    policy = run_output["policy_decision"]
    print("=== Edge diagnose (simulated AI-edge reliability) ===")
    print(f"run_id: {run_output['run_id']}")
    print(f"accepted_hypothesis: {run_output['accepted_hypothesis']}")
    print(f"impact: {run_output['reliability_impact']['severity']} ({run_output['reliability_impact']['scope']})")
    print(f"proof_status: {run_output['proof_status']}")
    print(f"policy: {policy['decision']}  action={policy['requested_action']}")
    print(f"reason_codes: {', '.join(policy['reason_codes']) or '(none)'}")
    print(f"safe_next_action: {run_output['safe_next_action']}")
    print(f"supporting: {', '.join(run_output['supporting_evidence']) or '(none)'}")
    print(f"contradicting: {', '.join(run_output['contradicting_evidence']) or '(none)'}")
    print(f"missing: {', '.join(run_output['missing_evidence']) or '(none)'}")
    print("Use --json for the full machine-readable contract.")


def cmd_edge_diagnose(args: argparse.Namespace) -> int:
    """Run edge reasoning from a fixture or simulated telemetry, persist, and print.

    Args:
        args: Namespace with ``fixture`` (path) or ``live_simulated`` (bool) plus optional
            ``profile``, ``requested_action``, ``confirm``, ``emit_json``, ``repo_root``.

    Returns:
        ``0`` on success; ``1`` on missing/invalid fixture input.
    """
    repo = _repo_root(getattr(args, "repo_root", None))
    fixture = getattr(args, "fixture", None)
    live = bool(getattr(args, "live_simulated", False))

    if not fixture and not live:
        print("edge-diagnose: provide --fixture PATH or --live-simulated.", file=sys.stderr)
        return 1

    requested_action = getattr(args, "requested_action", None)
    explicit_confirmation = bool(getattr(args, "confirm", False))
    proof_result: ProofResult | None = None

    if fixture:
        path = Path(fixture)
        if not path.is_file():
            print(f"edge-diagnose: fixture not found: {path}", file=sys.stderr)
            return 1
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"edge-diagnose: invalid fixture JSON: {exc}", file=sys.stderr)
            return 1
        raw = dict(blob.get("observations") or {})
        device_profile = dict(blob.get("device_profile") or {})
        proof_result = _proof_from_fixture(blob)
        if requested_action is None:
            requested_action = blob.get("requested_action")
        if not explicit_confirmation:
            explicit_confirmation = bool(blob.get("explicit_confirmation", False))
    else:
        profile = getattr(args, "profile", None) or "thermal"
        if profile not in SIM_PROFILES:
            print(f"edge-diagnose: unknown profile {profile!r}; choose from {sorted(SIM_PROFILES)}", file=sys.stderr)
            return 1
        raw = simulate_edge_observations(profile=profile)
        device_profile = simulated_device_profile(profile)

    run = run_edge_reasoning(
        raw,
        device_profile=device_profile,
        proof_result=proof_result,
        requested_action=requested_action,
        explicit_confirmation=explicit_confirmation,
    )
    append_edge_run(repo, run)
    _emit(run.to_output_dict(), emit_json=bool(getattr(args, "emit_json", False)))
    return 0


def cmd_edge_replay(args: argparse.Namespace) -> int:
    """Replay a stored edge run by id from ``logs/edge_runs.jsonl`` (read-only).

    Args:
        args: Namespace with ``run_id`` and optional ``repo_root``.

    Returns:
        ``0`` when the run is found and printed; ``1`` when missing.
    """
    repo = _repo_root(getattr(args, "repo_root", None))
    run_id = str(getattr(args, "run_id", "") or "").strip()
    if not run_id:
        print("edge-replay: missing RUN_ID — try: python -m src edge-replay <run_id>", file=sys.stderr)
        return 1
    row = load_edge_run(repo, run_id)
    if row is None:
        print(f"edge-replay: run_id not found in logs/edge_runs.jsonl: {run_id}", file=sys.stderr)
        return 1
    print(json.dumps(row, indent=2, ensure_ascii=False, default=str))
    return 0
