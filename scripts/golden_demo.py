#!/usr/bin/env python3
"""Golden 5-minute demo — fixture replay, policy, report (read-only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "windows_network_toolkit" / "examples" / "proxy_drift_incident.jsonl"


def main() -> int:
    from windows_network_toolkit.audit.replay import replay_to_dict
    from windows_network_toolkit.audit.report_generator import generate_report

    if not FIXTURE.is_file():
        print(f"Fixture missing: {FIXTURE}", file=sys.stderr)
        return 1

    payload = replay_to_dict(FIXTURE, dry_run=True)
    report = generate_report(
        timeline=payload["timeline"],
        decision=payload["decision"],
        policy=payload["policy"],
        remediation=payload["remediation"],
        audit_rows=[payload.get("audit") or {}],
        fmt="markdown",
    )
    print("=== Endpoint Reliability Golden Demo ===")
    print(f"Fixture: {FIXTURE.name}")
    print(f"Incident type: {payload['decision'].get('incident_type')}")
    print(f"Policy: {payload['policy'].get('outcome')}")
    print()
    print(report)
    print()
    print("Dashboard (optional): http://127.0.0.1:8000/dashboard/")
    print("API health: http://127.0.0.1:8000/v1/health")
    out = REPO / "logs" / "golden_demo_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"JSON artifact: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
