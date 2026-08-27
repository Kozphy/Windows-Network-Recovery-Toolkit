"""Purple Team CLI — scenarios, validate, run, benchmark, evidence, report."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.purple_team.detection import run_detection
from src.purple_team.evaluation import ABLATION_PRESETS, accumulate_metrics, baseline_compare
from src.purple_team.evidence import verify_evidence_bundle
from src.purple_team.models import FailureCategory, RunState, ScenarioRunResult, StageTiming
from src.purple_team.models.scenario_schema import load_all_scenarios
from src.purple_team.pipeline import (
    dry_run_preview,
    load_scenario_by_id,
    repo_root,
    run_benchmark,
    run_scenario,
)
from src.purple_team.reporting import engineering_report, executive_report, portfolio_summary
from src.purple_team.safety import PURPLE_AUTH_TOKEN
from src.purple_team.simulation import simulate_from_fixture


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def cmd_scenarios_list(_: argparse.Namespace) -> int:
    scenarios = load_all_scenarios()
    rows = [
        {
            "id": s.id,
            "title": s.title,
            "category": s.category,
            "expect_detection": s.expect_detection,
            "rule": s.expected_detection,
        }
        for s in scenarios
    ]
    _print_json({"count": len(rows), "scenarios": rows})
    return 0


def cmd_scenarios_inspect(args: argparse.Namespace) -> int:
    scen = load_scenario_by_id(args.scenario_id)
    _print_json(scen.to_dict())
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    scen = load_scenario_by_id(args.scenario_id)
    preview = dry_run_preview(scen)
    _print_json(preview)
    return 0 if preview["safety"]["allowed"] else 2


def cmd_run(args: argparse.Namespace) -> int:
    scen = load_scenario_by_id(args.scenario_id)
    dry_run = args.dry_run
    authorized = bool(args.authorize)
    if args.confirm == PURPLE_AUTH_TOKEN:
        authorized = True
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else None
    result = run_scenario(
        scen,
        dry_run=dry_run,
        authorized=authorized,
        approved=bool(args.approve),
        environment=args.environment,
        evidence_dir=evidence_dir,
    )
    _print_json(result.to_dict())
    if result.state.value == "DENIED":
        return 2
    if result.false_negative or result.false_positive:
        return 3
    if result.verification and not result.verification.passed and not dry_run:
        return 4
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    ablation = dict(ABLATION_PRESETS.get(args.ablation, {}))
    if args.ablation == "minus_proxy_rule":
        ablation = {"disable_rules": True}
    evidence_dir = Path(args.evidence_dir) if args.evidence_dir else (repo_root() / "reports" / "purple_team")
    if args.no_evidence:
        evidence_dir = None
    report = run_benchmark(
        dry_run=args.dry_run,
        authorized=True,
        evidence_dir=evidence_dir,
        ablation=ablation,
        category=args.category,
    )
    out = {
        **report,
        "portfolio": portfolio_summary(report),
        "engineering": engineering_report(report),
        "executive": executive_report(report),
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    _print_json(out if args.json else {"portfolio": out["portfolio"], "metrics": out["metrics"]})
    # Exit non-zero if any FN in non-ablation full run
    if args.ablation == "full" and out["metrics"]["confusion"]["fn"] > 0:
        return 3
    return 0


def cmd_baselines(args: argparse.Namespace) -> int:
    """Compare baseline_0 / static / single-rule / proposed using same scenarios."""
    scenarios = load_all_scenarios()
    root = repo_root()

    def _blank(scen, fired: bool, expected: bool) -> ScenarioRunResult:
        return ScenarioRunResult(
            run_id=str(uuid.uuid4()),
            scenario_id=scen.id,
            state=RunState.COMPLETED,
            dry_run=True,
            authorized=True,
            transitions=[],
            telemetry=[],
            detections=[],
            risk=None,
            recommendation=None,
            remediation=None,
            verification=None,
            timing=StageTiming(),
            failure_category=FailureCategory.NONE,
            error=None,
            expected_detection=expected,
            detection_matched_expectation=(fired == expected),
            true_positive=bool(expected and fired),
            false_positive=bool((not expected) and fired),
            true_negative=bool((not expected) and (not fired)),
            false_negative=bool(expected and (not fired)),
            evidence_bundle_path=None,
            limitations=[],
        )

    # baseline 0: never detect
    b0 = [_blank(s, False, s.expect_detection) for s in scenarios]

    # baseline 1: static ProxyEnable==1
    b1 = []
    for s in scenarios:
        _, events = simulate_from_fixture(s, run_id="b1", repo_root=root)
        fired = any(
            e.after.get("ProxyEnable") in (1, "1", True) and e.after.get("authorized") is not True
            for e in events
        )
        b1.append(_blank(s, fired, s.expect_detection))

    # baseline 2: DET-PROXY-001 only on all scenarios
    b2 = []
    for s in scenarios:
        _, events = simulate_from_fixture(s, run_id="b2", repo_root=root)
        proxy_scen = replace(s, expected_detection="DET-PROXY-001")
        dets = run_detection(proxy_scen, events)
        fired = any(d.detected for d in dets)
        b2.append(_blank(s, fired, s.expect_detection))

    proposed = run_benchmark(dry_run=True, authorized=True, evidence_dir=None)
    metrics = {
        "baseline_0_no_detection": accumulate_metrics(b0),
        "baseline_1_static_threshold": accumulate_metrics(b1),
        "baseline_2_repo_classifier_proxy": accumulate_metrics(b2),
        "proposed_purple_pipeline": proposed["metrics"],
    }
    out = baseline_compare(metrics)
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    _print_json(out)
    return 0


def cmd_evidence_verify(args: argparse.Namespace) -> int:
    path = Path(args.path)
    bundle = json.loads(path.read_text(encoding="utf-8"))
    result = verify_evidence_bundle(bundle)
    _print_json(result)
    return 0 if result["ok"] else 5


def cmd_report_latest(args: argparse.Namespace) -> int:
    reports = sorted((repo_root() / "reports" / "purple_team").glob("benchmark_*.json"))
    if not reports:
        # run a fresh dry-run benchmark
        out = run_benchmark(dry_run=True, authorized=True, evidence_dir=None)
        _print_json({"portfolio": portfolio_summary(out), "executive": executive_report(out)})
        return 0
    data = json.loads(reports[-1].read_text(encoding="utf-8"))
    _print_json(
        {
            "path": str(reports[-1]),
            "portfolio": data.get("portfolio") or portfolio_summary(data),
            "executive": data.get("executive") or executive_report(data),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="purple",
        description=(
            "Purple Team Security Validation Platform — fixture-driven control "
            "effectiveness experiments (not malware/EDR)."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("scenarios", help="Scenario library commands")
    ssp = sp.add_subparsers(dest="scenarios_cmd", required=True)
    p_list = ssp.add_parser("list", help="List scenarios")
    p_list.set_defaults(func=cmd_scenarios_list)
    p_ins = ssp.add_parser("inspect", help="Inspect a scenario")
    p_ins.add_argument("scenario_id")
    p_ins.set_defaults(func=cmd_scenarios_inspect)

    p_val = sub.add_parser("validate", help="Dry-run validate a scenario")
    p_val.add_argument("scenario_id")
    p_val.add_argument("--dry-run", action="store_true", default=True)
    p_val.set_defaults(func=cmd_validate)

    # Alias style: purple validate scenario <id>
    p_val2 = sub.add_parser("validate-scenario", help="Alias of validate")
    p_val2.add_argument("scenario_id")
    p_val2.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="Run a scenario (default dry-run)")
    p_run.add_argument("scenario_id")
    p_run.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    p_run.add_argument("--dry-run-false", dest="dry_run", action="store_false")
    p_run.add_argument("--authorize", action="store_true")
    p_run.add_argument("--confirm", default="")
    p_run.add_argument("--approve", action="store_true")
    p_run.add_argument("--environment", default="fixture")
    p_run.add_argument("--evidence-dir", default="")
    p_run.set_defaults(func=cmd_run)

    p_bench = sub.add_parser("benchmark", help="Run fixture benchmark suite")
    p_bench.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    p_bench.add_argument("--live-fixture", dest="dry_run", action="store_false")
    p_bench.add_argument("--category", default=None)
    p_bench.add_argument("--ablation", default="full", choices=list(ABLATION_PRESETS) + ["full"])
    p_bench.add_argument("--evidence-dir", default="")
    p_bench.add_argument("--no-evidence", action="store_true")
    p_bench.add_argument("--output", default="")
    p_bench.add_argument("--json", action="store_true")
    p_bench.set_defaults(func=cmd_benchmark)

    p_base = sub.add_parser("baselines", help="Compare detection baselines")
    p_base.add_argument("--output", default="")
    p_base.set_defaults(func=cmd_baselines)

    p_ev = sub.add_parser("evidence", help="Evidence commands")
    sev = p_ev.add_subparsers(dest="evidence_cmd", required=True)
    p_evv = sev.add_parser("verify", help="Verify evidence bundle integrity")
    p_evv.add_argument("path")
    p_evv.set_defaults(func=cmd_evidence_verify)

    p_rep = sub.add_parser("report", help="Reporting")
    srep = p_rep.add_subparsers(dest="report_cmd", required=True)
    p_latest = srep.add_parser("latest", help="Show latest benchmark summary")
    p_latest.set_defaults(func=cmd_report_latest)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
