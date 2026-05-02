"""Argparse-backed handlers for live observability and Proxy Guard CLIs.

This module sits beside ``src.cli`` (which imports these callables into subparsers).

Responsibilities:
    Normalize operator-facing flows for HKCU proxy inspection, attribution, monitoring,
    safe registry mutation, correlated snapshots, v2 hypothesis exports, and repair previews.

Key invariants:
    Writes never occur during ``proxy-disable --dry-run`` or ``repair-apply --dry-run``.
    ``emit_json`` branches emit **only** JSON to stdout where implemented (machine-readable).
    Fingerprints reuse SHA-256 truncation like legacy diagnosis (no raw hostnames in payloads).

Audit Notes:
    Inspect ``logs/repair_audit.jsonl`` after ``proxy-disable``,
    ``logs/decision_audit.jsonl`` ``type=diagnosis_live`` rows after ``diagnose-live``,
    and ``reports/last_diagnosis_live.json`` for structured recommendations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from .core.jsonl import append_jsonl as append_jsonl_core
from .core.models import registry_with_parsed
from .core.time_utils import utc_now_iso
from .decision_engine.explanations import primary_explanation_paragraph
from .decision_engine.live_scoring import ranked_dicts, score_live_snapshot
from .decision_engine.recommendations import live_recommendation_bundle
from .logging.feedback import FeedbackRecord, FeedbackState, append_feedback
from .observability.snapshot import build_live_network_snapshot
from .proxy_guard.failure_block import build_proxy_failure_blocks
from .proxy_guard.localhost_attribution import build_localhost_proxy_attribution
from .proxy_guard.owner import attribution_payload
from .proxy_guard.parser import parse_proxy_server, summarize_proxy_risk
from .proxy_guard.registry import read_proxy_registry
from .proxy_guard.repair_snapshots import (
    append_proxy_snapshots_jsonl,
    build_restore_reg_argv,
    build_rollback_plan,
    capture_wininet_snapshot,
    load_snapshot_record_by_id,
    merge_snapshot_payload,
    snapshot_confirmation_phrase,
)
from .proxy_guard.verification import verify_proxy_disabled
from .proxy_guard.config import build_service_config
from .proxy_guard.policy import load_proxy_guard_policy
from .proxy_guard.snapshot_capture import load_lkg_snapshot
from .proxy_guard.service import run_proxy_guard_service
from .proxy_guard.remediation import CONFIRMATION_PHRASE, build_user_proxy_disable_mutations
from .proxy_guard.watcher import monitor_proxy_registry
from .repair.executor import apply_mutations, apply_reg_argv_sequences
from .repair.policy import assert_no_firewall_reset_in_preview
from .repair.preview import summarize_mutations_plaintext
from .version import SCRIPT_VERSION


def _repo_root(cli: Path | None) -> Path:
    """Resolve checkout root (``--repo-root`` or implicit parent of ``src/``).

    Args:
        cli: Optional explicit repository root from argparse.

    Returns:
        Absolute ``Path`` to toolkit root.
    """
    if cli:
        return cli.resolve()
    return Path(__file__).resolve().parent.parent


def _fingerprint() -> dict[str, str]:
    """Return truncated hash map for JSONL/live payloads (matches ``src.cli`` policy).

    Returns:
        Dict with ``host_key_hash16`` hex prefix (not a hardware serial).
    """
    raw = f"{platform.node()}|{platform.release()}|{platform.machine()}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return {"host_key_hash16": digest}


def cmd_proxy_diagnose(args: argparse.Namespace) -> int:
    """WinINET-centric diagnose with FailureBlocks plus optional localhost listener attribution.

    Args:
        args: Supports ``emit_json``, ``repo_root``, ``skip_listener_probe``.

    Returns:
        Shell exit ``0``.
    """
    run = subprocess.run
    repo = _repo_root(getattr(args, "repo_root", None))
    reg = read_proxy_registry(run=run)
    parsed = parse_proxy_server(reg.proxy_server)
    merged = registry_with_parsed(reg, parsed)
    risk = summarize_proxy_risk(parsed, bool(merged.get("is_enabled")))
    attrib: dict[str, Any] | None = None
    if not bool(getattr(args, "skip_listener_probe", False)):
        attrib = build_localhost_proxy_attribution(reg, parsed, run=run)
    failures = build_proxy_failure_blocks(
        proxy_enable=reg.proxy_enable,
        parsed_proxy_dict=parsed.to_dict(),
        localhost_attribution=attrib,
    )
    payload: dict[str, Any] = {
        "schema_version": "1",
        "artifact": "proxy_diagnose",
        "script_version": SCRIPT_VERSION,
        "machine": _fingerprint(),
        "registry_merge": merged,
        "risk_diagnostic_sense": risk,
        "localhost_attribution": attrib,
        "failure_blocks": [b.to_dict() for b in failures],
    }

    if getattr(args, "emit_json", False):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    lines = [
        "=== Proxy diagnose (HKCU WinINET) ===",
        f"Proxy: {'ON' if merged.get('is_enabled') else 'OFF'}   Mode: {merged.get('proxy_mode')}",
        f"ProxyServer: {merged.get('proxy_server') or '(empty)'}",
        f"Risk (diagnostic): {risk}",
        "",
        "Failure blocks:",
    ]
    if not failures:
        lines.append("  (none)")
    for fb in failures:
        lines.append(f"  - [{fb.severity}] {fb.failure_id}")
        for lc in fb.likely_causes[:2]:
            lines.append(f"      • {lc}")
    if attrib:
        lines.extend(
            [
                "",
                f"Localhost listener probe: listeners={'yes' if attrib.get('listener_found') else 'no'} "
                f"port={attrib.get('localhost_port') or 'n/a'}",
            ]
        )
    lines.extend(["", "Use --json for machine-readable output."])
    print("\n".join(lines))
    return 0


def cmd_proxy_attribution(args: argparse.Namespace) -> int:
    """Print structured localhost proxy listener attribution JSON or human-readable rows."""
    run = subprocess.run
    reg = read_proxy_registry(run=run)
    parsed = parse_proxy_server(reg.proxy_server)
    port = getattr(args, "port", None)
    attrib = build_localhost_proxy_attribution(
        reg,
        parsed,
        run=run,
        override_port=int(port) if port is not None else None,
    )
    if getattr(args, "emit_json", False):
        print(json.dumps(attrib, indent=2, ensure_ascii=False))
        return 0
    print(f"localhost_proxy_detected={attrib.get('localhost_proxy_detected')} port={attrib.get('localhost_port')}")
    if not attrib.get("localhost_proxy_detected"):
        print("No loopback proxy port to attribute.")
        for n in attrib.get("notes") or []:
            print(f"Note: {n}")
        return 0
    print(f"listener_found={attrib.get('listener_found')}")
    for o in attrib.get("owners") or []:
        print(f"- pid={o.get('pid')} name={o.get('process_name')} path={o.get('executable_path')}")
        print(f"  cmdline={(o.get('command_line') or 'unavailable')[:200]}")
    for n in attrib.get("notes") or []:
        print(f"Note: {n}")
    return 0


def cmd_proxy_rollback(args: argparse.Namespace) -> int:
    """Restore HKCU WinINET captured in ``logs/proxy_snapshots.jsonl`` by ``snapshot_id``."""
    repo = _repo_root(getattr(args, "repo_root", None))
    snap_path = repo / "logs" / "proxy_snapshots.jsonl"
    snapshot_id = str(getattr(args, "snapshot_id", "") or "").strip()
    if not snapshot_id:
        print("snapshot_id is required.", file=sys.stderr)
        return 2
    record = load_snapshot_record_by_id(snap_path, snapshot_id)
    if not record:
        print(f"No snapshot matched id={snapshot_id!r} in {snap_path}", file=sys.stderr)
        return 2

    phrase = snapshot_confirmation_phrase()
    plan = record.get("rollback_plan") or build_rollback_plan(record)
    print("Rollback preview (HKCU WinINET)")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print("\nStructured argv preview:")
    for argv in build_restore_reg_argv(record):
        print(" ", " ".join(argv))

    if bool(getattr(args, "dry_run", False)):
        print("\n[dry-run] No registry restores performed.")
        return 0

    confirm = input(f"Type {phrase} to restore captured values: ")
    if confirm.strip() != phrase:
        print("Cancelled.")
        return 1

    argv_t = build_restore_reg_argv(record)
    results = apply_reg_argv_sequences(argv_t, dry_run=False)
    codes = [r.returncode for r in results]
    audit = {
        "type": "repair",
        "subtype": "proxy_rollback",
        "timestamp": utc_now_iso(),
        "snapshot_id": snapshot_id,
        "results": [
            {"argv": list(r.argv), "code": r.returncode, "stderr": r.stderr, "stdout": r.stdout} for r in results
        ],
        "confirmation_method": "typed_phrase",
    }
    append_jsonl_core(repo / "logs" / "repair_audit.jsonl", audit)
    if any(c != 0 for c in codes):
        print("Warning: some reg restores returned non-zero; see logs\\repair_audit.jsonl.", file=sys.stderr)
        return 1
    print("Rollback complete; appended repair_audit.jsonl row.")
    return 0


def _proxy_events_path(repo: Path) -> Path:
    """Return canonical append-only path for proxy monitor JSONL (documentation helper)."""
    return repo / "logs" / "proxy_guard_events.jsonl"


def cmd_proxy_status(args: argparse.Namespace) -> int:
    """Print HKCU WinINET proxy summary or JSON when ``--json`` (``emit_json``) is set.

    Side effects:
        Read-only ``reg query`` subprocesses via ``read_proxy_registry``.

    Args:
        args: Namespace with ``emit_json`` bool from ``--json`` flag.

    Returns:
        Process exit code ``0``.
    """
    reg = read_proxy_registry()
    parsed = parse_proxy_server(reg.proxy_server)
    merged = registry_with_parsed(reg, parsed)
    risk = summarize_proxy_risk(parsed, bool(merged.get("is_enabled")))
    if getattr(args, "emit_json", False):
        merged_out = dict(merged)
        merged_out["risk_diagnostic_sense"] = risk
        print(json.dumps(merged_out, indent=2, ensure_ascii=False))
        return 0
    lines = [
        f"Proxy Status: {'ON' if merged.get('is_enabled') else 'OFF'}",
        f"Proxy Server: {merged.get('proxy_server') or '(empty)'}",
        f"Mode: {merged.get('proxy_mode')}",
        f"Localhost Port: {merged.get('localhost_port') or 'n/a'}",
        f"Risk: {risk}",
        "Why: Browser traffic may be routed through a local process when loopback proxy flags are set.",
    ]
    print("\n".join(lines))
    return 0


def cmd_proxy_owner(args: argparse.Namespace) -> int:
    """Resolve TCP listener owners for a localhost proxy port via netstat/tasklist/CIM.

    Args:
        args: Includes optional ``port`` override and ``emit_json`` for JSON-only output.

    Returns:
        ``0`` on success (including empty owner lists).

    Side effects:
        Executes ``netstat``, ``tasklist``, and PowerShell CIM enrichment on Windows.
    """
    run = subprocess.run
    port: int | None = args.port
    if port is None:
        reg = read_proxy_registry(run=run)
        parsed = parse_proxy_server(reg.proxy_server)
        port = parsed.localhost_port
    block = attribution_payload(port, run=run)
    owners = block.get("owners") or []
    if getattr(args, "emit_json", False):
        print(json.dumps(block, indent=2, ensure_ascii=False))
        return 0
    print(f"Local proxy port: {block.get('port')}")
    if not owners:
        print("No listener owner rows were resolved (see notes).")
        for n in block.get("notes") or []:
            print(f"Note: {n}")
        return 0
    o = owners[0]
    print(f"Owner PID: {o.get('pid')}")
    print(f"Process: {o.get('process_name')}")
    print(f"Parent: {o.get('parent_name')}")
    cl = o.get("command_line")
    print(f"Command line: {cl if cl else 'unavailable'}")
    if o.get("permission_limited"):
        print("Note: command line may require administrator privileges or CIM access.")
    return 0


def cmd_proxy_monitor(args: argparse.Namespace) -> int:
    """Poll HKCU proxy keys; optionally append JSONL events on change.

    Idempotency:
        Each distinct registry state emits at most one initial snapshot per run; changes append.

    Args:
        args: ``interval``, ``once``, optional ``jsonl`` path string.

    Returns:
        ``0`` after loop exit (``once``) or interrupt (operator Ctrl+C outside handler).

    Audit Notes:
        Review ``--jsonl`` target for append growth; correlates with ``proxy_guard`` events.
    """
    jsonl = Path(args.jsonl) if getattr(args, "jsonl", None) else None
    interval = max(1.0, float(getattr(args, "interval", 5.0)))

    def owner_fn(p: int | None) -> dict[str, Any]:
        if p is None:
            return {}
        return attribution_payload(int(p), run=subprocess.run)

    monitor_proxy_registry(
        interval=interval,
        once=bool(getattr(args, "once", False)),
        jsonl_path=jsonl,
        emit_json_stdout=False,
        port_owner_fn=lambda prt: owner_fn(prt),
        run=subprocess.run,
    )
    return 0


def cmd_proxy_guard(args: argparse.Namespace) -> int:
    """Run policy-aware proxy monitoring with optional low-risk automatic rollback.

    On non-Windows hosts the command exits with a clear error (no partial execution).

    Args:
        args: ``interval``, ``once``, ``auto_rollback``, optional ``policy`` and ``jsonl`` paths,
            ``repo_root``, and ``dry_run_rollback`` for tests.

    Returns:
        ``0`` on normal loop exit, ``2`` when the platform or policy file is unusable.
    """
    if platform.system() != "Windows":
        print("proxy-guard is supported on Windows only.", file=sys.stderr)
        return 2
    repo = _repo_root(getattr(args, "repo_root", None))
    reports_dir = repo / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = repo / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if getattr(args, "show_lkg", False):
        snap = load_lkg_snapshot(repo / "reports" / "proxy_guard_lkg.json")
        print(json.dumps(snap.to_jsonable() if snap else {}, indent=2, ensure_ascii=False))
        return 0

    if getattr(args, "clear_lkg", False):
        tgt = repo / "reports" / "proxy_guard_lkg.json"
        if tgt.is_file():
            tgt.unlink()
        return 0

    policy_arg = getattr(args, "policy", None)
    config_pol = repo / "config" / "proxy_guard_policy.json"
    if policy_arg:
        policy_path = Path(policy_arg)
    elif config_pol.is_file():
        policy_path = config_pol
    else:
        policy_path = repo / "shared" / "proxy_guard_policy.example.json"

    if not policy_path.is_file():
        print(f"Policy file not found: {policy_path}", file=sys.stderr)
        return 2

    policy = load_proxy_guard_policy(policy_path)
    jsonl_arg = getattr(args, "jsonl", None)
    jsonl = Path(jsonl_arg) if jsonl_arg else repo / "logs" / "proxy_guard_control.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    interval = max(1.0, float(getattr(args, "interval", 5.0)))
    cfg_arg = getattr(args, "service_config", None)
    cfg_path = Path(cfg_arg) if cfg_arg else None
    slog = getattr(args, "structured_log", None)
    structured_log_path = Path(slog) if slog else None
    dry_combo = bool(getattr(args, "dry_run_rollback", False) or getattr(args, "proxy_guard_dry_run", False))
    cfg = build_service_config(
        policy=policy,
        jsonl_path=jsonl,
        interval=interval,
        once=bool(getattr(args, "once", False)),
        auto_rollback=bool(getattr(args, "auto_rollback", False)),
        dry_run_rollback=dry_combo,
        run=subprocess.run,
        config_file=cfg_path,
        structured_log_path=structured_log_path,
        exit_after_registry_change_events=None,
        repo_root=repo,
        attribution_mode=str(getattr(args, "attribution_mode", "auto")),
        trust_current_lkg=bool(getattr(args, "trust_current_lkg", False)),
        restore_git_npm_env=bool(getattr(args, "restore_git_npm_env", False)),
        cli_rollback=bool(getattr(args, "cli_rollback", False)),
        rollback_confirm_phrase=str(getattr(args, "rollback_confirm_phrase", "") or ""),
    )
    run_proxy_guard_service(cfg)
    return 0


def cmd_proxy_disable(args: argparse.Namespace) -> int:
    """Preview or apply HKCU ``ProxyEnable=0`` (+ optional ``ProxyServer`` delete).

    Side effects (non-dry-run):
        Runs ``reg.exe`` argv lists; appends ``logs/repair_audit.jsonl``.
        Immediately before mutations, persists ``logs/proxy_snapshots.jsonl`` for rollback.

    Raises:
        None directly; policy violations print and return ``2``.

    Returns:
        ``0`` success, ``1`` cancelled confirmation, ``2`` policy guard failure.

    Audit Notes:
        Recovery: verify keys via ``proxy-status``; rollback via ``proxy-rollback``; software may
        reapply proxy policy afterward.
    """
    repo = _repo_root(args.repo_root)
    run = subprocess.run
    logs_dir = repo / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reg_before_preview = read_proxy_registry(run=run)
    parsed = parse_proxy_server(reg_before_preview.proxy_server)
    merged_before_preview = registry_with_parsed(reg_before_preview, parsed)
    print("Current WinINET (HKCU) view:")
    print(json.dumps(merged_before_preview, indent=2, ensure_ascii=False))
    mutations, human_lines = build_user_proxy_disable_mutations(
        clear_proxy_server_value=bool(getattr(args, "clear_server", False)),
    )
    text = "\n".join(human_lines)
    print("\nPlanned actions:\n" + text)
    try:
        assert_no_firewall_reset_in_preview(text)
    except ValueError as exc:
        print(exc)
        return 2
    print("\nStructured reg argv preview:\n" + summarize_mutations_plaintext(mutations))
    dry = bool(getattr(args, "dry_run", False))
    if dry:
        print("\n[dry-run] No registry writes or snapshot persisted.")
        return 0

    confirm = input(f"Type {CONFIRMATION_PHRASE} to continue: ")
    if confirm.strip() != CONFIRMATION_PHRASE:
        print("Cancelled.")
        return 1

    capture_pre = capture_wininet_snapshot(run=run)
    rollback_plan = build_rollback_plan(capture_pre)
    append_proxy_snapshots_jsonl(repo, merge_snapshot_payload(capture_pre, rollback_plan))

    planned_action = {
        "human": list(human_lines),
        "mutation_argv": [list(m.argv) for m in mutations],
        "clear_server": bool(getattr(args, "clear_server", False)),
    }

    results = apply_mutations(mutations, dry_run=False)
    reg_after = read_proxy_registry(run=run)
    verification = verify_proxy_disabled(reg_after)
    merged_after = registry_with_parsed(reg_after, parse_proxy_server(reg_after.proxy_server))

    audit = {
        "type": "repair",
        "subtype": "proxy_disable",
        "timestamp": utc_now_iso(),
        "snapshot_id": capture_pre.snapshot_id,
        "before": capture_pre.to_jsonable(),
        "planned_action": planned_action,
        "after": merged_after,
        "verification_result": verification.to_dict(),
        "rollback_plan": rollback_plan,
        "results": [
            {"argv": list(r.argv), "code": r.returncode, "stderr": r.stderr, "stdout": r.stdout}
            for r in results
        ],
        "confirmation_method": "typed_phrase",
    }
    append_jsonl_core(repo / "logs" / "repair_audit.jsonl", audit)

    print("Applied mutations; see logs\\repair_audit.jsonl for snapshot + verification.")

    if not verification.ok:
        print(
            f"WARNING: verification failed ({verification.detail}); re-check proxy-status.",
            file=sys.stderr,
        )
        return 1
    print("Verification: ProxyEnable reported disabled.")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Persist ``LiveNetworkSnapshot`` JSON and append ``network_snapshots.jsonl`` row.

    Output guarantees:
        Filename uses UTC timestamp slug with ``:`` stripped; snapshot body includes commands list.

    Side effects:
        Writes under ``reports/snapshots/`` and appends one JSONL line.
    """
    repo = _repo_root(args.repo_root)
    snapshot, cmds = build_live_network_snapshot(run=subprocess.run)
    snap_dir = repo / "reports" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = utc_now_iso().replace(":", "").replace("+00:00", "Z")
    path = snap_dir / f"{ts}.json"
    payload = snapshot.to_dict()
    payload["commands_executed"] = list(cmds)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    append_jsonl_core(
        repo / "logs" / "network_snapshots.jsonl",
        {
            "type": "network_snapshot",
            "timestamp": utc_now_iso(),
            "path": str(path),
            "snapshot_id": str(uuid.uuid4()),
        },
    )
    print(f"Wrote {path}")
    return 0


def cmd_diagnose_live(args: argparse.Namespace) -> int:
    """Run live snapshot + v2 hypothesis scoring + recommendation bundle export.

    Side effects:
        Writes ``reports/snapshots/<uuid>.json``, ``reports/last_diagnosis_live.json``,
        appends ``logs/network_snapshots.jsonl`` and ``logs/decision_audit.jsonl``.

    Args:
        args: ``emit_json`` prints JSON-only payload to stdout when true.

    Returns:
        ``0`` on success.

    Audit Notes:
        Compare ``hypotheses_ranked`` with ``live_snapshot_ref`` file for evidence drill-down.
    """
    repo = _repo_root(args.repo_root)
    snapshot, cmds = build_live_network_snapshot(run=subprocess.run)
    ranked = score_live_snapshot(snapshot)
    top = ranked[0]
    reco = live_recommendation_bundle(top, primary_hypothesis=top.hypothesis)
    explain = primary_explanation_paragraph(snapshot, top)
    diagnosis_id = str(uuid.uuid4())
    snap_dir = repo / "reports" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts_slug = utc_now_iso().replace(":", "-").replace("+00:00", "Z")
    snap_path = snap_dir / f"{diagnosis_id}.json"
    snap_path.write_text(
        json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    append_jsonl_core(
        repo / "logs" / "network_snapshots.jsonl",
        {
            "type": "network_snapshot",
            "timestamp": utc_now_iso(),
            "path": str(snap_path),
            "diagnosis_id": diagnosis_id,
        },
    )
    live_payload: dict[str, Any] = {
        "diagnosis_id": diagnosis_id,
        "generated_at_utc": utc_now_iso(),
        "engine": "live_v2",
        "script_version": SCRIPT_VERSION,
        "machine": _fingerprint(),
        "live_snapshot_ref": str(snap_path),
        "hypotheses_ranked": ranked_dicts(ranked),
        "primary_hypothesis": top.hypothesis,
        "primary_confidence": top.confidence,
        "primary_evidence": list(top.evidence),
        "negative_evidence": list(top.negative_evidence),
        "explain_paragraph": explain,
        "recommendations": reco,
        "commands_executed": list(cmds),
    }
    last_path = repo / "reports" / "last_diagnosis_live.json"
    last_path.write_text(json.dumps(live_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    append_jsonl_core(
        repo / "logs" / "decision_audit.jsonl",
        {
            "type": "diagnosis_live",
            "timestamp": utc_now_iso(),
            "diagnosis_id": diagnosis_id,
            "script_version": SCRIPT_VERSION,
            "machine": live_payload["machine"],
            "hypotheses": live_payload["hypotheses_ranked"],
            "primary": top.hypothesis,
            "confidence": top.confidence,
            "safety_tier": "diagnose",
        },
    )

    if getattr(args, "emit_json", False):
        print(json.dumps(live_payload, indent=2, ensure_ascii=False))
        return 0
    print("=== Live diagnosis (v2) ===")
    print(f"Diagnosis ID: {diagnosis_id}")
    print(explain)
    print("\nRanked hypotheses:")
    for row in live_payload["hypotheses_ranked"][:10]:
        print(f"  {row['rank']}. {row['hypothesis']}: {float(row['confidence']):.2f}")
        for ev in row.get("evidence") or []:
            print(f"      - {ev}")
    print(f"\nSnapshot: {snap_path}")
    print(f"Last live payload: {last_path}")
    return 0


def _read_live_or_legacy(repo: Path) -> tuple[dict[str, Any], str]:
    """Load newest diagnosis artifact preferring live v2 JSON when present.

    Raises:
        FileNotFoundError: When neither artefact exists.

    Returns:
        Tuple of payload dict and source label ``live`` or ``legacy``.
    """
    live = repo / "reports" / "last_diagnosis_live.json"
    legacy = repo / "reports" / "last_diagnosis.json"
    if live.is_file():
        return json.loads(live.read_text(encoding="utf-8")), "live"
    if legacy.is_file():
        return json.loads(legacy.read_text(encoding="utf-8")), "legacy"
    raise FileNotFoundError("No last_diagnosis_live.json or last_diagnosis.json — run diagnose-live or diagnose.")


def _normalize_recommendations_blob(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract nested recommendations dict for both v1 and v2 payload shapes."""
    if payload.get("engine") == "live_v2":
        return payload.get("recommendations") or {}
    return payload.get("recommendations") or {}


def cmd_repair_preview(args: argparse.Namespace) -> int:
    """Print tiered repair rows from latest live (preferred) or legacy diagnosis file.

    Returns:
        ``0`` after printing.

    Raises:
        FileNotFoundError propagates when no artefact exists.
    """
    repo = _repo_root(args.repo_root)
    payload, source = _read_live_or_legacy(repo)
    blob = _normalize_recommendations_blob(payload)
    print(f"Repair preview source: {source}")
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
            ak = item.get("action_key")
            if ak:
                print(f"      action_key: {ak}")
        print()
    return 0


def cmd_repair_apply(args: argparse.Namespace) -> int:
    """Optionally elevate first LOW-tier ``scripts/*.bat`` after ``RUN`` confirmation.

    Side effects:
        May launch elevated PowerShell; appends JSONL feedback identical to legacy repair-safe.

    Returns:
        ``0`` success path, ``1`` cancel/not applicable, ``2`` path guard violation.

    Audit Notes:
        Skips launching when ``action_key`` is ``proxy_disable``—operators must run ``proxy-disable``.
    """
    repo = _repo_root(args.repo_root)
    payload, source = _read_live_or_legacy(repo)
    blob = _normalize_recommendations_blob(payload)
    safe_items = blob.get("repair_safe") or []
    runnable = [i for i in safe_items if i.get("script") and i.get("risk") == "LOW"]

    print("repair-preview source:", source)
    print("Eligible LOW actions with scripts:")
    for item in runnable:
        print(f"- [{item.get('risk')}] {item.get('title')} -> {item.get('script')}")

    if not runnable:
        print("Nothing runnable (use proxy-disable CLI for HKCU disables).")
        return 0

    if getattr(args, "dry_run", False):
        print("[dry-run] not executing.")
        return 0

    first = runnable[0]
    if first.get("action_key") == "proxy_disable":
        print("Use `python -m src proxy-disable` for typed confirmation on HKCU disables.")
        return 1

    script_rel = Path(str(first["script"]))
    target = (repo / script_rel).resolve()
    scripts_root = (repo / "scripts").resolve()
    try:
        target.relative_to(scripts_root)
    except ValueError:
        print("Refusing to execute script outside scripts/.")
        return 2

    answer = input('Type RUN to execute the first LOW-risk script listed above: ')
    if answer.strip().upper() != "RUN":
        print("Cancelled.")
        return 1

    ps = f"Start-Process -FilePath '{target}' -Verb RunAs -Wait"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)

    diag_id = payload.get("diagnosis_id", "unknown")
    fb = input("Did it help? [y/N/unknown]: ").strip().lower() or "unknown"
    state: FeedbackState
    if fb in {"y", "yes"}:
        state = "true"
    elif fb in {"n", "no"}:
        state = "false"
    else:
        state = "unknown"
    notes_in = input("Optional notes (blank skip): ").strip()
    append_feedback(
        repo / "logs" / "decision_feedback.jsonl",
        FeedbackRecord(
            diagnosis_id=str(diag_id),
            recommended_action=str(script_rel.as_posix()),
            user_feedback_fixed=state,
            notes=notes_in or "repair-apply feedback",
        ),
    )
    return 0
