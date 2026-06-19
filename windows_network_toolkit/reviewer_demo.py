"""Deterministic reviewer demo — read-only stdout walkthrough for hiring panels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from windows_network_toolkit.analytics_pipeline import (
    normalize_events_from_fixture,
    run_endpoint_analytics_pipeline,
)
from windows_network_toolkit.control_tests import run_endpoint_control_tests
from windows_network_toolkit.evidence_schema import STANDARD_LIMITATIONS
from windows_network_toolkit.incident_classifier import classify_incidents_from_events

_MODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "big4": (
        "control test",
        "management information",
        "evidence tier",
        "ITGC",
        "preview-only",
        "classification is not accusation",
        "governance",
        "audit",
    ),
    "faang": (
        "reliability",
        "SLO",
        "fleet",
        "observability",
        "dry-run",
        "preview-only",
        "limitations",
        "endpoint",
    ),
    "mixed": (
        "control test",
        "management information",
        "reliability",
        "preview-only",
        "classification is not accusation",
        "limitations",
        "governance",
        "dry-run",
    ),
}

_FORBIDDEN_PHRASES = (
    "MALWARE_DETECTED",
    "MITM_CONFIRMED",
    "COMPROMISED",
    "autonomous repair",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_demo_fixture(repo: Path) -> dict[str, Any]:
    analytics_path = repo / "tests" / "fixtures" / "analytics_pipeline_fixture.json"
    dead_proxy_path = repo / "tests" / "fixtures" / "enert" / "dead_proxy_59081.json"
    fixture: dict[str, Any] = {}
    if analytics_path.is_file():
        fixture.update(json.loads(analytics_path.read_text(encoding="utf-8")))
    if dead_proxy_path.is_file():
        dead = json.loads(dead_proxy_path.read_text(encoding="utf-8"))
        if dead.get("proxy_state"):
            fixture["proxy_state"] = dead["proxy_state"]
        if dead.get("classification"):
            fixture["classification_inject"] = dead["classification"]
        if dead.get("proof"):
            fixture["health_inject"] = {
                "timestamp_utc": dead["proxy_state"].get("timestamp_utc"),
                "proxy_status": "DEAD_PROXY_CONFIG",
                "direct_probe_ok": True,
                "proxy_probe_ok": False,
                "proxy_https_connect_ok": False,
                "limitations": dead["proof"].get("limitations", []),
            }
    return fixture


def _read_text_safe(path: Path, limit: int = 400) -> str:
    if not path.is_file():
        return f"{path} (not found)"
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            text = path.read_text(encoding=encoding)
            return text[:limit] + ("..." if len(text) > limit else "")
        except UnicodeDecodeError:
            continue
    return f"{path.name} (unreadable encoding)"


def _emit(step: int, title: str, body: str, out: TextIO) -> None:
    out.write(f"\n--- Step {step}: {title} ---\n")
    out.write(body.rstrip() + "\n")


def run_reviewer_demo(
    *,
    mode: str = "mixed",
    out_dir: Path | None = None,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Run the 10-step reviewer demo without host mutation."""
    mode = mode.lower()
    if mode not in _MODE_KEYWORDS:
        raise ValueError(f"unsupported mode: {mode}")

    repo = _repo_root()
    sink = stream or __import__("sys").stdout
    fixture = _load_demo_fixture(repo)

    _emit(1, "Load fixture", "Fixture sources: analytics_pipeline_fixture + dead_proxy_59081", sink)

    events = normalize_events_from_fixture(fixture)
    _emit(
        2,
        "Normalize evidence",
        f"Normalized {len(events)} evidence events (read-only).",
        sink,
    )

    incidents = classify_incidents_from_events(events)
    primary = incidents[0].incident_class if incidents else "UNKNOWN"
    _emit(
        3,
        "Classify incident",
        f"Primary classification: {primary}\n"
        f"Limitations: {incidents[0].limitations[:2] if incidents else STANDARD_LIMITATIONS[:2]}",
        sink,
    )

    health = fixture.get("health_inject") or {}
    _emit(
        4,
        "Health / proof (fixture inject)",
        f"Direct probe ok: {health.get('direct_probe_ok')}\n"
        f"Proxy probe ok: {health.get('proxy_probe_ok')}\n"
        "No live probes — fixture inject only.",
        sink,
    )

    control_results = run_endpoint_control_tests(
        proxy_state=fixture.get("proxy_state") or {},
        health_audit=health,
        owner=fixture.get("proxy_owner"),
        reverter_diagnosis=(fixture.get("timeline") or [{}])[0].get("reverter_diagnosis")
        if fixture.get("timeline")
        else None,
    )
    summary_lines = [f"{t.control_id}: {t.test_result}" for t in control_results[:4]]
    _emit(5, "Control tests", "\n".join(summary_lines), sink)

    _emit(
        6,
        "Policy outcome",
        "Policy decision: PREVIEW_ONLY\n"
        "Dry-run default — no registry mutation without typed confirmation.",
        sink,
    )

    audit_rows: list[dict[str, Any]] = [
        {
            "timestamp": fixture.get("proxy_state", {}).get("timestamp_utc", "2026-06-11T04:31:31Z"),
            "incident_id": incidents[0].incident_id if incidents else "INC-DEMO",
            "classification": {"primary_classification": primary},
            "policy_decision": {"outcome": "PREVIEW_ONLY"},
            "dry_run": True,
            "limitations": list(STANDARD_LIMITATIONS[:3]),
        }
    ]
    audit_path: Path | None = None
    if out_dir is not None:
        audit_dir = out_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path = audit_dir / "reviewer_demo_audit.jsonl"
        with audit_path.open("w", encoding="utf-8") as fh:
            for row in audit_rows:
                fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    _emit(
        7,
        "Simulate audit append",
        f"Rows: {len(audit_rows)} (in-memory)"
        + (f"\nWritten: {audit_path}" if audit_path else ""),
        sink,
    )

    sample_audit = repo / "tests" / "fixtures" / "risk_analytics" / "audit_sample" / "incidents.jsonl"
    chain_msg = "sample audit file not found — skip chain verify"
    if sample_audit.is_file():
        from src.platform_core.governance.chain_of_custody import verify_chain

        rows: list[dict[str, Any]] = []
        for line in sample_audit.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        ok, msg = verify_chain(rows)
        chain_msg = f"verify_chain on sample: ok={ok} ({msg})"
    _emit(8, "Audit chain check", chain_msg, sink)

    gov_path = repo / "reports" / "sample_governance_report.md"
    gov_snippet = _read_text_safe(gov_path)
    _emit(9, "Governance report", f"Reference: {gov_path}\n{gov_snippet}", sink)

    keywords = _MODE_KEYWORDS[mode]
    talking = "\n".join(f"- {kw}" for kw in keywords)
    _emit(
        10,
        f"Talking points ({mode})",
        talking
        + "\n\nBoundary: management information only — classification is not accusation.",
        sink,
    )

    payload = run_endpoint_analytics_pipeline(fixture=fixture)
    return {
        "mode": mode,
        "incident_class": primary,
        "control_tests": len(control_results),
        "analytics_schema": payload.get("schema_version"),
        "audit_path": str(audit_path) if audit_path else None,
        "keywords": list(keywords),
    }
