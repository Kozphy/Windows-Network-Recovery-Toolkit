"""Local diagnostic CLI: collect → classify → plan → optional guarded execution → verify."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .classifier import classify_with_primary
from .collector import collect_evidence, load_evidence_from_json
from .executor import ExecutionResult, RepairExecutor, results_to_payload
from .jsonl_logger import JsonlEventLogger
from .planner import plan
from .schemas import RankedCause, RepairPlan
from .verifier import verification_to_dict, verify_after_repair


def _repo_root(cli_value: Path | None) -> Path:
    if cli_value:
        return cli_value.resolve()
    here = Path(__file__).resolve()
    return here.parent.parent


def _ranked_to_json(ranked: list[RankedCause]) -> list[dict[str, object]]:
    return [
        {"category": r.category, "confidence": r.confidence, "explanation": r.explanation}
        for r in ranked
    ]


def _plan_to_json(p: RepairPlan) -> dict[str, object]:
    return {
        "rationale": p.rationale,
        "verification_hint": p.verification_hint,
        "steps": [
            {
                "script": s.script_relative_path,
                "description": s.description,
                "risk": s.risk,
                "requires_confirmation": s.requires_confirmation,
                "destructive": s.destructive,
            }
            for s in p.steps
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Windows Network Recovery Toolkit — local diagnostic platform",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: parent of agent/).",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Load evidence from JSON instead of live collection (offline mode).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write full structured diagnostic payload to this JSON file.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Append structured JSONL events (default: <repo>/logs/diagnostic_agent.jsonl).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Attempt to execute planned scripts allowed by policy (non-destructive unless confirmed).",
    )
    parser.add_argument(
        "--confirm-script",
        action="append",
        default=[],
        metavar="REL_PATH",
        help="Mark script relative path as confirmed for guarded execution (repeatable).",
    )
    parser.add_argument(
        "--confirm-firewall",
        action="store_true",
        help="Explicit opt-in for reset_firewall.bat only if also listed via --confirm-script.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="After execution (or baseline), run verifier comparing fixture-vs-live when fixture used.",
    )
    args = parser.parse_args(argv)

    root = _repo_root(args.repo_root)
    log_path = args.log_file or (root / "logs" / "diagnostic_agent.jsonl")
    logger = JsonlEventLogger(log_path)

    logger.diagnosis_started(mode="fixture" if args.fixture else "live")

    if args.fixture:
        evidence = load_evidence_from_json(args.fixture)
    else:
        evidence = collect_evidence(repo_root=root)

    summary = {
        k: v
        for k, v in evidence.to_dict().items()
        if k not in ("winhttp_proxy_summary", "recent_processes")
    }
    summary["winhttp_proxy_summary_len"] = len(evidence.winhttp_proxy_summary)
    logger.diagnosis_completed(evidence_summary=summary)

    primary, ranked = classify_with_primary(evidence)
    logger.root_cause_classified(ranked=_ranked_to_json(ranked))

    repair = plan(primary, evidence)
    logger.repair_plan_created(plan=_plan_to_json(repair))

    out_payload: dict[str, object] = {
        "evidence": evidence.to_dict(),
        "ranked_causes": _ranked_to_json(ranked),
        "primary_cause": _ranked_to_json([primary]) if primary else None,
        "repair_plan": _plan_to_json(repair),
    }

    exec_results: list[ExecutionResult] | None = None
    if args.execute:
        confirmed = frozenset(args.confirm_script)
        executor = RepairExecutor(
            root,
            confirm_firewall=args.confirm_firewall,
            confirmed_scripts=confirmed,
        )
        step_paths = [s.script_relative_path for s in repair.steps]
        logger.repair_started(steps=list(step_paths))
        exec_results = executor.execute_plan(repair)
        logger.repair_completed(results=results_to_payload(exec_results))
        out_payload["execution"] = results_to_payload(exec_results)

    if args.verify:

        def _collect_live():
            return collect_evidence(repo_root=root)

        v = verify_after_repair(evidence, _collect_live)
        vdict = verification_to_dict(v)
        logger.verification_completed(verification=vdict)
        out_payload["verification"] = vdict

    text = json.dumps(out_payload, indent=2, ensure_ascii=False)
    print(text)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
