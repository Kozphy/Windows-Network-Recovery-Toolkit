"""Deterministic portfolio demos — no host mutation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCENARIOS: dict[str, str] = {
    "healthy": "healthy_endpoint.json",
    "proxy-drift": "proxy_drift_correlated_only.json",
    "sysmon-writer": "sysmon_registry_writer_proven.json",
    "final-causation": "final_causation_browser_path_failure.json",
    "suspicious-external": "suspicious_external_proxy.json",
    "developer-proxy": "developer_tool_proxy_allowed.json",
    "stale-listener": "stale_localhost_proxy_listener.json",
}


def _root(arg: str | None) -> Path:
    return Path(arg).resolve() if arg else Path.cwd().resolve()


def _fixture(name: str, repo: Path) -> Path:
    fname = SCENARIOS.get(name, name if name.endswith(".json") else f"{name}.json")
    return repo / "tests" / "fixtures" / "demo" / fname


def run_demo_scenario(name: str, *, repo_root: Path | None = None) -> dict[str, Any]:
    from platform_core.evidence_model import evidence_limitations, resolve_evidence_level
    from platform_core.policy_model import evaluate_endpoint_policy

    repo = _root(str(repo_root) if repo_root else None)
    blob = json.loads(_fixture(name, repo).read_text(encoding="utf-8"))
    proof = blob.get("proof_inputs") or {}
    ctx = blob.get("context") or {}
    level = resolve_evidence_level(proof)
    policy = evaluate_endpoint_policy(
        evidence_level=level,
        confidence_ordinal=float(ctx.get("confidence_ordinal", 0.5)),
        external_proxy=bool(ctx.get("external_proxy")),
        known_dev_tool=bool(ctx.get("known_dev_tool")),
        healthy_baseline=bool(ctx.get("healthy_baseline")),
    )
    return {
        "scenario_id": blob.get("scenario_id"),
        "title": blob.get("title"),
        "evidence_level": level,
        "expected_evidence_level": blob.get("expected_evidence_level"),
        "policy": policy,
        "expected_policy": blob.get("expected_policy"),
        "limitations": blob.get("limitations") or evidence_limitations(level),  # type: ignore[arg-type]
        "recommended_next_steps": blob.get("recommended_next_steps") or [],
    }


def render_markdown(report: dict[str, Any]) -> str:
    pol = report.get("policy") or {}
    lines = [
        f"# {report.get('title')}",
        "",
        f"**Evidence:** `{report.get('evidence_level')}` (expected `{report.get('expected_evidence_level')}`)",
        f"**Policy:** `{pol.get('decision')}` (expected `{report.get('expected_policy')}`)",
        "",
        "## Limitations",
    ]
    lines.extend(f"- {x}" for x in report.get("limitations") or [])
    lines.extend(["", "## Next steps"])
    lines.extend(f"- {x}" for x in report.get("recommended_next_steps") or [])
    lines.append("\n_Observation ≠ proof · Correlation ≠ causation · PREVIEW ≠ execute approval._\n")
    return "\n".join(lines)


def cmd_demo_scenario(args: argparse.Namespace) -> int:
    name = str(getattr(args, "demo_scenario", "healthy"))
    fmt = str(getattr(args, "demo_format", "markdown")).lower()
    report = run_demo_scenario(name, repo_root=_root(getattr(args, "repo_root", None)))
    if fmt == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report), end="")
    if report.get("expected_evidence_level") and report["evidence_level"] != report["expected_evidence_level"]:
        print("evidence mismatch", file=sys.stderr)
        return 1
    if report.get("expected_policy") and (report.get("policy") or {}).get("decision") != report["expected_policy"]:
        print("policy mismatch", file=sys.stderr)
        return 1
    return 0
