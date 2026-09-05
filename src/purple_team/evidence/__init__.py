"""Tamper-evident evidence bundles with chained hashes."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.purple_team import __version__
from src.purple_team.models import ScenarioRunResult

SCHEMA = "purple_evidence_bundle.v1"


def _sha256(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_evidence_bundle(
    result: ScenarioRunResult,
    *,
    pre_state: dict[str, Any],
    simulation_evidence: dict[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    prev = "0" * 64
    stages = [
        ("pre_state", pre_state),
        ("simulation", simulation_evidence),
        ("telemetry", [t.to_dict() for t in result.telemetry]),
        ("detections", [d.to_dict() for d in result.detections]),
        ("risk", result.risk.to_dict() if result.risk else {}),
        (
            "response",
            {
                "recommendation": result.recommendation.to_dict()
                if result.recommendation
                else None,
                "remediation": result.remediation.to_dict() if result.remediation else None,
            },
        ),
        ("verification", result.verification.to_dict() if result.verification else {}),
        (
            "metrics",
            {
                "true_positive": result.true_positive,
                "false_positive": result.false_positive,
                "true_negative": result.true_negative,
                "false_negative": result.false_negative,
                "timing": result.timing.to_dict(),
            },
        ),
    ]
    for name, payload in stages:
        entry = {
            "stage": name,
            "payload": payload,
            "prev_hash": prev,
        }
        digest = _sha256(entry)
        entry["hash"] = digest
        records.append(entry)
        prev = digest

    bundle = {
        "schema_version": SCHEMA,
        "run_id": result.run_id,
        "scenario_id": result.scenario_id,
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purple_team_version": __version__,
        "state": result.state.value,
        "chain_tip": prev,
        "records": records,
        "provenance": {
            "producer": "src.purple_team.evidence",
            "version": __version__,
            "run_id": result.run_id,
            "scenario_id": result.scenario_id,
        },
        "trust_assumptions": [
            "Hashes provide tamper-evidence for the local bundle file, not remote WORM storage.",
            "Integrity verification assumes the verifier trusts the first known tip or stored tip.",
            "Does not prevent deletion of the entire bundle; detects in-place mutation of records.",
        ],
        "limitations": result.limitations,
    }
    bundle["bundle_hash"] = _sha256({k: v for k, v in bundle.items() if k != "bundle_hash"})
    return bundle


def verify_evidence_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Verify chained hashes; return {ok, errors[]}."""
    errors: list[str] = []
    prev = "0" * 64
    for i, rec in enumerate(bundle.get("records") or []):
        expected_prev = rec.get("prev_hash")
        if expected_prev != prev:
            errors.append(f"record[{i}] prev_hash mismatch")
        check = {k: v for k, v in rec.items() if k != "hash"}
        if _sha256(check) != rec.get("hash"):
            errors.append(f"record[{i}] hash mismatch")
        prev = rec.get("hash") or ""
    if bundle.get("chain_tip") != prev:
        errors.append("chain_tip mismatch")
    stored = bundle.get("bundle_hash")
    recomputed = _sha256({k: v for k, v in bundle.items() if k != "bundle_hash"})
    if stored != recomputed:
        errors.append("bundle_hash mismatch")
    return {"ok": not errors, "errors": errors, "chain_tip": prev}


def write_evidence_bundle(bundle: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
