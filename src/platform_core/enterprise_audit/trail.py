"""Enterprise audit trail — immutable chain-of-custody export."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from platform_core.models import utc_now_iso

from src.platform_core.governance.chain_of_custody import chain_hash, verify_chain


def build_audit_trail(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build hash-chained audit records for full enterprise pipeline output."""
    records: list[dict[str, Any]] = []
    prev = "genesis"
    layers = [
        ("business_objectives", payload.get("business_objectives") or []),
        ("assets", payload.get("assets") or []),
        ("threats", payload.get("threats") or []),
        ("controls", payload.get("controls") or []),
        ("tests", payload.get("control_tests") or []),
        ("findings", payload.get("findings") or []),
        ("risks", payload.get("risk_assessments") or []),
        ("remediations", payload.get("remediations") or []),
    ]
    for layer_name, items in layers:
        for item in items:
            body = {
                "timestamp": utc_now_iso(),
                "source": "risk_analytics_pipeline",
                "layer": layer_name,
                "event_id": _event_id(item),
                "evidence_tier": item.get("evidence_tier") or payload.get("evidence_tier", "OBSERVED_ONLY"),
                "classification": item.get("classification") or payload.get("classification"),
                "policy_decision": item.get("policy_decision") or payload.get("policy_decision"),
                "limitations": item.get("limitations") or [],
                "payload_excerpt": _excerpt(item),
            }
            current = chain_hash(prev, body)
            records.append({**body, "previous_hash": prev, "current_hash": current})
            prev = current
    return records


def _event_id(item: dict[str, Any]) -> str:
    for key in ("id", "objective_id", "asset_id", "threat_id", "control_id", "test_id",
                "finding_id", "risk_id", "remediation_id", "case_id"):
        if item.get(key):
            return str(item[key])
    return "unknown"


def _excerpt(item: dict[str, Any]) -> str:
    text = json.dumps(item, sort_keys=True, default=str)[:256]
    return text


def verify_audit_trail(records: list[dict[str, Any]]) -> tuple[bool, str]:
    return verify_chain(records)


def export_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str)


def export_jsonl(records: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(r, default=str) for r in records) + "\n"


def export_csv_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "finding_id,severity,description,control_id,recommendation\n"
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["finding_id", "severity", "description", "control_id", "recommendation"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in findings:
        writer.writerow(row)
    return buf.getvalue()


def append_audit_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, default=str) + "\n")
