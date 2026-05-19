"""Backward-compatible bridge from legacy proxy_guard scan payloads."""

from __future__ import annotations

from typing import Any

from proxy_reasoning.audit import append_proxy_reasoning_run
from proxy_reasoning.pipeline import run_proxy_reasoning


def enrich_scan_with_reasoning(
    scan_payload: dict[str, Any],
    *,
    requested_action: str | None = "diagnose",
    audit: bool = True,
) -> dict[str, Any]:
    """Run proxy reasoning on a scan dict and attach ``proxy_reasoning`` + optional audit row.

    Existing ``infer_proxy_risk`` output can remain on the payload; this adds the structured run.
    """
    run = run_proxy_reasoning(payload=scan_payload, requested_action=requested_action)
    if audit:
        append_proxy_reasoning_run(run)
    out = dict(scan_payload)
    out["proxy_reasoning"] = {
        "run_id": run.run_id,
        "accepted_hypothesis": run.accepted_hypothesis,
        "classification": run.entity.trust_risk_attributes.classification,
        "policy_decision": run.policy_decision.decision,
        "user_visible_summary": run.user_visible_summary,
    }
    return out
