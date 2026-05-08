"""Append-only audit and replay helpers for reasoning runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from platform_core.reasoning_engine import run_reasoning
from platform_core.reasoning_models import Observation, ProofResult, ReasoningRun
from platform_core.storage import append_jsonl, iter_jsonl, platform_data_dir

REASONING_AUDIT_FILE = "reasoning_runs.jsonl"


def reasoning_audit_path(path: Path | None = None) -> Path:
    """Resolve the reasoning audit JSONL path."""
    return path or platform_data_dir() / REASONING_AUDIT_FILE


def to_audit_record(run: ReasoningRun) -> dict[str, Any]:
    """Serialize a reasoning run into a replayable audit record."""
    return {
        "record_type": "reasoning_run",
        "version_metadata": run.version_metadata,
        "run": run.model_dump(mode="json"),
        "raw_observations": [obs.model_dump(mode="json") for obs in run.raw_observations],
        "normalized_signals": run.normalized_signals,
        "detected_events": [event.model_dump(mode="json") for event in run.detected_events],
        "state_transitions": [transition.model_dump(mode="json") for transition in run.state_transitions],
        "hypothesis_ranking": run.hypothesis_ranking,
        "evidence_tree": run.evidence_tree.model_dump(mode="json"),
        "proof_result": run.proof_result.model_dump(mode="json"),
        "policy_decision": run.policy_decision.model_dump(mode="json"),
        "recommended_next_test": run.recommended_next_test,
        "remediation_preview": run.remediation_preview,
        "limitations": run.limitations,
    }


def append_reasoning_run(run: ReasoningRun, *, path: Path | None = None) -> Path:
    """Append one reasoning run to JSONL.

    Args:
        run: Reasoning run to persist.
        path: Optional test path.

    Returns:
        Path written.
    """
    out = reasoning_audit_path(path)
    append_jsonl(out, to_audit_record(run))
    return out


def iter_reasoning_records(path: Path | None = None) -> Iterator[dict[str, Any]]:
    """Yield reasoning audit records."""
    yield from iter_jsonl(reasoning_audit_path(path))


def replay_reasoning_record(record: dict[str, Any]) -> ReasoningRun:
    """Recompute a reasoning run from stored observations and proof result only.

    Args:
        record: Audit record produced by :func:`to_audit_record`.

    Returns:
        Recomputed reasoning run. The machine is not probed.
    """
    run_blob = record.get("run") or {}
    observations_blob = record.get("raw_observations") or run_blob.get("raw_observations") or []
    observations = [Observation(**item) for item in observations_blob if isinstance(item, dict)]
    proof_blob = record.get("proof_result") or run_blob.get("proof_result") or {}
    proof = ProofResult(**proof_blob) if isinstance(proof_blob, dict) else ProofResult()
    policy_blob = record.get("policy_decision") or run_blob.get("policy_decision") or {}
    requested_action = policy_blob.get("requested_action") if isinstance(policy_blob, dict) else None
    explicit_confirmation = bool(
        isinstance(policy_blob, dict)
        and "confirmed_proof_safe_action_confirmation_present" in (policy_blob.get("reason_codes") or [])
    )
    return run_reasoning(
        observations,
        proof_result=proof,
        requested_action=requested_action,
        explicit_confirmation=explicit_confirmation,
        source="replay",
        run_id=str(run_blob.get("id") or record.get("run_id") or ""),
    )
