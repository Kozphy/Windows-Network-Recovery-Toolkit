"""Command-line interface for the v1 decision architecture (`python -m src`).

This module wires **feature collection** (live Windows probes or fixture JSON),
**deterministic scoring** (`src.decision_engine`), **tiered recommendations**
(`src.recommendations`), **append-only audit/feedback logs** (`src.logging`), and
**artifact persistence** under `reports/` and `logs/` at the toolkit repo root.

Pipeline position:
    ``diagnostics`` → ``decision_engine.scoring`` → ``recommendations`` →
    JSON snapshot + JSONL audit (+ optional repair-safe subprocess launch).

Key invariants:
    Machine identity in audit rows uses a **truncated SHA-256** of
    hostname/release/arch (see `_fingerprint`), not raw hostnames.
    ``repair-safe --apply`` only runs the first **LOW**-risk ``*.bat`` under
    ``scripts/``, after the user types ``RUN``; destructive and firewall resets
    stay out of this path per recommendation policy.

Failure modes:
    Missing ``reports/last_diagnosis.json`` causes ``explain``, ``recommend``,
    ``repair-safe``, and ``export-report`` to raise ``FileNotFoundError`` until
    ``diagnose`` runs successfully.

Audit Notes:
    Each ``diagnose`` appends one line to ``logs/decision_audit.jsonl`` and
    overwrites ``reports/last_diagnosis.json``. Inspect those files to verify
    scores, evidence, and which probe commands ran.

Live (v2) surfaces:
    ``snapshot``, ``proxy-*``, ``diagnose-live``, and structured proxy disable previews append or
    refresh artefacts under ``reports/snapshots/``, ``reports/last_diagnosis_live.json``,
    ``logs/decision_audit.jsonl``, ``logs/network_snapshots.jsonl``, ``logs/repair_audit.jsonl``,
    and optionally ``logs/proxy_guard_events.jsonl`` mirroring README paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .diagnostics.collector import collect_features, load_features_json
from .diagnostics.features import FeatureVector
from .decision_engine.scoring import CauseScore, DecisionResult, explain_primary, score_root_causes
from .command_handlers import (
    cmd_diagnose_live,
    cmd_proxy_disable,
    cmd_proxy_monitor,
    cmd_proxy_owner,
    cmd_proxy_status,
    cmd_repair_apply,
    cmd_repair_preview,
    cmd_snapshot,
)
from .logging.audit import append_jsonl
from .logging.feedback import FeedbackRecord, FeedbackState, append_feedback
from .recommendations.engine import RecommendationBundle, build_recommendations
from .version import SCRIPT_VERSION


def _repo_root(explicit: Path | None) -> Path:
    """Resolve toolkit repository root for report and log paths.

    Args:
        explicit: Optional path from ``--repo-root``; must point at the checkout.

    Returns:
        Absolute resolved ``Path`` to the repo root (parent of ``src/``).

    Raises:
        None.
    """
    if explicit:
        return explicit.resolve()
    return Path(__file__).resolve().parent.parent


def _fingerprint() -> dict[str, str]:
    """Build a non-reversible machine key for audit correlation.

    Returns:
        Mapping with ``host_key_hash16``: first 16 hex chars of SHA-256 over
        ``node|release|machine``. Not a stable hardware ID across reinstalls.

    Raises:
        None.
    """
    raw = f"{platform.node()}|{platform.release()}|{platform.machine()}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return {"host_key_hash16": digest}


def _scores_dict(result: DecisionResult) -> dict[str, float]:
    """Project each cause to its scalar confidence for JSON snapshots.

    Args:
        result: Full scoring outcome from `score_root_causes`.

    Returns:
        Mapping of root-cause key to confidence in ``[0.0, 1.0]``.

    Raises:
        None.
    """
    return {k: v.confidence for k, v in result.scores_by_cause.items()}


def _serialize_cause(score: CauseScore) -> dict[str, Any]:
    """Flatten a scored cause into an audit/export-friendly dictionary.

    Args:
        score: One ``CauseScore`` entry.

    Returns:
        Dict with ``cause``, ``confidence``, ``evidence`` list.

    Raises:
        None.
    """
    return {
        "cause": score.cause,
        "confidence": score.confidence,
        "evidence": list(score.evidence),
    }


def _serialize_bundle(bundle: RecommendationBundle) -> dict[str, Any]:
    """Normalize all recommendation tiers for JSON payloads.

    Args:
        bundle: Tiered suggestion groups from `build_recommendations`.

    Returns:
        Dict with diagnose/repair-safe/guided/advanced arrays matching README naming.

    Raises:
        None.
    """

    def pack(items: tuple[Any, ...]) -> list[dict[str, Any]]:
        return [
            {
                "title": r.title,
                "detail": r.detail,
                "script": r.script_relative,
                "tier": r.tier,
                "risk": r.risk,
                "reversible_notes": r.reversible_notes,
            }
            for r in items
        ]

    return {
        "diagnose": pack(bundle.diagnose),
        "repair_safe": pack(bundle.safe),
        "guided_repair": pack(bundle.guided),
        "advanced_repair": pack(bundle.advanced),
    }


def _build_payload(
    *,
    diagnosis_id: str,
    features: FeatureVector,
    decision: DecisionResult,
    bundle: RecommendationBundle,
    commands_executed: list[dict[str, str]],
) -> dict[str, Any]:
    """Assemble the JSON-serializable snapshot written to reports and audit logs.

    Args:
        diagnosis_id: New UUID string for this run.
        features: Normalized ``FeatureVector`` from probes or fixture.
        decision: Full per-cause scoring outcome.
        bundle: Tiered recommendations for this primary cause.
        commands_executed: Probe command labels from live collection or fixture.

    Returns:
        Dict suitable for ``reports/last_diagnosis.json`` and audit subset.

    Raises:
        None.
    """
    primary = decision.primary()
    return {
        "diagnosis_id": diagnosis_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "machine": _fingerprint(),
        "features": features.to_dict(),
        "confidence_by_cause": _scores_dict(decision),
        "ranked_root_causes": [_serialize_cause(s) for s in decision.ranked()],
        "selected_root_cause": primary.cause,
        "selected_confidence": primary.confidence,
        "selected_evidence": list(primary.evidence),
        "explain_sentence": explain_primary(primary, features),
        "recommendations": _serialize_bundle(bundle),
        "commands_executed": commands_executed,
    }


def _write_last_diagnosis(repo: Path, payload: dict[str, Any]) -> Path:
    """Persist the latest diagnosis snapshot (overwrites prior file).

    Side effects:
        Creates ``reports/`` if missing; overwrites ``last_diagnosis.json``.

    Args:
        repo: Repository root containing ``reports/``.
        payload: Full snapshot from `_build_payload`.

    Returns:
        Path to ``reports/last_diagnosis.json``.

    Raises:
        OSError: If the directory cannot be created or file cannot be written.
        TypeError: If payload is not JSON-serializable.
    """
    reports = repo / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / "last_diagnosis.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _read_last_diagnosis(repo: Path) -> dict[str, Any]:
    """Load the persisted snapshot produced by the last ``diagnose`` command.

    Args:
        repo: Repository root containing ``reports/last_diagnosis.json``.

    Returns:
        Parsed diagnosis payload dictionary.

    Raises:
        FileNotFoundError: If no snapshot exists yet.
        json.JSONDecodeError: If file content is invalid JSON.
    """
    path = repo / "reports" / "last_diagnosis.json"
    if not path.is_file():
        raise FileNotFoundError("No last_diagnosis.json - run diagnose first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _audit(repo: Path, payload: dict[str, Any]) -> None:
    """Append a single diagnosis audit record (append-only JSONL).

    Side effects:
        Creates ``logs/`` if needed; appends one line to
        ``logs/decision_audit.jsonl``.

    Args:
        repo: Repository root.
        payload: Same structure as `_write_last_diagnosis` payload.

    Raises:
        TypeError / OSError: Propagated from `append_jsonl`.
    """
    audit_path = repo / "logs" / "decision_audit.jsonl"
    record = {
        "type": "diagnosis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "diagnosis_id": payload["diagnosis_id"],
        "script_version": SCRIPT_VERSION,
        "machine": payload["machine"],
        "features": payload["features"],
        "scores": payload["confidence_by_cause"],
        "selected_root_cause": payload["selected_root_cause"],
        "confidence": payload["selected_confidence"],
        "evidence": payload["selected_evidence"],
        "recommended_actions": payload["recommendations"],
        "commands_executed": payload["commands_executed"],
    }
    append_jsonl(audit_path, record)


def cmd_diagnose(args: argparse.Namespace) -> int:
    """Run scoring, persist ``last_diagnosis.json``, append audit JSONL, print summary.

    Input assumptions:
        ``--fixture`` points at JSON with ``FeatureVector`` fields (see
        `load_features_json`); live mode assumes Windows tooling used by the
        collector (``ping``, ``nslookup``, ``curl``, PowerShell).

    Raises:
        Propagates exceptions from collection, scoring, or I/O helpers.

    Returns:
        ``0`` on success.

    Audit Notes:
        Review ``logs/decision_audit.jsonl`` for the authoritative append-only
        trail; ``reports/last_diagnosis.json`` is overwritten each run.
    """
    repo = _repo_root(args.repo_root)
    if args.fixture:
        features = load_features_json(Path(args.fixture))
        commands_executed = [
            {"label": "fixture", "cmd": str(Path(args.fixture).resolve())},
        ]
    else:
        features, meta = collect_features(repo_root=repo)
        commands_executed = list(meta.get("commands_executed") or [])

    decision = score_root_causes(features)
    primary = decision.primary()
    bundle = build_recommendations(primary, features, repo)
    diagnosis_id = str(uuid.uuid4())
    payload = _build_payload(
        diagnosis_id=diagnosis_id,
        features=features,
        decision=decision,
        bundle=bundle,
        commands_executed=commands_executed,
    )
    _audit(repo, payload)
    last_path = _write_last_diagnosis(repo, payload)

    human = [
        "=== Windows Network Recovery Toolkit - Decision Architecture ===",
        f"Diagnosis ID: {diagnosis_id}",
        "",
        payload["explain_sentence"],
        "",
        "Root cause ranking (confidence):",
    ]
    for item in payload["ranked_root_causes"][:7]:
        human.append(f"  - {item['cause']}: {item['confidence']:.2f}")
    human.extend(
        [
            "",
            "Tiered recommendations:",
            "  - Diagnose:",
        ]
    )
    for rec in bundle.diagnose:
        human.append(f"    - [{rec.risk}] {rec.title}")
    human.append("  - Repair-safe:")
    for rec in bundle.safe:
        human.append(f"    - [{rec.risk}] {rec.title}")
    human.extend(["  - Guided repair:"])
    for rec in bundle.guided:
        human.append(f"    - [{rec.risk}] {rec.title}")
    human.extend(["  - Advanced repair (manual confirmation outside this CLI):"])
    for rec in bundle.advanced:
        human.append(f"    - [{rec.risk}] {rec.title}")
    human.extend(
        [
            "",
            f"Structured snapshot: {last_path}",
            f"Audit log appended: logs\\decision_audit.jsonl",
        ]
    )

    print("\n".join(human))
    if args.json:
        print("\nJSON_PAYLOAD_START")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("JSON_PAYLOAD_END")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Print the rationale sentence plus primary evidence bullets from the last diagnose.

    Raises:
        FileNotFoundError: When ``reports/last_diagnosis.json`` is absent.
        json.JSONDecodeError: When snapshot content is malformed.

    Returns:
        Shell exit ``0``.
    """
    repo = _repo_root(args.repo_root)
    if getattr(args, "live", False):
        live_path = repo / "reports" / "last_diagnosis_live.json"
        if not live_path.is_file():
            print("No last_diagnosis_live.json — run diagnose-live first.")
            return 1
        payload = json.loads(live_path.read_text(encoding="utf-8"))
        print(payload.get("explain_paragraph") or "No explanation available.")
        print("\nEvidence:")
        for line in payload.get("primary_evidence") or []:
            print(f"- {line}")
        neg = payload.get("negative_evidence") or []
        if neg:
            print("\nNegative evidence (less likely explanations):")
            for line in neg:
                print(f"- {line}")
        return 0

    payload = _read_last_diagnosis(repo)
    sentence = payload.get("explain_sentence", "")
    print(sentence if sentence else "No explanation available.")
    print("\nEvidence:")
    for line in payload.get("selected_evidence", []):
        print(f"- {line}")
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    """Print persisted tier buckets (diagnose / repair-safe / guided / advanced) to stdout.

    Raises:
        FileNotFoundError: When no snapshot exists.
        json.JSONDecodeError: When JSON cannot be decoded.

    Returns:
        Shell exit ``0``.
    """
    repo = _repo_root(args.repo_root)
    if getattr(args, "live", False):
        live_path = repo / "reports" / "last_diagnosis_live.json"
        if not live_path.is_file():
            print("No last_diagnosis_live.json — run diagnose-live first.")
            return 1
        payload = json.loads(live_path.read_text(encoding="utf-8"))
        blob = payload.get("recommendations") or {}
        sections = ("diagnose", "repair_safe", "guided_repair", "advanced_repair")
        for section in sections:
            print(section.upper())
            for item in blob.get(section, []):
                print(f"  [{item.get('risk')}] {item.get('title')}")
                detail = item.get("detail") or ""
                if detail:
                    print(f"      {detail}")
                script = item.get("script")
                if script:
                    print(f"      script: {script}")
            print()
        return 0

    payload = _read_last_diagnosis(repo)
    blob = payload.get("recommendations") or {}
    sections = ("diagnose", "repair_safe", "guided_repair", "advanced_repair")
    for section in sections:
        print(section.upper())
        for item in blob.get(section, []):
            print(f"  [{item.get('risk')}] {item.get('title')}")
            detail = item.get("detail") or ""
            if detail:
                print(f"      {detail}")
            script = item.get("script")
            if script:
                print(f"      script: {script}")
        print()
    return 0


def cmd_repair_safe(args: argparse.Namespace) -> int:
    """Preview safe-tier repairs; optionally launch first LOW-risk ``scripts/*.bat``.

    Side effects (``--apply`` only):
        Spawns PowerShell ``Start-Process -Verb RunAs`` for elevated batch,
        interacts on stdin for ``RUN`` and feedback prompts.

    Raises:
        None directly; subprocess errors surface as failed elevation or denied
        paths (exit codes ``1`` or ``2``).

    Audit Notes:
        Successful ``--apply`` appends interactive feedback via
        `append_feedback`; verify ``logs/decision_feedback.jsonl``.
    """
    repo = _repo_root(args.repo_root)
    payload = _read_last_diagnosis(repo)
    safe_items = payload.get("recommendations", {}).get("repair_safe") or []

    printable = []
    runnable = []
    for item in safe_items:
        printable.append(item)
        if item.get("script") and item.get("risk") == "LOW":
            runnable.append(item)

    if not printable:
        print("No safe-tier recommendations captured in last diagnosis.")
        return 0

    print("repair-safe tier preview (nothing executed yet unless --apply was passed):")
    for item in printable:
        print(f"- [{item.get('risk')}] {item.get('title')}")
        if item.get("script"):
            print(f"    Script: {item['script']}")
        rev = item.get("reversible_notes")
        if rev:
            print(f"    Reversibility: {rev}")

    if not runnable:
        print("\nNothing executable automatically in this tier (advisory-only actions).")
        return 0

    if not getattr(args, "apply", False):
        print('\nAppend `--apply` to optionally launch the first LOW-risk *.bat script after confirming "RUN".')
        return 0

    print(
        "\nSafety policy: destructive operations and firewall resets are never launched from this CLI. "
        "Only LOW-risk scripts listed above are eligible."
    )

    diag_id = payload.get("diagnosis_id", "unknown-diagnosis-id")
    first = runnable[0]
    script_rel = Path(first["script"])
    target = (repo / script_rel).resolve()
    scripts_root = (repo / "scripts").resolve()
    try:
        target.relative_to(scripts_root)
    except ValueError:
        print("Refusing to execute script outside scripts/ directory.")
        return 2

    if not target.is_file():
        print(f"Script not found: {target}")
        return 2

    answer = input("Type RUN to execute the first LOW-risk repair script listed above: ")
    if answer.strip().upper() != "RUN":
        print("Cancelled.")
        return 1

    print(f"\nLaunching elevated batch via PowerShell.Start-Process: {target}")
    ps = (
        f"Start-Process -FilePath '{target}' "
        "-Verb RunAs -Wait"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)

    note = (
        f"Ran safe-tier script `{script_rel}` for diagnosis `{diag_id}` under interactive confirmation.\n\n"
        "Was the connectivity issue resolved? Re-run diagnostics if unsure."
    )
    answer_fix = (
        input("Did that fix your issue? [y/N/unknown]: ").strip().lower() or "unknown"
    )
    if answer_fix in {"y", "yes"}:
        state: FeedbackState = "true"
    elif answer_fix in {"n", "no"}:
        state = "false"
    else:
        state = "unknown"

    user_notes = input("Optional notes (blank to skip): ").strip()
    fb = FeedbackRecord(
        diagnosis_id=diag_id,
        recommended_action=str(script_rel.as_posix()),
        user_feedback_fixed=state,
        notes=user_notes or "post-repair safe-tier feedback",
    )
    append_feedback(repo / "logs" / "decision_feedback.jsonl", fb)
    print(f"Saved feedback entry to logs\\decision_feedback.jsonl (diagnosis_id={diag_id}).")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    """Normalize CLI flags and append one feedback row to ``decision_feedback.jsonl``.

    Parses ``--user-feedback-fixed`` using true/false/unknown aliases documented in README.

    Raises:
        TypeError / OSError: From `append_feedback` if JSON serialization or disk write fails.

    Returns:
        Shell exit ``0``.
    """
    repo = _repo_root(args.repo_root)
    state_raw = args.user_feedback_fixed.lower()
    if state_raw in {"true", "t", "y", "yes"}:
        fb_state: FeedbackState = "true"
    elif state_raw in {"false", "f", "n", "no"}:
        fb_state = "false"
    else:
        fb_state = "unknown"

    record = FeedbackRecord(
        diagnosis_id=args.diagnosis_id,
        recommended_action=args.recommended_action,
        user_feedback_fixed=fb_state,
        notes=args.notes or "",
    )
    append_feedback(repo / "logs" / "decision_feedback.jsonl", record)
    print("Recorded feedback.")
    return 0


def cmd_export_report(args: argparse.Namespace) -> int:
    """Materialize human-readable plaintext from ``last_diagnosis.json``.

    Side effects:
        Writes ``reports/diagnosis_report_<utc_ts>.txt`` unless ``--out`` given.

    Raises:
        FileNotFoundError: If no snapshot exists.
        OSError: If report path cannot be written.
    """
    repo = _repo_root(args.repo_root)
    payload = _read_last_diagnosis(repo)
    ranked = payload.get("ranked_root_causes") or []
    blob = payload.get("recommendations") or {}

    lines: list[str] = []
    lines.extend(
        [
            "WINDOWS NETWORK RECOVERY TOOLKIT — DIAGNOSIS REPORT",
            f"Generated (UTC): {payload.get('generated_at_utc')}",
            f"Toolkit version : {payload.get('script_version')}",
            f"Diagnosis ID    : {payload.get('diagnosis_id')}",
            "",
            "SUMMARY",
            "-------",
            payload.get("explain_sentence") or "",
            "",
            "ROOT CAUSE RANKING",
            "------------------",
        ]
    )
    for idx, item in enumerate(ranked, start=1):
        lines.append(f"{idx}. {item.get('cause')} — {float(item.get('confidence', 0)):.2f}")
        evidence = item.get("evidence") or []
        for bullet in evidence:
            lines.append(f"   • {bullet}")
    lines.extend(
        [
            "",
            "SELECTED HYPOTHESIS",
            "-------------------",
            f"Cause       : {payload.get('selected_root_cause')}",
            f"Confidence  : {float(payload.get('selected_confidence') or 0):.2f}",
            "",
            "EVIDENCE",
            "--------",
        ]
    )
    for bullet in payload.get("selected_evidence") or []:
        lines.append(f"- {bullet}")
    lines.extend(
        [
            "",
            "RECOMMENDED ACTIONS (tiered)",
            "-----------------------------",
            "Modes: diagnose (read-only), repair-safe (reversible/low risk), ",
            "guided repair (confirmation in batch wrappers), ",
            "advanced repair (destructive/policy sensitive — manual only).",
            "",
            "Diagnostics:",
        ]
    )
    for item in blob.get("diagnose", []):
        lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
        if item.get("script"):
            lines.append(f"      Command/script: {item['script']}")
    lines.extend(["", "Repair-safe:"])
    for item in blob.get("repair_safe", []):
        lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
        lines.append(f"      {item.get('detail')}")
        if item.get("script"):
            lines.append(f"      Script: {item['script']}")
        lines.append(f"      Risk: {item.get('risk')} — {item.get('reversible_notes')}")
    lines.extend(["", "Guided repair:"])
    for item in blob.get("guided_repair", []):
        lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
        if item.get("script"):
            lines.append(f"      Script: {item['script']}")
    lines.extend(["", "Advanced repair (never auto-applied):"])
    for item in blob.get("advanced_repair", []):
        lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
        if item.get("script"):
            lines.append(f"      Script reference: {item['script']}")
    lines.extend(
        [
            "",
            "COMMANDS EXECUTED (labels only)",
            "--------------------------------",
        ]
    )
    for cmd in payload.get("commands_executed") or []:
        lines.append(f"- {cmd.get('label')}: {cmd.get('cmd')}")
    lines.extend(
        [
            "",
            "NEXT STEPS",
            "----------",
            "1) Execute the safest matching recommendation first.",
            "2) Record feedback via `python -m src feedback ...` after trying a repair.",
            "3) Re-run diagnose to validate post-change signals.",
            "",
            "NOTICE: This report stays on-disk; upload only if your policy permits.",
        ]
    )

    report_dir = repo / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = Path(args.out) if args.out else report_dir / f"diagnosis_report_{ts}.txt"
    outfile.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {outfile}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Configure argparse for ``python -m src`` dispatch.

    Returns:
        Root parser with mutually exclusive subcommands that map 1:1 to README workflows.

    Raises:
        None.
    """
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Decision architecture CLI for Windows network diagnostics.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Explicit repository root (defaults to toolkit checkout).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_diag = sub.add_parser("diagnose", help="Collect features, score, audit, persist last snapshot.")
    p_diag.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Load features JSON instead of probing live Windows state.",
    )
    p_diag.add_argument("--json", action="store_true", help="Print machine-readable payload after summary.")
    p_diag.set_defaults(func=cmd_diagnose)

    p_exp_sub = sub.add_parser("explain", help="Print rationale for last diagnose or diagnose-live.")
    p_exp_sub.add_argument(
        "--live",
        action="store_true",
        help="Use reports/last_diagnosis_live.json (diagnose-live) instead of last_diagnosis.json.",
    )
    p_exp_sub.set_defaults(func=cmd_explain)

    p_rec_sub = sub.add_parser("recommend", help="Show tiered recommendations from last diagnose run.")
    p_rec_sub.add_argument(
        "--live",
        action="store_true",
        help="Use live v2 recommendations from last_diagnosis_live.json.",
    )
    p_rec_sub.set_defaults(func=cmd_recommend)

    p_safe = sub.add_parser(
        "repair-safe",
        help="Preview safe-tier fixes from the last diagnose run.",
    )
    p_safe.add_argument(
        "--apply",
        action="store_true",
        help="Prompt to launch the first LOW-risk *.bat recommendation (otherwise preview only).",
    )
    p_safe.set_defaults(func=cmd_repair_safe)

    p_fb = sub.add_parser("feedback", help="Persist structured outcome feedback tied to diagnosis_id.")
    p_fb.add_argument("--diagnosis-id", required=True, dest="diagnosis_id")
    p_fb.add_argument("--recommended-action", required=True, dest="recommended_action")
    p_fb.add_argument("--user-feedback-fixed", required=True, dest="user_feedback_fixed")
    p_fb.add_argument("--notes", default="", dest="notes")
    p_fb.set_defaults(func=cmd_feedback)

    p_exp = sub.add_parser("export-report", help="Render a plaintext report under reports/.")
    p_exp.add_argument("--out", type=str, default=None, help="Custom output filename.")
    p_exp.set_defaults(func=cmd_export_report)

    p_ps = sub.add_parser("proxy-status", help="Show HKCU WinINET proxy keys with parsed mode.")
    p_ps.add_argument("--json", dest="emit_json", action="store_true", help="Print merged JSON mapping.")
    p_ps.set_defaults(func=cmd_proxy_status)

    p_po = sub.add_parser("proxy-owner", help="Resolve netstat listener owners for localhost proxy port.")
    p_po.add_argument("--port", type=int, default=None, help="Override port (defaults to parsed ProxyServer).")
    p_po.add_argument("--json", dest="emit_json", action="store_true", help="Emit JSON attribution block.")
    p_po.set_defaults(func=cmd_proxy_owner)

    p_pm = sub.add_parser("proxy-monitor", help="Poll HKCU proxy registry for changes (read-only).")
    p_pm.add_argument("--interval", type=float, default=5.0, help="Seconds between polls (default 5).")
    p_pm.add_argument("--once", action="store_true", help="Single poll then exit.")
    p_pm.add_argument(
        "--jsonl",
        type=str,
        default=None,
        help="Append JSONL events to this path (e.g. logs/proxy_guard_events.jsonl).",
    )
    p_pm.set_defaults(func=cmd_proxy_monitor)

    p_pd = sub.add_parser("proxy-disable", help="Preview/apply safe HKCU WinINET proxy disable (typed confirm).")
    p_pd.add_argument("--dry-run", action="store_true", help="Show planned reg commands only.")
    p_pd.add_argument(
        "--clear-server",
        action="store_true",
        help='Also ``reg delete`` the ProxyServer value after ProxyEnable=0.',
    )
    p_pd.set_defaults(func=cmd_proxy_disable)

    p_sn = sub.add_parser("snapshot", help="Persist full observability JSON under reports/snapshots/.")
    p_sn.set_defaults(func=cmd_snapshot)

    p_dl = sub.add_parser(
        "diagnose-live",
        help="Snapshot + deterministic v2 hypotheses + live recommendations artifact.",
    )
    p_dl.add_argument("--json", dest="emit_json", action="store_true", help="Print JSON payload.")
    p_dl.set_defaults(func=cmd_diagnose_live)

    p_rp = sub.add_parser(
        "repair-preview",
        help="Preview repair tiers from latest live or legacy diagnosis artifact.",
    )
    p_rp.set_defaults(func=cmd_repair_preview)

    p_ra = sub.add_parser(
        "repair-apply",
        help="Interactively launch first LOW-tier script like repair-safe (live or legacy).",
    )
    p_ra.add_argument("--dry-run", action="store_true", help="List candidates without elevation.")
    p_ra.set_defaults(func=cmd_repair_apply)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse argv and delegate to registered subcommand handler.

    Raises:
        SystemExit propagates indirectly through argparse misuse (handled externally).

    Returns:
        Integral POSIX-style exit status from the dispatched command handler.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 1
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
