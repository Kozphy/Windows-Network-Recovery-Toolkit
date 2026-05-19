"""Diagnose-first investigation orchestration."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.time_utils import utc_now_iso
from .audit import append_investigation
from .collectors import (
    collect_dev_process_correlation,
    collect_listener_evidence,
    collect_proxy_state,
    load_optional_before_snapshot,
)
from .constants import ATTRIBUTION_LISTENER_ONLY, ENGINE_VERSION, MALWARE_FORBIDDEN, SCHEMA_VERSION
from .hypotheses import build_hypotheses, observations_from_evidence
from .models import ProxyInvestigationResult, new_run_id
from .remediation import remediation_previews
from .report import render_incident_report
from .validation import run_validation


def _attribution_status(listener: dict, dev: dict) -> tuple[str, list[str]]:
    lb = listener.get("localhost_attribution") or {}
    if lb.get("listener_found") and (lb.get("owners") or dev.get("dev_process_rows")):
        return "listener_correlation", [
            "localhost listener correlated with one or more processes",
            ATTRIBUTION_LISTENER_ONLY,
        ]
    return "unknown", [ATTRIBUTION_LISTENER_ONLY, "No reliable registry writer proof in this run."]


def _risk_assessment(proxy: dict, path: dict | None, validation: dict) -> dict[str, Any]:
    composite = (path or {}).get("composite_state")
    enable = proxy.get("proxy_enable")
    if enable != 1:
        return {"operational_risk": "low", "classification_hint": "NO_PROXY_OR_DISABLED"}
    if composite == "LOOPBACK_BROKEN":
        return {"operational_risk": "high", "classification_hint": "LOOPBACK_PROXY_PATH_UNHEALTHY"}
    if composite == "LOOPBACK_OPERATIONAL":
        return {"operational_risk": "low", "classification_hint": "KNOWN_DEV_PROXY_CANDIDATE"}
    if validation.get("https_ok") is False:
        return {"operational_risk": "medium", "classification_hint": "CONNECTIVITY_DEGRADED"}
    return {"operational_risk": "medium", "classification_hint": "UNKNOWN_LOCAL_PROXY"}


def run_proxy_investigation(
    *,
    repo_root: Path,
    run: Callable[..., Any] = subprocess.run,
    write_audit: bool = True,
    write_report_file: bool = True,
) -> ProxyInvestigationResult:
    """Execute full read-only investigation workflow."""
    before = load_optional_before_snapshot(repo_root)
    proxy = collect_proxy_state(run=run)
    listener = collect_listener_evidence(run=run)
    dev = collect_dev_process_correlation(run=run)
    validation, path_assessment = run_validation(run=run)

    hypotheses, competing, primary = build_hypotheses(
        proxy=proxy,
        listener=listener,
        dev=dev,
        validation=validation,
        path_assessment=path_assessment,
        before=before,
    )
    observations = observations_from_evidence(
        proxy=proxy,
        listener=listener,
        dev=dev,
        validation=validation,
        before=before,
    )
    attr_status, attr_notes = _attribution_status(listener, dev)
    previews = remediation_previews()

    verification_strategy = [
        "Compare WinINET vs WinHTTP proxy surfaces.",
        "Run DNS, TCP 443, and HTTPS direct probes.",
        "If loopback proxy: compare HTTPS with proxy vs --noproxy bypass.",
        "Optional: python -m src diagnose-live --proofs for policy-grade contrast.",
        "Optional: enable Sysmon/EventLog registry write telemetry for writer proof.",
        "After preview: python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY --soak-minutes 15",
    ]

    limitations = [
        MALWARE_FORBIDDEN,
        ATTRIBUTION_LISTENER_ONLY,
        "Investigation is read-only unless operator runs previewed remediation separately.",
    ]

    result = ProxyInvestigationResult(
        run_id=new_run_id(),
        timestamp=utc_now_iso(),
        schema_version=SCHEMA_VERSION,
        before_snapshot=before,
        proxy_snapshot=proxy,
        listener_evidence=listener,
        dev_process_evidence=dev,
        validation=validation,
        path_assessment=path_assessment,
        observations=observations,
        hypotheses=hypotheses,
        competing_hypotheses=competing,
        primary_hypothesis_id=primary,
        confidence_boundary=hypotheses[0].confidence if hypotheses else "low",
        verification_strategy=verification_strategy,
        attribution_status=attr_status,  # type: ignore[arg-type]
        attribution_notes=attr_notes,
        risk_assessment=_risk_assessment(proxy, path_assessment, validation),
        remediation_previews=previews,
        limitations=limitations,
        human_report="",
    )
    result.human_report = render_incident_report(result)

    if write_audit:
        append_investigation(result, repo_root=repo_root)
    if write_report_file:
        out_dir = repo_root / "reports" / "proxy_investigations"
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / f"{result.run_id}.md"
        report_path.write_text(result.human_report, encoding="utf-8")
        result.human_report = result.human_report + f"\n\nReport file: {report_path}\n"

    return result
