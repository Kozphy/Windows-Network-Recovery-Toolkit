"""Replay JSONL fixtures through the ERP pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from windows_network_toolkit.pipeline import PipelineResult, run_incident_pipeline


def _incident_type_value(decision: Any) -> str:
    incident_type = decision.incident_type
    return incident_type.value if hasattr(incident_type, "value") else str(incident_type)


def replay_jsonl(path: Path | str, *, dry_run: bool = True) -> PipelineResult:
    return run_incident_pipeline(jsonl_path=path, dry_run=dry_run)


def replay_to_dict(path: Path | str, *, dry_run: bool = True) -> dict[str, Any]:
    result = replay_jsonl(path, dry_run=dry_run)
    return {
        "incident_id": result.bundle.incident_id,
        "timeline": result.timeline,
        "incident_type": _incident_type_value(result.decision),
        "confidence": result.decision.confidence,
        "decision": result.decision.model_dump(),
        "policy": result.policy,
        "remediation": result.remediation,
        "audit": result.audit_record,
    }


def load_jsonl_signals(path: Path | str) -> dict[str, Any]:
    signals: dict[str, Any] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            if "signal" in row:
                signals[str(row["signal"])] = row.get("observed_value", row.get("value"))
            elif "name" in row:
                signals[str(row["name"])] = row.get("value")
            else:
                signals.update({k: v for k, v in row.items() if k not in {"timestamp", "timestamp_utc"}})
    return signals
