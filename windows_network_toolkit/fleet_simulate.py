"""Primary CLI fleet simulation — synthetic audit JSONL for analytics and Power BI."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from windows_network_toolkit.evidence_schema import STANDARD_LIMITATIONS

STANDARD_FLEET_LIMITATIONS = [
    "Synthetic fleet simulation — not production telemetry.",
    "Classification is triage, not a malware verdict.",
    "Does not prove malware or MITM.",
]

_INCIDENT_WEIGHTS: list[tuple[str, int]] = [
    ("DEAD_PROXY_CONFIG", 28),
    ("WININET_WINHTTP_MISMATCH", 18),
    ("HEALTHY_LOCALHOST_PROXY", 12),
    ("UNKNOWN_LOCAL_PROXY", 15),
    ("PAC_CONFIGURED", 10),
    ("DIRECT_ONLY_WORKS", 12),
    ("REVERTER_SUSPECTED", 5),
]

_CLASS_LIMITATIONS: dict[str, list[str]] = {
    "DEAD_PROXY_CONFIG": ["Dead localhost proxy — browser path may fail while ping works."],
    "WININET_WINHTTP_MISMATCH": ["WinINET and WinHTTP stacks diverge — correlate with path probes."],
    "HEALTHY_LOCALHOST_PROXY": ["Local proxy listener present — verify intended dev tooling."],
    "UNKNOWN_LOCAL_PROXY": ["Unknown local proxy — owner correlation only without writer proof."],
    "PAC_CONFIGURED": ["PAC URL configured — validate policy intent separately."],
    "DIRECT_ONLY_WORKS": ["Direct path works — proxy path may still be misconfigured."],
    "REVERTER_SUSPECTED": ["Enable/disable cycle detected — investigate reverter pattern."],
}

_EVIDENCE_TIERS = ("observation", "correlation", "proof")
_POLICY_OUTCOMES = ("PREVIEW_ONLY", "REQUIRE_TYPED_CONFIRMATION")


def _weighted_classes(rng: random.Random) -> list[str]:
    pool: list[str] = []
    for cls, weight in _INCIDENT_WEIGHTS:
        pool.extend([cls] * weight)
    rng.shuffle(pool)
    return pool


def _limitations_for(classification: str) -> list[str]:
    extra = _CLASS_LIMITATIONS.get(classification, [])
    return list(STANDARD_FLEET_LIMITATIONS) + list(STANDARD_LIMITATIONS[:2]) + extra


def _incident_row(
    *,
    endpoint_id: str,
    classification: str,
    idx: int,
    base_time: datetime,
    rng: random.Random,
) -> dict[str, Any]:
    ts = (base_time + timedelta(minutes=idx)).isoformat().replace("+00:00", "Z")
    incident_id = f"INC-{hashlib.sha256(f'{endpoint_id}:{classification}'.encode()).hexdigest()[:8].upper()}"
    return {
        "incident_id": incident_id,
        "endpoint_id": endpoint_id,
        "case_id": f"FLEET-{idx:04d}",
        "classification": {"primary_classification": classification},
        "evidence_tier": rng.choice(_EVIDENCE_TIERS),
        "policy_decision": {"outcome": rng.choice(_POLICY_OUTCOMES)},
        "timestamp": ts,
        "limitations": _limitations_for(classification),
        "source": "fleet_simulate",
    }


def _preview_row(incident_id: str, ts: str) -> dict[str, Any]:
    return {
        "incident_id": incident_id,
        "action": "remediation_preview",
        "dry_run": True,
        "timestamp": ts,
        "limitations": ["Preview-only — no registry mutation applied."],
    }


def run_fleet_simulate(
    *,
    scenario: str = "mixed_proxy_failures",
    endpoints: int = 100,
    seed: int = 42,
    out_dir: Path,
) -> dict[str, Any]:
    """Generate synthetic incidents.jsonl compatible with analytics pipeline."""
    if scenario != "mixed_proxy_failures":
        raise ValueError(f"unsupported scenario: {scenario}")

    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    incidents_path = out_dir / "incidents.jsonl"
    if incidents_path.is_file():
        incidents_path.unlink()

    classes = _weighted_classes(rng)
    base_time = datetime(2026, 6, 12, 8, 0, 0, tzinfo=UTC)
    endpoint_ids: list[str] = []
    rows_written = 0

    with incidents_path.open("w", encoding="utf-8") as fh:
        for i in range(endpoints):
            ep_id = f"endpoint-{i + 1:03d}"
            endpoint_ids.append(ep_id)
            classification = classes[i % len(classes)]
            row = _incident_row(
                endpoint_id=ep_id,
                classification=classification,
                idx=i,
                base_time=base_time,
                rng=rng,
            )
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
            rows_written += 1
            preview_ts = (base_time + timedelta(minutes=i, seconds=30)).isoformat().replace("+00:00", "Z")
            preview = _preview_row(row["incident_id"], preview_ts)
            fh.write(json.dumps(preview, separators=(",", ":")) + "\n")
            rows_written += 1

    summary = {
        "scenario": scenario,
        "endpoints": endpoints,
        "seed": seed,
        "rows_written": rows_written,
        "incident_rows": endpoints,
        "output_dir": str(out_dir.resolve()),
        "incidents_path": str(incidents_path.resolve()),
        "endpoint_ids_sample": endpoint_ids[:3] + ["..."] + endpoint_ids[-1:],
    }
    summary_path = out_dir / "fleet_simulate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
