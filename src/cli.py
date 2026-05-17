"""Argparse routers for ``python -m src``; delegates execution to ``src.command_handlers``.

Module responsibility:
    Register subcommands (legacy diagnostics, Proxy Guard, live hypothesis exports, repair previews/replay wrappers,
    proof probes) and map ``Namespace`` objects to handler callables defined outside this module for testability.

System placement:
    Sits atop ``src.diagnostics`` collectors, ``src.hypothesis`` scoring, optional ``src.proof`` checks, persistence
    helpers under ``src.logging``, and toolkit-specific remediation preview logic routed through handlers. FastAPI
    demo APIs live separately under ``backend/``—not imported here unless tests patch.

Pipeline position:
    Legacy path: collectors → ``hypothesis.v1_scoring`` (via ``decision_engine.scoring`` shim) →
    ``src.recommendations.build_recommendations`` → artefacts. Live path: handlers orchestrate snapshots, scoring,
    policy, proof, and audits (see ``cmd_diagnose_live`` docstring).

Side effects:
    This module performs no filesystem writes directly; delegated handlers mutate ``reports/`` and ``logs/`` per command.

Key invariants:
    Audit fingerprints truncate SHA-256 digests rather than emitting raw hostname strings where documented.

    ``repair-safe --apply`` elevates LOW-risk scripts only after ``RUN``; firewall resets remain outside this shortcut.

Failure modes:
    Missing ``reports/last_diagnosis.json`` surfaces ``FileNotFoundError`` for explain/recommend/export until
    ``diagnose`` populates artefacts.

Audit Notes:
    Legacy ``diagnose`` appends ``logs/decision_audit.jsonl`` rows and replaces ``reports/last_diagnosis.json``.

    ``proxy-watch`` tails HKCU churn into ``logs/proxy_guard.jsonl`` (`schema_version=1`) for attribution replays.

    Live commands refresh ``reports/snapshots/*.json``, ``reports/last_diagnosis_live.json``,
    ``logs/decision_runs.jsonl`` (replayable audits), companion JSONL tails, ``logs/network_snapshots.jsonl``,
    ``logs/repair_audit.jsonl`` for guarded registry flows, optionally ``logs/proxy_guard_*`` artefacts.

See Also:
    ``docs/cli_reference.md``, ``docs/decision_engine_v2.md``.
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
from .hypothesis.v1_scoring import CauseScore, DecisionResult, explain_primary, score_root_causes
from .command_handlers import (
    cmd_diagnose_live,
    cmd_replay_live_run,
    cmd_proxy_attribution,
    cmd_proxy_diagnose,
    cmd_proxy_disable,
    cmd_proxy_guard,
    cmd_proxy_monitor,
    cmd_proxy_owner,
    cmd_proxy_report,
    cmd_proxy_watch_report,
    cmd_proxy_rollback,
    cmd_proxy_watch,
    cmd_proxy_snapshot_diff,
    cmd_proxy_snapshot_list,
    cmd_proxy_snapshot_restore,
    cmd_proxy_snapshot_save,
    cmd_proxy_snapshot_show,
    cmd_proxy_status,
    cmd_repair_apply,
    cmd_repair_preview,
    cmd_snapshot,
)
from .network_state.cli_handlers import (
    cmd_network_state_diff,
    cmd_network_state_evidence_import,
    cmd_network_state_report,
    cmd_network_state_restore,
    cmd_network_state_snapshot_list,
    cmd_network_state_snapshot_save,
    cmd_network_state_snapshot_set_default,
    cmd_network_state_snapshot_show,
)
from .command_handlers_safety import (
    cmd_agent_next_step,
    cmd_proxy_config_check,
    cmd_proxy_registry_writer_proof,
    cmd_proxy_restore_lkg,
)
from .logging.audit import append_jsonl
from .logging.feedback import FeedbackRecord, FeedbackState, append_feedback
from .proof.proxy_https import run_localhost_proxy_https_proof
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


def _parse_bool_arg(value: str | bool | None) -> bool:
    """Parse CLI boolean flags that accept explicit true/false strings."""

    if isinstance(value, bool):
        return value
    if value is None:
        return True
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true or false")


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
        raise FileNotFoundError(
            "No reports/last_diagnosis.json - run `python -m src diagnose` first, "
            "or use `diagnose-live` plus `--live` on explain, recommend, repair-safe, and export-report."
        )
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
        Use ``--live`` or ``--proof`` for the v2 live engine (same as ``diagnose-live``);
        ``--proof`` enables the Proof Engine (HTTPS localhost-proxy contrast).

    Raises:
        Propagates exceptions from collection, scoring, or I/O helpers.

    Returns:
        ``0`` on success.

    Audit Notes:
        Review ``logs/decision_audit.jsonl`` for the authoritative append-only
        trail; ``reports/last_diagnosis.json`` is overwritten each run.
    """
    use_live = bool(getattr(args, "live_engine", False) or getattr(args, "proof_engine", False))
    if use_live:
        if getattr(args, "fixture", None):
            print(
                "diagnose: --fixture is only for legacy v1 mode; omit it when using --live or --proof, "
                "or run `python -m src diagnose-live` directly.",
                file=sys.stderr,
            )
            return 2
        if getattr(args, "json", False) and getattr(args, "both_formats", False):
            print("diagnose: use only one of --json or --both with --live/--proof.", file=sys.stderr)
            return 2
        live_ns = argparse.Namespace(
            repo_root=args.repo_root,
            emit_json=bool(getattr(args, "json", False)),
            emit_both=bool(getattr(args, "both_formats", False)),
            live_proofs=bool(getattr(args, "proof_engine", False)),
            replay_run_id=None,
        )
        return cmd_diagnose_live(live_ns)

    if getattr(args, "both_formats", False):
        print(
            "diagnose: --both is for live v2 output; add --live or --proof, or use `diagnose-live --both`.",
            file=sys.stderr,
        )
        return 2

    repo = _repo_root(args.repo_root)
    if not args.fixture and platform.system() != "Windows":
        print(
            "diagnose without --fixture requires Windows (live probes use reg, netsh, PowerShell, etc.). "
            "Use --fixture <features.json> on other platforms.",
            file=sys.stderr,
        )
        return 2
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
        "=== Windows Network Recovery Toolkit — diagnose (legacy v1) ===",
        "",
        "What this does",
        "--------------",
        "Collects connectivity/proxy/feature signals (or loads --fixture JSON), scores fixed v1 root-cause",
        "buckets (DNS, proxy, Winsock, …), persists reports/last_diagnosis.json, and appends logs/decision_audit.jsonl.",
        "Scores are heuristic confidences — not calibrated probabilities.",
        "",
        "For richer loopback-proxy / listener context and policy gates, prefer:",
        "  python -m src diagnose --live",
        "  python -m src diagnose --proof",
        "",
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
    if getattr(args, "json", False):
        print("\nJSON_PAYLOAD_START")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("JSON_PAYLOAD_END")
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Offline replay CLI entry (wraps ``cmd_replay_live_run``)."""
    pid = getattr(args, "replay_positional_id", None)
    rid = (str(pid).strip() if pid is not None else "") or ""
    alt = getattr(args, "replay_flag_id", None)
    if isinstance(alt, str) and alt.strip():
        rid = rid or alt.strip()
    ej = bool(getattr(args, "emit_json", False))
    eb = bool(getattr(args, "emit_both", False))
    if ej and eb:
        print("replay: use only one of --json or --both.", file=sys.stderr)
        return 2
    if not rid:
        print(
            "replay: missing RUN_ID — try: python -m src replay <uuid>   or   python -m src replay --run-id <uuid>",
            file=sys.stderr,
        )
        return 2
    ns = argparse.Namespace(
        repo_root=args.repo_root,
        replay_run_id=rid,
        emit_json=ej,
        emit_both=eb,
    )
    return cmd_replay_live_run(ns)


def cmd_preview(args: argparse.Namespace) -> int:
    """Repair tier preview CLI entry (`preview` ≡ `repair-preview`)."""
    ej = bool(getattr(args, "emit_json_preview", False))
    eb = bool(getattr(args, "emit_both_preview", False))
    if ej and eb:
        print("preview: use only one of --json or --both.", file=sys.stderr)
        return 2
    ns = argparse.Namespace(
        repo_root=args.repo_root,
        emit_json_preview=ej,
        emit_both_preview=eb,
    )
    return cmd_repair_preview(ns)


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
            print("No last_diagnosis_live.json - run diagnose-live first.")
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
            print("No last_diagnosis_live.json - run diagnose-live first.")
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
    if getattr(args, "live", False):
        live_path = repo / "reports" / "last_diagnosis_live.json"
        if not live_path.is_file():
            print("No last_diagnosis_live.json - run diagnose-live first.", file=sys.stderr)
            return 1
        payload = json.loads(live_path.read_text(encoding="utf-8"))
    else:
        payload = _read_last_diagnosis(repo)
    if getattr(args, "apply", False) and platform.system() != "Windows":
        print("repair-safe --apply requires Windows (elevated script launch).", file=sys.stderr)
        return 2
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


def cmd_proof_localhost_https(args: argparse.Namespace) -> int:
    """Run read-only localhost-proxy HTTPS causal contrast (:mod:`src.proof`)."""
    if platform.system() != "Windows":
        print(
            "proof-localhost-https uses Windows registry, netsh, netstat, and curl only.",
            file=sys.stderr,
        )
        return 2
    url = str(getattr(args, "proof_test_url", None) or "https://www.google.com")
    result = run_localhost_proxy_https_proof(test_url=url)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    return 0


def _write_live_diagnosis_report(repo: Path, payload: dict[str, Any], args: argparse.Namespace) -> int:
    """Write plaintext from ``last_diagnosis_live.json`` (v2 engine)."""
    ranked = payload.get("hypotheses_ranked") or []
    blob = payload.get("recommendations") or {}
    lines: list[str] = [
        "WINDOWS NETWORK RECOVERY TOOLKIT — LIVE DIAGNOSIS REPORT (v2)",
        f"Generated (UTC): {payload.get('generated_at_utc')}",
        f"Toolkit version : {payload.get('script_version')}",
        f"Diagnosis ID    : {payload.get('diagnosis_id')}",
        f"Snapshot file   : {payload.get('live_snapshot_ref')}",
        "",
        "SUMMARY",
        "-------",
        str(payload.get("explain_paragraph") or ""),
        "",
        "HYPOTHESES (ranked)",
        "---------------------",
    ]
    for row in ranked[:12]:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"{row.get('rank', '?')}. {row.get('hypothesis')} — {float(row.get('confidence') or 0):.2f}"
        )
        for ev in row.get("evidence") or []:
            lines.append(f"   • {ev}")
    lines.extend(
        [
            "",
            "RECOMMENDED ACTIONS (tiered)",
            "-----------------------------",
            "Diagnostics:",
        ]
    )
    for item in blob.get("diagnose", []):
        if isinstance(item, dict):
            lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
            if item.get("script"):
                lines.append(f"      Command/script: {item['script']}")
    lines.extend(["", "Repair-safe:"])
    for item in blob.get("repair_safe", []):
        if isinstance(item, dict):
            lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
            lines.append(f"      {item.get('detail')}")
            if item.get("script"):
                lines.append(f"      Script: {item['script']}")
    lines.extend(["", "Guided repair:"])
    for item in blob.get("guided_repair", []):
        if isinstance(item, dict):
            lines.append(f"  • [{item.get('risk')}] {item.get('title')}")
            if item.get("script"):
                lines.append(f"      Script: {item['script']}")
    lines.extend(["", "Advanced repair (never auto-applied):"])
    for item in blob.get("advanced_repair", []):
        if isinstance(item, dict):
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
        if isinstance(cmd, dict):
            lines.append(f"- {cmd.get('label')}: {cmd.get('cmd')}")
    lines.extend(
        [
            "",
            "NEXT STEPS",
            "----------",
            "1) Execute the safest matching recommendation first.",
            "2) Record feedback via `python -m src feedback ...` after trying a repair.",
            "3) Re-run diagnose-live to validate post-change signals.",
            "",
            "NOTICE: This report stays on-disk; upload only if your policy permits.",
        ]
    )
    report_dir = repo / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = Path(args.out) if args.out else report_dir / f"diagnosis_live_report_{ts}.txt"
    outfile.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {outfile}")
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
    if getattr(args, "live", False):
        live_path = repo / "reports" / "last_diagnosis_live.json"
        if not live_path.is_file():
            print("No last_diagnosis_live.json - run diagnose-live first.", file=sys.stderr)
            return 1
        payload = json.loads(live_path.read_text(encoding="utf-8"))
        return _write_live_diagnosis_report(repo, payload, args)
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

    p_diag = sub.add_parser(
        "diagnose",
        help="Diagnose connectivity: legacy v1 scoring, or live v2 via --live / --proof.",
        description=(
            "Default (no flags): collects signals, applies v1 root-cause scores, writes "
            "`reports/last_diagnosis.json`, appends `logs/decision_audit.jsonl`. "
            "`--live`: same snapshot + v2 engine as `diagnose-live`. "
            "`--proof`: live run plus Proof Engine (HTTPS localhost-proxy contrast). "
            "With `--live`/`--proof`, `--json` streams JSON-only (API-friendly); "
            "`--both` adds a human preamble before JSON_PAYLOAD delimiters."
        ),
    )
    p_diag.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Load features JSON instead of probing (legacy v1 only; incompatible with --live/--proof).",
    )
    p_diag.add_argument(
        "--live",
        dest="live_engine",
        action="store_true",
        help="Run live v2 diagnosis (snapshot + hypotheses + policy); alias of `diagnose-live`.",
    )
    p_diag.add_argument(
        "--proof",
        dest="proof_engine",
        action="store_true",
        help="Live v2 with Proof Engine enabled (implies --live).",
    )
    p_diag.add_argument(
        "--json",
        action="store_true",
        help=(
            "Legacy v1: append JSON payload after human text (JSON_PAYLOAD_* delimiters). "
            "Live (`--live`/`--proof`): JSON only on stdout — same behavior as `diagnose-live --json`."
        ),
    )
    p_diag.add_argument(
        "--both",
        dest="both_formats",
        action="store_true",
        help="With --live/--proof only: explainable prose, then JSON block (exclusive with --json).",
    )
    p_diag.set_defaults(func=cmd_diagnose, live_engine=False, proof_engine=False, both_formats=False)

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
        "--live",
        action="store_true",
        help="Use reports/last_diagnosis_live.json (diagnose-live) instead of last_diagnosis.json.",
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
    p_exp.add_argument(
        "--live",
        action="store_true",
        help="Use reports/last_diagnosis_live.json (diagnose-live) instead of last_diagnosis.json.",
    )
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

    p_pxw = sub.add_parser(
        "proxy-watch",
        help="Poll WinINET HKCU state, diff, attribute processes, append logs/proxy_guard.jsonl (no silent rollback).",
    )
    p_pxw.add_argument("--interval", type=float, default=5.0, help="Seconds between polls (default 5).")
    p_pxw.add_argument("--once", action="store_true", help="Poll twice (detect first change if any) then exit.")
    p_pxw.add_argument(
        "--evidence-csv",
        type=str,
        default=None,
        dest="proxy_watch_evidence_csv",
        metavar="PATH",
        help="Optional Procmon CSV export (Internet Settings path rows) to modestly boost attribution confidence.",
    )
    p_pxw.set_defaults(func=cmd_proxy_watch)

    p_pxrep = sub.add_parser(
        "proxy-report",
        help="Summarize recent proxy-watch rows from logs/proxy_guard.jsonl.",
    )
    p_pxrep.add_argument("--tail", type=int, default=50, dest="proxy_report_tail", help="Inspect last N rows.")
    p_pxrep.add_argument("--json", dest="emit_json", action="store_true", help="Emit JSON summary + rows.")
    p_pxrep.set_defaults(func=cmd_proxy_report)

    p_pxw = sub.add_parser(
        "proxy-watch-report",
        help="Human-readable report for reports/proxy_guard_watch.jsonl (Windows).",
    )
    p_pxw.add_argument("--tail", type=int, default=10, dest="proxy_watch_tail", help="Last N events (default 10).")
    p_pxw.add_argument("--json", dest="emit_json", action="store_true", help="Emit raw JSON instead of text.")
    p_pxw.set_defaults(func=cmd_proxy_watch_report)

    p_pg = sub.add_parser(
        "proxy-guard",
        help="Policy-aware proxy monitor with optional WinINET/WinHTTP rollback (Windows).",
    )
    p_pg.add_argument("--interval", type=float, default=5.0, help="Seconds between polls (default 5).")
    p_pg.add_argument("--once", action="store_true", help="Single poll then exit (initial baseline snapshot).")
    p_pg.add_argument(
        "--auto-rollback",
        action="store_true",
        help="On blocked changes, restore prior HKCU/WinHTTP snapshot via reg/netsh (still respects dry-run gates).",
    )
    p_pg.add_argument(
        "--rollback",
        action="store_true",
        dest="cli_rollback",
        help="Enable rollback planning/execution like --auto-rollback; live HKCU writes require --rollback-confirm RESTORE_PROXY unless using --auto-rollback alone.",
    )
    p_pg.add_argument(
        "--rollback-confirm",
        type=str,
        default="",
        dest="rollback_confirm_phrase",
        metavar="PHRASE",
        help='When using --rollback (not --auto-rollback), live restore requires phrase "RESTORE_PROXY".',
    )
    p_pg.add_argument(
        "--policy",
        type=str,
        default=None,
        help="JSON policy file (defaults to shared/proxy_guard_policy.example.json under repo root).",
    )
    p_pg.add_argument(
        "--jsonl",
        type=str,
        default=None,
        help="Append control-plane JSONL (default logs/proxy_guard_control.jsonl).",
    )
    p_pg.add_argument(
        "--dry-run-rollback",
        action="store_true",
        help="Log rollback commands without executing reg/netsh (testing).",
    )
    p_pg.add_argument(
        "--config",
        type=str,
        default=None,
        dest="service_config",
        help="Optional JSON service config (probe retries, rollback cooldown — see docs/proxy_guard.md).",
    )
    p_pg.add_argument(
        "--structured-log",
        type=str,
        default=None,
        dest="structured_log",
        help="Append JSON-lines operational log (same schema as stderr; optional file sink).",
    )
    p_pg.add_argument(
        "--dry-run",
        action="store_true",
        dest="proxy_guard_dry_run",
        help="Prevent live HKCU / WinHTTP restore even when auto-rollback is enabled (audit + dry commands only).",
    )
    p_pg.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Print machine JSON on each change instead of human-readable text.",
    )
    p_pg.add_argument(
        "--trust-current",
        action="store_true",
        dest="trust_current_lkg",
        help="Persist the first captured snapshot under reports/proxy_guard_lkg.json as last-known-good.",
    )
    p_pg.add_argument(
        "--show-lkg",
        action="store_true",
        dest="show_lkg",
        help="Print reports/proxy_guard_lkg.json and exit.",
    )
    p_pg.add_argument(
        "--clear-lkg",
        action="store_true",
        dest="clear_lkg",
        help="Remove reports/proxy_guard_lkg.json and exit.",
    )
    p_pg.add_argument(
        "--attribution-mode",
        choices=("auto", "best-effort", "eventlog"),
        default="auto",
        help="Prefer Sysmon EventID 13 (auto/eventlog) or skip to listen-owner heuristics (best-effort).",
    )
    p_pg.add_argument(
        "--restore-git-npm-env",
        action="store_true",
        dest="restore_git_npm_env",
        help="Reserved — currently guarded off inside rollback until an explicit confirmation story exists.",
    )
    p_pg.add_argument(
        "--known-good",
        type=str,
        default=None,
        metavar="NAME",
        help=(
            "On rollback, restore this named snapshot: prefer logs/network_state_snapshots.jsonl "
            "(Network State Manager), else logs/proxy_known_good_snapshots.jsonl (HKCU/Git/npm/env/WinHTTP)."
        ),
    )
    p_pg.add_argument(
        "--evidence-csv",
        type=str,
        default=None,
        dest="proxy_guard_evidence_csv",
        metavar="PATH",
        help="Optional Procmon CSV export (RegSetValue on Internet Settings proxy keys) for layered attribution.",
    )
    p_pg.add_argument(
        "--attribution-window",
        type=int,
        default=90,
        dest="proxy_guard_attribution_seconds",
        metavar="SECONDS",
        help="Sysmon Event 13 / rough Procmon time gate in seconds (default 90; minimum 60 in config clamp).",
    )
    p_pg.set_defaults(func=cmd_proxy_guard)

    p_pss = sub.add_parser(
        "proxy-snapshot",
        help="Named last-known-good proxy snapshots (capture, compare, restore allowlisted surfaces).",
    )
    p_pss_sub = p_pss.add_subparsers(dest="proxy_snapshot_cmd", required=True)

    p_pss_sv = p_pss_sub.add_parser(
        "save",
        help="Capture HKCU WinINET, WinHTTP, Git, npm, and user proxy env into logs/proxy_known_good_snapshots.jsonl.",
    )
    p_pss_sv.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME", help="Snapshot label.")
    p_pss_sv.add_argument(
        "--as-default",
        action="store_true",
        help="Also write config/last_known_good_proxy.json pointing at this snapshot.",
    )
    p_pss_sv.set_defaults(func=cmd_proxy_snapshot_save)

    p_pss_ls = p_pss_sub.add_parser("list", help="List snapshot names from JSONL plus default-config flag.")
    p_pss_ls.set_defaults(func=cmd_proxy_snapshot_list)

    p_pss_sh = p_pss_sub.add_parser("show", help="Print the latest JSONL record for --name.")
    p_pss_sh.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_pss_sh.set_defaults(func=cmd_proxy_snapshot_show)

    p_pss_df = p_pss_sub.add_parser("diff", help="Compare current machine state vs saved snapshot (changed fields only).")
    p_pss_df.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_pss_df.set_defaults(func=cmd_proxy_snapshot_diff)

    p_pss_rs = p_pss_sub.add_parser(
        "restore",
        help="Restore allowlisted proxy settings from snapshot (dry-run unless --confirm RESTORE_KNOWN_GOOD_PROXY).",
    )
    p_pss_rs.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_pss_rs.add_argument("--dry-run", action="store_true", help="Force preview only even if confirm phrase is set.")
    p_pss_rs.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="confirm_phrase",
        metavar="PHRASE",
        help='Live restore requires exact phrase RESTORE_KNOWN_GOOD_PROXY; omit for dry-run preview only.',
    )
    p_pss_rs.set_defaults(func=cmd_proxy_snapshot_restore)

    p_pxdiag = sub.add_parser(
        "proxy-diagnose",
        help="WinINET-focused diagnose with FailureBlocks and optional localhost listener attribution.",
    )
    p_pxdiag.add_argument("--json", dest="emit_json", action="store_true", help="Emit machine-readable JSON.")
    p_pxdiag.add_argument(
        "--skip-listener-probe",
        action="store_true",
        help="Skip netstat/tasklist attribution (offline / faster CI).",
    )
    p_pxdiag.set_defaults(func=cmd_proxy_diagnose)

    p_pxattr = sub.add_parser(
        "proxy-attribution",
        help="Structured localhost proxy listener attribution (netstat + tasklist + CIM).",
    )
    p_pxattr.add_argument("--json", dest="emit_json", action="store_true", help="Emit JSON only.")
    p_pxattr.add_argument("--port", type=int, default=None, help="Override proxy port parsing.")
    p_pxattr.set_defaults(func=cmd_proxy_attribution)

    p_pxrb = sub.add_parser(
        "proxy-rollback",
        help="Restore HKCU WinINET from snapshots JSONL (--snapshot-id) or a known-good JSON file (--from-snapshot).",
    )
    g_rb = p_pxrb.add_mutually_exclusive_group(required=True)
    g_rb.add_argument("--snapshot-id", dest="snapshot_id", metavar="ID", help="UUID from logs/proxy_snapshots.jsonl.")
    g_rb.add_argument(
        "--from-snapshot",
        type=str,
        dest="rollback_from_snapshot",
        metavar="PATH",
        help="Path to known-good JSON ({\"snapshot\":{...}} or flat ProxySnapshot dict). Live apply needs --confirm RESTORE_PROXY_SNAPSHOT_FILE.",
    )
    p_pxrb.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="rollback_file_confirm_phrase",
        metavar="PHRASE",
        help="With --from-snapshot: typed phrase RESTORE_PROXY_SNAPSHOT_FILE enables live restore (omit for preview).",
    )
    p_pxrb.add_argument("--dry-run", action="store_true", help="Show argv preview only.")
    p_pxrb.set_defaults(snapshot_id=None, func=cmd_proxy_rollback)

    p_pd = sub.add_parser("proxy-disable", help="Preview/apply safe HKCU WinINET proxy disable (typed confirm).")
    p_pd.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        type=_parse_bool_arg,
        help="Preview only by default. Use --dry-run false with --confirm DISABLE_WININET_PROXY to apply.",
    )
    p_pd.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="confirm_phrase",
        metavar="PHRASE",
        help="Live apply requires exact phrase DISABLE_WININET_PROXY.",
    )
    p_pd.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_pd.add_argument(
        "--clear-server",
        action="store_true",
        help='Also ``reg delete`` the ProxyServer value after ProxyEnable=0.',
    )
    p_pd.set_defaults(func=cmd_proxy_disable)

    p_proxy = sub.add_parser("proxy", help="Grouped proxy commands.")
    p_proxy_sub = p_proxy.add_subparsers(dest="proxy_cmd", required=True)
    p_proxy_disable = p_proxy_sub.add_parser(
        "disable",
        help="Preview/apply safe HKCU WinINET proxy disable (default dry-run).",
    )
    p_proxy_disable.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        type=_parse_bool_arg,
        help="Preview only by default. Use --dry-run false with --confirm DISABLE_WININET_PROXY to apply.",
    )
    p_proxy_disable.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="confirm_phrase",
        metavar="PHRASE",
        help="Live apply requires exact phrase DISABLE_WININET_PROXY.",
    )
    p_proxy_disable.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_proxy_disable.add_argument(
        "--clear-server",
        action="store_true",
        help="Preview the older ProxyServer delete path; live apply is blocked by the allowlist.",
    )
    p_proxy_disable.set_defaults(func=cmd_proxy_disable)

    p_proxy_restore_lkg = p_proxy_sub.add_parser(
        "restore-lkg",
        help="Restore HKCU WinINET proxy fields from latest known-good snapshot (typed-confirmation gated; default dry-run).",
    )
    p_proxy_restore_lkg.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        type=_parse_bool_arg,
        help="Preview only by default. Use --dry-run false with --confirm RESTORE_WININET_PROXY_FROM_LKG to apply.",
    )
    p_proxy_restore_lkg.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="confirm_phrase",
        metavar="PHRASE",
        help="Live restore requires exact phrase RESTORE_WININET_PROXY_FROM_LKG.",
    )
    p_proxy_restore_lkg.add_argument(
        "--name",
        type=str,
        default="",
        dest="snapshot_name",
        metavar="NAME",
        help="Optional snapshot label; defaults to the youngest stored snapshot.",
    )
    p_proxy_restore_lkg.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_proxy_restore_lkg.set_defaults(func=cmd_proxy_restore_lkg)

    p_proxy_cc = p_proxy_sub.add_parser(
        "config-check",
        help="Read-only proxy config audit (WinINET, WinHTTP, Git, npm, env, browser policy).",
    )
    p_proxy_cc.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_proxy_cc.set_defaults(func=cmd_proxy_config_check)

    p_proxy_rwp = p_proxy_sub.add_parser(
        "registry-writer-proof",
        help="Read-only Sysmon / Security 4657 / Procmon CSV evidence for WinINET proxy registry writes.",
    )
    p_proxy_rwp.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_proxy_rwp.add_argument("--since-seconds", type=int, default=120, help="Lookback window in seconds (default 120).")
    p_proxy_rwp.add_argument(
        "--procmon-csv",
        type=str,
        default=None,
        dest="procmon_csv",
        metavar="PATH",
        help="Optional Procmon CSV export to enrich evidence.",
    )
    p_proxy_rwp.set_defaults(func=cmd_proxy_registry_writer_proof)

    p_agent = sub.add_parser("agent", help="Bounded local agent surfaces (recommendation only; no mutation).")
    p_agent_sub = p_agent.add_subparsers(dest="agent_cmd", required=True)
    p_agent_ns = p_agent_sub.add_parser(
        "next-step",
        help="Recommend the next read-only probe or preview action based on the latest stored diagnosis.",
    )
    p_agent_ns.add_argument(
        "--goal",
        type=str,
        default="suggest_next_probe",
        choices=(
            "suggest_next_probe",
            "rank_hypotheses",
            "explain_risk",
            "recommend_preview_action",
            "summarize_audit",
            "identify_missing_evidence",
        ),
        help="Bounded planner goal.",
    )
    p_agent_ns.add_argument(
        "--run-id",
        type=str,
        default="",
        dest="run_id",
        metavar="DIAGNOSIS_ID",
        help="Optional diagnosis run id; defaults to the latest stored diagnosis.",
    )
    p_agent_ns.add_argument("--json", dest="emit_json", action="store_true", help="Emit structured JSON only.")
    p_agent_ns.set_defaults(func=cmd_agent_next_step)

    p_sn = sub.add_parser("snapshot", help="Persist full observability JSON under reports/snapshots/.")
    p_sn.set_defaults(func=cmd_snapshot)

    p_dl = sub.add_parser(
        "diagnose-live",
        help="Snapshot + deterministic v2 hypotheses + live recommendations (or offline --replay run_id).",
        description=(
            "Preferred long-form name for the live stack. Equivalent to `python -m src diagnose --live`; "
            "add `--replay RUN_ID` (or Top-level command `replay`) for offline parity checks."
        ),
    )
    p_dl.add_argument("--json", dest="emit_json", action="store_true", help="Stdout JSON payload only.")
    p_dl.add_argument(
        "--both",
        dest="emit_both",
        action="store_true",
        help="Human-readable summary first, then JSON_PAYLOAD_START … JSON_PAYLOAD_END wrapping the same payload.",
    )
    p_dl.add_argument(
        "--proofs",
        dest="live_proofs",
        action="store_true",
        help="Run read-only Proof Engine (HTTPS via localhost proxy vs bypass) and attach hypothesis_decisions.",
    )
    p_dl.add_argument(
        "--replay",
        dest="replay_run_id",
        default=None,
        metavar="RUN_ID",
        help=(
            "Offline: load logs/decision_runs.jsonl by run_id — same as `python -m src replay RUN_ID`. "
            "Use `--json` for JSON-only tooling output; `--both` for human plus JSON markers."
        ),
    )
    p_dl.set_defaults(func=cmd_diagnose_live, live_proofs=False, emit_both=False)

    p_replay_cli = sub.add_parser(
        "replay",
        help="Offline replay: parity check a saved live run from logs/decision_runs.jsonl.",
        description=(
            "Recomputes deterministic scores from archived observations — no probes. "
            "RUN_ID equals `diagnosis_id` / `run_id` in the audit row. "
            "`--json` prints the structured parity object only; `--both` emits narration then JSON_PAYLOAD delimiters. "
            "Positional RUN_ID overrides `--run-id` when both are set."
        ),
    )
    p_replay_cli.add_argument(
        "replay_positional_id",
        nargs="?",
        default=None,
        metavar="RUN_ID",
        help="UUID/key from logs/decision_runs.jsonl (same as diagnose-live `--replay`).",
    )
    p_replay_cli.add_argument(
        "--run-id",
        dest="replay_flag_id",
        default=None,
        metavar="RUN_ID",
        help="Same UUID as positional RUN_ID; ignored when positional is provided.",
    )
    p_replay_cli.add_argument("--json", dest="emit_json", action="store_true", help="JSON report on stdout only.")
    p_replay_cli.add_argument(
        "--both",
        dest="emit_both",
        action="store_true",
        help="Human execution-flow text, then extractable JSON between JSON_PAYLOAD_* lines.",
    )
    p_replay_cli.set_defaults(func=cmd_replay, emit_json=False, emit_both=False)

    p_plhp = sub.add_parser(
        "proof-localhost-https",
        help="Proof Engine: causal HTTPS probe via localhost proxy vs curl --noproxy (no config changes).",
    )
    p_plhp.add_argument(
        "--url",
        dest="proof_test_url",
        default="https://www.google.com",
        metavar="HTTPS_URL",
        help="Target URL for HTTPS contrast probes (default: %(default)s).",
    )
    p_plhp.set_defaults(func=cmd_proof_localhost_https)

    p_pv = sub.add_parser(
        "preview",
        help="Explainable read-only preview of tiered repairs from latest diagnosis (no scripts run).",
        description=(
            "Shows diagnose / repair_safe / guided / advanced tiers from `last_diagnosis_live.json` "
            "(preferred) or legacy `last_diagnosis.json`. Use `--both` when you want human text plus extractable JSON."
        ),
    )
    p_pv.add_argument("--json", dest="emit_json_preview", action="store_true", help="Structured tiers JSON only.")
    p_pv.add_argument(
        "--both",
        dest="emit_both_preview",
        action="store_true",
        help="Tier list for humans, then JSON_PAYLOAD markers with the `--json` object.",
    )
    p_pv.set_defaults(func=cmd_preview, emit_json_preview=False, emit_both_preview=False)

    p_rp = sub.add_parser(
        "repair-preview",
        help="Synonym for `preview` — tiered repairs from latest diagnosis artifact.",
    )
    p_rp.add_argument("--json", dest="emit_json_preview", action="store_true", help="Structured JSON only.")
    p_rp.add_argument("--both", dest="emit_both_preview", action="store_true", help="Human tiers + JSON delimiters.")
    p_rp.set_defaults(func=cmd_repair_preview, emit_json_preview=False, emit_both_preview=False)

    p_ra = sub.add_parser(
        "repair-apply",
        help="Interactively launch first LOW-tier script like repair-safe (live or legacy).",
    )
    p_ra.add_argument("--dry-run", action="store_true", help="List candidates without elevation.")
    p_ra.set_defaults(func=cmd_repair_apply)

    p_ns = sub.add_parser(
        "network-state",
        help="Network State Manager: named snapshots, drift diff, policy, reports, preview/restore.",
    )
    ns_sub = p_ns.add_subparsers(dest="network_state_cmd", required=True)

    p_nss = ns_sub.add_parser("snapshot", help="Save or manage known-good snapshots.")
    nss_sub = p_nss.add_subparsers(dest="network_state_snapshot_cmd", required=True)

    p_nss_sv = nss_sub.add_parser(
        "save",
        help="Capture WinINET, WinHTTP, Git, npm, user proxy env → logs/network_state_snapshots.jsonl.",
    )
    p_nss_sv.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME", help="Profile label.")
    p_nss_sv.set_defaults(func=cmd_network_state_snapshot_save)

    p_nss_ls = nss_sub.add_parser("list", help="List profile names + default flag.")
    p_nss_ls.set_defaults(func=cmd_network_state_snapshot_list)

    p_nss_sh = nss_sub.add_parser("show", help="Print latest JSONL record for --name.")
    p_nss_sh.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_nss_sh.set_defaults(func=cmd_network_state_snapshot_show)

    p_nss_sd = nss_sub.add_parser("set-default", help="Write config/network_state_default.json from latest --name.")
    p_nss_sd.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_nss_sd.set_defaults(func=cmd_network_state_snapshot_set_default)

    p_nsdiff = ns_sub.add_parser("diff", help="Compare current machine vs saved snapshot or default profile.")
    g_ns = p_nsdiff.add_mutually_exclusive_group(required=True)
    g_ns.add_argument("--name", dest="snapshot_name", metavar="NAME")
    g_ns.add_argument("--default", dest="use_default", action="store_true", help="Use config/network_state_default.json.")
    p_nsdiff.add_argument("--json", dest="json_out", action="store_true")
    p_nsdiff.set_defaults(snapshot_name=None, use_default=False, func=cmd_network_state_diff)

    p_ns_rep = ns_sub.add_parser("report", help="Summarize recent events + drift vs default.")
    p_ns_rep.add_argument("--since", default="24h", help="Window like 24h, 7d, 30m.")
    p_ns_rep.add_argument("--json", dest="json_out", action="store_true")
    p_ns_rep.set_defaults(func=cmd_network_state_report)

    p_ns_rs = ns_sub.add_parser(
        "restore",
        help='Preview or restore named snapshot (live requires --confirm RESTORE_NETWORK_STATE; default is dry-run preview).',
    )
    p_ns_rs.add_argument("--name", required=True, dest="snapshot_name", metavar="NAME")
    p_ns_rs.add_argument("--dry-run", action="store_true", help="Force preview only.")
    p_ns_rs.add_argument(
        "--confirm",
        type=str,
        default="",
        dest="confirm_phrase",
        metavar="PHRASE",
        help='Typed phrase RESTORE_NETWORK_STATE enables live argv-only restores.',
    )
    p_ns_rs.set_defaults(func=cmd_network_state_restore)

    p_ns_ev = ns_sub.add_parser("evidence", help="Import optional Procmon-style CSV (no tracers installed).")
    ev_sub = p_ns_ev.add_subparsers(dest="network_state_evidence_cmd", required=True)
    p_ns_ev_imp = ev_sub.add_parser("import", help="Append normalized rows to logs/network_state_evidence.jsonl.")
    p_ns_ev_imp.add_argument("--file", required=True, dest="evidence_file", metavar="PATH")
    p_ns_ev_imp.set_defaults(func=cmd_network_state_evidence_import)

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
    try:
        return int(handler(args))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in diagnosis snapshot: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
