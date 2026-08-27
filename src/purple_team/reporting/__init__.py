"""Engineering, executive, and portfolio reports from benchmark JSON."""

from __future__ import annotations

from typing import Any


def portfolio_summary(benchmark: dict[str, Any]) -> dict[str, Any]:
    metrics = benchmark.get("metrics") or {}
    confusion = metrics.get("confusion") or {}
    operational = metrics.get("operational") or {}
    per = metrics.get("per_scenario") or []
    rules = {r.get("scenario_id") for r in per}
    return {
        "title": "Purple Team Validation Summary",
        "scenarios": benchmark.get("n_scenarios") or len(per),
        "scenario_ids": sorted(rules),
        "detection_recall": confusion.get("recall"),
        "precision": confusion.get("precision"),
        "false_positive_rate": confusion.get("false_positive_rate"),
        "f1": confusion.get("f1"),
        "median_mttd_s": operational.get("median_mttd_s"),
        "verification_success_rate": operational.get("verification_success_rate"),
        "remediation_success_rate": operational.get("remediation_success_rate"),
        "evidence_integrity": "PASS" if not benchmark.get("error_analysis") else "REVIEW",
        "limitations": benchmark.get("limitations") or [],
    }


def engineering_report(benchmark: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for r in benchmark.get("results") or []:
        dets = r.get("detections") or []
        rows.append(
            {
                "scenario": r.get("scenario_id"),
                "telemetry_events": len(r.get("telemetry") or []),
                "rules": [d.get("rule_id") for d in dets],
                "detected": [d.get("detected") for d in dets],
                "latencies": (r.get("timing") or {}),
                "failure_category": r.get("failure_category"),
                "verification": r.get("verification"),
            }
        )
    return rows


def executive_report(benchmark: dict[str, Any]) -> dict[str, Any]:
    port = portfolio_summary(benchmark)
    gaps = []
    for row in (benchmark.get("metrics") or {}).get("per_scenario") or []:
        if row.get("fn"):
            gaps.append(f"Missed detection on {row.get('scenario_id')}")
        if row.get("fp"):
            gaps.append(f"False positive on {row.get('scenario_id')}")
    return {
        "control_tested": "Windows endpoint configuration / path-control validation (fixture lab)",
        "effectiveness": {
            "recall": port.get("detection_recall"),
            "precision": port.get("precision"),
            "fpr": port.get("false_positive_rate"),
            "verification_success": port.get("verification_success_rate"),
        },
        "residual_risk": (
            "Fixture success does not prove production SOC efficacy; "
            "live Windows mutation remains policy-gated outside this suite."
        ),
        "coverage_gap": gaps or ["No FN/FP in this fixture run"],
        "recommended_next_action": (
            "Expand scenario library; keep CI fixture-only; "
            "never enable privileged host-changing scenarios in generic CI."
        ),
    }
