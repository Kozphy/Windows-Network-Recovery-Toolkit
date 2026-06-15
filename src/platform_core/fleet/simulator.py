"""Fixture-driven fleet simulation — 100+ synthetic endpoints, no live mutation."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.platform_core.governance.chain_of_custody import chain_hash, verify_chain

_REPO = Path(__file__).resolve().parents[3]
DEFAULT_FLEET_FIXTURE = _REPO / "tests" / "fixtures" / "fleet" / "fleet_100_endpoints.jsonl"


def load_fleet_fixture(path: str | Path | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else DEFAULT_FLEET_FIXTURE
    if not p.is_file():
        raise FileNotFoundError(f"fleet fixture not found: {p}")
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def fleet_summary_from_fixture(path: str | Path | None = None) -> dict[str, Any]:
    rows = load_fleet_fixture(path)
    classifications = Counter(r.get("classification", "UNKNOWN") for r in rows)
    tiers = Counter(r.get("evidence_tier", "OBSERVED_ONLY") for r in rows)
    policies = Counter(r.get("policy_decision", "PREVIEW_ONLY") for r in rows)
    severities = Counter(r.get("severity", "medium") for r in rows)
    incidents = sum(1 for r in rows if r.get("incident_open", True))
    risk_buckets = Counter(r.get("risk_bucket", "medium") for r in rows)

    return {
        "total_endpoints": len(rows),
        "total_incidents": incidents,
        "classifications": dict(classifications),
        "evidence_tiers": dict(tiers),
        "policy_decisions": dict(policies),
        "severity_breakdown": dict(severities),
        "risk_buckets": dict(risk_buckets),
        "remediation_preview_count": sum(
            1 for r in rows if r.get("policy_decision") in ("PREVIEW_ONLY", "PREVIEW")
        ),
        "fixture_path": str(path or DEFAULT_FLEET_FIXTURE),
        "limitations": [
            "Synthetic fleet data — not live endpoint telemetry.",
            "Observation is not proof.",
            "Confidence scores are ordinal, not probability.",
        ],
    }


def render_fleet_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Fleet simulation report",
        "",
        f"- **Total endpoints:** {summary.get('total_endpoints')}",
        f"- **Open incidents:** {summary.get('total_incidents')}",
        f"- **Remediation previews:** {summary.get('remediation_preview_count')}",
        "",
        "## Classifications",
    ]
    for k, v in sorted((summary.get("classifications") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Evidence tiers"])
    for k, v in sorted((summary.get("evidence_tiers") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Policy decisions"])
    for k, v in sorted((summary.get("policy_decisions") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Risk buckets"])
    for k, v in sorted((summary.get("risk_buckets") or {}).items()):
        lines.append(f"- {k}: {v}")
    lines.extend(["", "## Limitations"])
    for lim in summary.get("limitations") or []:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("_Fixture-based simulation — no live endpoint mutation._")
    return "\n".join(lines) + "\n"


def replay_fleet_fixture(path: str | Path | None = None) -> dict[str, Any]:
    """Deterministic replay digest from sorted endpoint ids."""
    rows = load_fleet_fixture(path)
    ordered = sorted(rows, key=lambda r: r.get("endpoint_id", ""))
    payload = {
        "endpoint_count": len(ordered),
        "classification_digest": sorted(
            f"{r.get('endpoint_id')}:{r.get('classification')}" for r in ordered
        ),
    }
    import hashlib

    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"summary": fleet_summary_from_fixture(path), "content_digest": digest}


def build_audit_chain_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build hash-chained audit records from fleet rows for demo export."""
    records: list[dict[str, Any]] = []
    prev = "genesis"
    for row in rows[:20]:
        body = {
            "event_id": row.get("event_id") or row.get("endpoint_id"),
            "timestamp": row.get("timestamp_utc", ""),
            "source": row.get("source", "fleet_simulation"),
            "evidence_tier": row.get("evidence_tier", "OBSERVED_ONLY"),
            "classification": row.get("classification"),
            "policy_decision": row.get("policy_decision"),
            "limitations": row.get("limitations") or [],
        }
        current = chain_hash(prev, body)
        records.append({**body, "previous_hash": prev, "current_hash": current})
        prev = current
    return records


def verify_fleet_audit_chain(records: list[dict[str, Any]]) -> tuple[bool, str]:
    return verify_chain(records)
