"""LAN privacy orchestration — bundle loading and command runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .classifier import classify_lan_behavior
from .collectors import collect_inventory, collect_mdns_summary, collect_ssdp_summary, observations_from_watch_events
from .executive_report import build_executive_report, write_executive_report
from .privacy_risk_score import compute_privacy_risk_score
from .report import build_lan_privacy_report, render_lan_privacy_markdown
from .segmentation_advisor import advise_segmentation
from .watch import load_watch_jsonl, run_lan_watch

try:
    from windows_network_toolkit.diagnostics.router_evidence.correlator import correlate_host_router
    from windows_network_toolkit.diagnostics.router_evidence.runner import load_router_jsonl
except ImportError:
    correlate_host_router = None  # type: ignore[assignment,misc]
    load_router_jsonl = None  # type: ignore[assignment,misc]

try:
    from windows_network_toolkit.lan_control_tests import run_lan_control_tests
except ImportError:
    run_lan_control_tests = None  # type: ignore[assignment,misc]


def load_bundle(path: str | Path) -> dict[str, Any]:
    """Load executive bundle JSON fixture."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    repo = p.parent
    root = p.parents[2] if len(p.parents) > 2 else p.parent

    def _resolve_ref(ref: str) -> str:
        if not ref:
            return ref
        candidate = Path(ref)
        if candidate.is_file():
            return str(candidate)
        for base in (repo, root):
            for c in (base / ref, base / Path(ref).name):
                if c.is_file():
                    return str(c)
        return ref

    if data.get("host_log"):
        data["host_log"] = _resolve_ref(data["host_log"])
    if data.get("router_log"):
        data["router_log"] = _resolve_ref(data["router_log"])
    return data


def _resolve_observations(bundle: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    observations: list[dict[str, Any]] = list(bundle.get("observations") or [])
    inventory = bundle.get("inventory") or {}
    router_events: list[dict[str, Any]] = list(bundle.get("router_events") or [])

    if bundle.get("host_log") and load_watch_jsonl:
        events = load_watch_jsonl(bundle["host_log"])
        observations.extend(observations_from_watch_events(events))
        if not inventory.get("devices") and events:
            inventory = {"devices": events[-1].get("devices") or [], "subnet": bundle.get("subnet", "")}

    if bundle.get("router_log") and load_router_jsonl:
        router_events.extend(load_router_jsonl(bundle["router_log"]))

    if not inventory.get("devices") and bundle.get("inventory_fixture"):
        inventory = collect_inventory(inject=bundle["inventory_fixture"])

    return observations, inventory, router_events


def run_lan_risk_score_pipeline(bundle: dict[str, Any]) -> dict[str, Any]:
    observations, inventory, router_events = _resolve_observations(bundle)
    devices = inventory.get("devices") or []
    classification = classify_lan_behavior(observations=observations, devices=devices)
    score = compute_privacy_risk_score(
        observations=observations,
        devices=devices,
        router_events=router_events,
        classification=classification.primary_classification,
    )
    return {
        "classification": classification.to_dict(),
        "risk_score": score.to_dict(),
    }


def run_lan_privacy_report_pipeline(
    bundle: dict[str, Any],
    *,
    fmt: str = "json",
    out_dir: str = "",
) -> dict[str, Any]:
    observations, inventory, router_events = _resolve_observations(bundle)
    devices = inventory.get("devices") or []
    classification = classify_lan_behavior(observations=observations, devices=devices)
    score = compute_privacy_risk_score(
        observations=observations,
        devices=devices,
        router_events=router_events,
        classification=classification.primary_classification,
    )
    report = build_lan_privacy_report(
        inventory=inventory,
        observations=observations,
        classification=classification.to_dict(),
        risk_score=score,
        timeline=observations,
    )
    result: dict[str, Any] = {"report": report}
    if fmt in {"markdown", "both"}:
        result["markdown"] = render_lan_privacy_markdown(report)
    if out_dir:
        p = Path(out_dir)
        p.mkdir(parents=True, exist_ok=True)
        if fmt in {"json", "both"}:
            (p / "lan_privacy_report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        if fmt in {"markdown", "both"}:
            (p / "lan_privacy_report.md").write_text(result.get("markdown", ""), encoding="utf-8")
    return result


def run_executive_report_pipeline(
    bundle: dict[str, Any],
    *,
    fmt: str = "both",
    out_dir: str = "",
) -> dict[str, Any]:
    observations, inventory, router_events = _resolve_observations(bundle)
    devices = inventory.get("devices") or []
    classification = classify_lan_behavior(observations=observations, devices=devices)
    score = compute_privacy_risk_score(
        observations=observations,
        devices=devices,
        router_events=router_events,
        classification=classification.primary_classification,
    )
    correlation: dict[str, Any] = {}
    if correlate_host_router and (observations or router_events):
        correlation = correlate_host_router(observations, router_events, devices)

    control_results: list[dict[str, Any]] = []
    if run_lan_control_tests:
        score_payload = {
            **score.to_dict(),
            "primary_classification": classification.primary_classification,
        }
        control_results = [
            r.to_dict()
            for r in run_lan_control_tests(
                inventory=inventory,
                observations=observations,
                router_events=router_events,
                score_result=score_payload,
            )
        ]

    has_router = bool(router_events) or bundle.get("has_router_evidence", False)
    upnp = any(o.get("protocol") in {"SSDP", "UPNP"} for o in observations)
    segmentation = advise_segmentation(
        devices=devices,
        classification=classification.primary_classification,
        has_router_evidence=has_router,
        router_upnp_observed=upnp,
    )

    domains = [
        e.get("domain") or e.get("query", "")
        for e in router_events
        if e.get("event_type") == "dns" or e.get("domain")
    ]

    report = build_executive_report(
        inventory=inventory,
        observations=observations,
        classification=classification.to_dict(),
        risk_score=score.to_dict(),
        control_results=control_results,
        segmentation_advice=segmentation,
        correlation=correlation,
        external_domains=[d for d in domains if d],
    )
    result: dict[str, Any] = {"report": report}
    if out_dir:
        result["written"] = write_executive_report(report, out_dir=out_dir, fmt=fmt)
    elif fmt == "markdown":
        from .executive_report import render_executive_markdown

        result["markdown"] = render_executive_markdown(report)
    return result
