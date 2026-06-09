"""Fixture-based fleet simulation — no live endpoint mutation."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from platform_core.models import utc_now_iso


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


def fleet_demo_dir(repo_root: Path | None = None) -> Path:
    root = _repo_root(repo_root)
    path = root / "platform_data_fleet_demo"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_fleet_scenario(name: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    path = root / "fixtures" / "fleet" / f"{name}.json"
    if not path.is_file():
        path = root / "fixtures" / "fleet" / f"{name.replace('-', '_')}.json"
    if not path.is_file():
        raise FileNotFoundError(f"fleet scenario not found: {name}")
    blob = json.loads(path.read_text(encoding="utf-8"))
    return blob if isinstance(blob, dict) else {}


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")


def run_fleet_simulation(
    *,
    scenario: str,
    endpoints: int = 25,
    repo_root: Path | None = None,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate synthetic endpoint snapshots and incidents under platform_data_fleet_demo/."""
    spec = load_fleet_scenario(scenario, repo_root=repo_root)
    root = _repo_root(repo_root)
    base = out_dir or fleet_demo_dir(root)
    for name in (
        "endpoints.jsonl",
        "snapshots.jsonl",
        "failure_events.jsonl",
        "platform_signals.jsonl",
        "incidents.jsonl",
    ):
        p = base / name
        if p.is_file():
            p.unlink()

    now = datetime.now(timezone.utc)
    incident_count = 0
    drift_count = 0
    template = spec.get("incident_template") or {}
    categories = spec.get("categories") or ["proxy_drift"]

    for i in range(max(1, endpoints)):
        ep_id = f"ep-fleet-{i:04d}"
        ts = (now - timedelta(minutes=i)).isoformat()
        _append_jsonl(
            base / "endpoints.jsonl",
            {
                "endpoint_id": ep_id,
                "hostname": f"ws-demo-{i:04d}",
                "os_family": "windows",
                "last_seen": ts,
            },
        )
        _append_jsonl(
            base / "snapshots.jsonl",
            {
                "endpoint_id": ep_id,
                "timestamp": ts,
                "proxy_enable": 1 if i % int(spec.get("drift_every_n", 5) or 5) == 0 else 0,
                "proxy_server": template.get("proxy_server") if i % 5 == 0 else None,
            },
        )
        if i % int(spec.get("drift_every_n", 5) or 5) == 0:
            drift_count += 1
            ev_id = f"fe-{uuid.uuid4().hex[:12]}"
            _append_jsonl(
                base / "failure_events.jsonl",
                {
                    "event_id": ev_id,
                    "endpoint_id": ep_id,
                    "category": categories[0],
                    "severity": template.get("severity", "medium"),
                    "status": "open",
                    "timestamp": ts,
                    "summary": template.get("summary", "Synthetic proxy drift"),
                    "evidence_level": template.get("evidence_level", "observation"),
                },
            )
            _append_jsonl(
                base / "platform_signals.jsonl",
                {
                    "kind": "proxy_registry_change",
                    "endpoint_id": ep_id,
                    "occurred_at": ts,
                    "detected_at": (now - timedelta(minutes=i - 1)).isoformat(),
                },
            )
            _append_jsonl(
                base / "incidents.jsonl",
                {
                    "incident_id": f"inc-{ep_id}",
                    "endpoint_id": ep_id,
                    "scenario": scenario,
                    "status": "open",
                    "severity": template.get("severity", "medium"),
                },
            )
            incident_count += 1

    summary = {
        "scenario": scenario,
        "endpoints": endpoints,
        "proxy_drift_incidents": drift_count,
        "incidents_total": incident_count,
        "output_dir": str(base),
        "generated_at": utc_now_iso(),
    }
    (base / "fleet_simulation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def fleet_report(*, repo_root: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    """Summarize last fleet simulation output."""
    root = _repo_root(repo_root)
    base = out_dir or fleet_demo_dir(root)
    summary_path = base / "fleet_simulation_summary.json"
    if summary_path.is_file():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "scenario": "none",
        "endpoints": 0,
        "proxy_drift_incidents": 0,
        "incidents_total": 0,
        "output_dir": str(base),
        "generated_at": utc_now_iso(),
    }


def render_fleet_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Fleet simulation report",
        "",
        f"- **Scenario:** {report.get('scenario')}",
        f"- **Endpoints:** {report.get('endpoints')}",
        f"- **Proxy drift incidents:** {report.get('proxy_drift_incidents')}",
        f"- **Incidents total:** {report.get('incidents_total')}",
        f"- **Output:** `{report.get('output_dir')}`",
        f"- **Generated:** {report.get('generated_at')}",
        "",
        "_Fixture-based simulation — no live endpoint mutation._",
    ]
    return "\n".join(lines) + "\n"
