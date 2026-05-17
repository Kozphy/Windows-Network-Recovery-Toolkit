"""Argparse-backed handlers for Proxy Guard flows, snapshots, live diagnosis, repair previews/replay.

Module responsibility:
    Maps ``argparse.Namespace`` objects from ``src.cli`` subcommands onto filesystem writes,
    ``reg.exe`` argv sequences (HKCU-only where documented), subprocess probes for live snapshots,
    and append-only JSONL audit trails. Keeps orchestration here; deterministic scoring lives in
    ``src.hypothesis``, policy gates in ``src.policy``, proofs in ``src.proof``.

System placement:
    Called only from ``src.cli`` dispatch (and tests). FastAPI toolkit routes in
    ``backend/live_observability.py`` subprocess ``python -m src …`` rather than importing these
    callables directly, preserving identical stdin/confirmation semantics.

Key invariants:
    * No registry mutations or repair ``reg`` argv execution during ``proxy-disable --dry-run`` or
      ``repair-apply --dry-run``.
    * Where a handler documents JSON-only stdout (e.g. ``emit_json`` on live/replay paths), human
      banners must not precede payloads on success paths for that branch.
    * Live diagnosis fingerprints use ``_fingerprint()`` (truncated SHA-256); payloads avoid raw hostname
      strings unless already present from upstream tooling.

Input assumptions:
    * Windows-only commands guard with ``exit_code_if_not_windows`` before probing WinINET/registry.
    * ``args.repo_root`` is optional; ``_repo_root`` resolves toolkit root hosting ``reports/`` and ``logs/``.
    * JSON artefacts consumed by helpers (last diagnosis files) match writer schemas; malformed files
      raise decode errors at the read site.

Output guarantees:
    * Exit codes: ``0`` success; ``1`` operator cancel / post-mutation verification soft-failure where
      documented; ``2`` unsupported platform or policy/assertion refusal.
    * Append-only logs grow by one logical record per mutation or diagnosis row where implemented.

Side effects:
    * Vary by ``cmd_*``: see each docstring for exact paths under ``reports/``, ``logs/``, subprocess
      execution, and ``network_state`` correlation hooks.

Failure modes:
    * Abrupt termination can leave partially written trailing JSONL lines; tail readers should skip
      invalid JSON per ``src.core.jsonl`` guidance.
    * Proof Engine exceptions during live diagnosis set ``proof_engine_error`` on the audit row and
      degrade trust instead of terminating the CLI (unless gated elsewhere).

Raises:
    * Most handlers swallow or print recoverable faults; ``_read_live_or_legacy`` raises
      ``FileNotFoundError`` when no diagnosis artefacts exist.

Audit Notes:
    * HKCU mutations: correlate ``logs/repair_audit.jsonl`` with ``logs/proxy_snapshots.jsonl``.
    * Live stacks: ``logs/decision_audit.jsonl`` (`type=diagnosis_live`),
      ``logs/decision_runs.jsonl`` (replay schema), ``reports/last_diagnosis_live.json``.

Engineering Notes:
    * Centralizes long-running CLI choreography so smaller packages remain test-friendly and reusable.

See Also:
    ``docs/cli_reference.md``, ``docs/decision_engine_v2.md``, ``docs/proxy_guard.md``, ``docs/safety_model.md``.
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
from .core.windows_cli import exit_code_if_not_windows
from .core.time_utils import utc_now_iso
from .audit.replay import (
    SCHEMA_VERSION as _REPLAY_SCHEMA_VERSION,
    build_replay_report,
    find_decision_run,
    format_replay_flow_text,
)
from .hypothesis.explanations import primary_explanation_paragraph
from .hypothesis.live_scoring import ranked_dicts, score_live_snapshot
from .hypothesis.recommendations import live_recommendation_bundle
from .observation.adversarial import adversarial_hints
from .observation.trust import assess_trust
from .policy.hypothesis_gates import build_hypothesis_decisions
from .proof.proxy_https import run_localhost_proxy_https_proof
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
from .proxy_guard.remediation import (
    CONFIRMATION_PHRASE,
    build_user_proxy_disable_mutations,
    validate_action_confirmation,
)
from .proxy_guard.watcher import monitor_proxy_registry
from .network_state.event_log import (
    correlation_key as v2_correlation_key,
    incident_id_from_proxy as v2_incident_id_from_proxy,
    log_attribution as v2_log_attribution,
    log_snapshot as v2_log_snapshot,
    log_repair_attempt as v2_log_repair_attempt,
    log_verification as v2_log_verification,
    parse_proxy as v2_parse_observed_proxy,
    update_or_write_incident_summary as v2_update_incident_summary,
)
from .network_state.snapshot_store import resolve_named_snapshot
from .proxy_guard.known_good_store import get_latest_named_record, snapshot_from_record
from .proxy_guard.models import ProxySnapshot
from .proxy_guard.proxy_watch import run_proxy_watch_loop
from .proxy_guard.rollback import execute_known_good_proxy_restore
from .proxy_guard.proxy_snapshot_commands import (
    cmd_proxy_snapshot_diff,
    cmd_proxy_snapshot_list,
    cmd_proxy_snapshot_restore,
    cmd_proxy_snapshot_save,
    cmd_proxy_snapshot_show,
)
from .repair.executor import apply_mutations, apply_reg_argv_sequences
from .repair.policy import assert_no_firewall_reset_in_preview
from .repair.preview import summarize_mutations_plaintext
from .version import SCRIPT_VERSION


_V2_REL_INCIDENT_HELP = [
    "Identify process listening on the loopback proxy port",
    "Check startup entries",
    "Check scheduled tasks",
    "Check browser/VPN/proxy tools",
    "Monitor registry value changes over time",
]


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
    if (code := exit_code_if_not_windows("proxy-diagnose")) is not None:
        return code
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
    if (code := exit_code_if_not_windows("proxy-attribution")) is not None:
        return code
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


ROLLBACK_PROXY_SNAPSHOT_FILE_PHRASE = "RESTORE_PROXY_SNAPSHOT_FILE"


def cmd_proxy_rollback(args: argparse.Namespace) -> int:
    """Restore HKCU WinINET from ``logs/proxy_snapshots.jsonl`` UUID row or typed ``--from-snapshot`` JSON file."""
    repo = _repo_root(getattr(args, "repo_root", None))
    from_snapshot = getattr(args, "rollback_from_snapshot", None)

    if from_snapshot:
        if (code := exit_code_if_not_windows("proxy-rollback (--from-snapshot)")) is not None:
            return code
        snap_path_fs = Path(str(from_snapshot)).expanduser().resolve()
        if not snap_path_fs.is_file():
            print(f"Snapshot file not found: {snap_path_fs}", file=sys.stderr)
            return 2
        try:
            blob = json.loads(snap_path_fs.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Unable to read JSON snapshot file: {exc}", file=sys.stderr)
            return 2
        inner = blob.get("snapshot") if isinstance(blob.get("snapshot"), dict) else blob
        if not isinstance(inner, dict):
            print("Snapshot JSON must contain a ProxySnapshot-compatible object or {\"snapshot\": {...}}.", file=sys.stderr)
            return 2
        target = ProxySnapshot.from_json_dict(inner)
        phrase = str(getattr(args, "rollback_file_confirm_phrase", "") or "").strip()
        dry = bool(getattr(args, "dry_run", False))
        live = phrase == ROLLBACK_PROXY_SNAPSHOT_FILE_PHRASE and not dry

        preview = execute_known_good_proxy_restore(target, dry_run=True, restore_winhttp=True, run=subprocess.run)
        print(json.dumps(preview, indent=2, ensure_ascii=False, default=str))
        if dry or not live:
            print("\nDry-run only. Pass exact --confirm RESTORE_PROXY_SNAPSHOT_FILE (omit --dry-run) to execute.", file=sys.stderr)
            return 0
        result = execute_known_good_proxy_restore(target, dry_run=False, restore_winhttp=True, run=subprocess.run)
        append_jsonl_core(
            repo / "logs" / "proxy_guard_actions.jsonl",
            {
                "schema_version": 1,
                "timestamp_utc": utc_now_iso(),
                "action": "proxy_rollback_known_good_file",
                "result": "ok" if result.get("success") else "error",
                "note": json.dumps({"path": str(snap_path_fs)})[:2000],
            },
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result.get("success") else 1

    if (code := exit_code_if_not_windows("proxy-rollback (--snapshot-id)")) is not None:
        return code

    snap_path = repo / "logs" / "proxy_snapshots.jsonl"
    snapshot_id = str(getattr(args, "snapshot_id", "") or "").strip()
    if not snapshot_id:
        print("snapshot_id or --from-snapshot is required.", file=sys.stderr)
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
    if (code := exit_code_if_not_windows("proxy-status")) is not None:
        return code
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
    if (code := exit_code_if_not_windows("proxy-owner")) is not None:
        return code
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


def cmd_proxy_watch(args: argparse.Namespace) -> int:
    """Run the ``proxy-watch`` loop: HKCU snapshots, drift diff, attribution, JSONL auditing.

    Args:
        args: Namespace carrying ``interval``, ``once``, ``repo_root``, optional ``proxy_watch_evidence_csv``.

    Returns:
        ``0`` on normal completion (including ``--once`` short runs), ``2`` when the host OS is non-Windows.

    Side effects:
        Calls :func:`~src.proxy_guard.proxy_watch.run_proxy_watch_loop`, which reads policy files, invokes
        subprocess probes, appends NDJSON audits, prints ``initial_poll`` JSON to stdout, and prints alerts to stderr.

    Privileges:
        Follows downstream probe requirements—typically interactive user token without mandatory elevation.

    Audit Notes:
        Persisted artifacts live under :func:`~src.proxy_guard.audit.proxy_change_audit_jsonl_path`; optional CSV
        boosts only adjust scoring mass, not row schema.

    Failure modes:
        Missing evidence CSV paths log to stderr and continue with zero boost.
    """

    if (code := exit_code_if_not_windows("proxy-watch")) is not None:
        return code
    repo = _repo_root(getattr(args, "repo_root", None))
    eb = 0.0
    csv_arg = getattr(args, "proxy_watch_evidence_csv", None)
    if csv_arg:
        csv_path = Path(str(csv_arg))
        if csv_path.is_file():
            from .proxy_guard.evidence_import import confidence_boost_from_csv

            boost, _ = confidence_boost_from_csv(csv_path.resolve())
            eb += float(boost)
        else:
            print(f"Evidence CSV not found: {csv_path}", file=sys.stderr)
    run_proxy_watch_loop(
        repo_root=repo,
        interval_seconds=max(1.0, float(getattr(args, "interval", 5.0))),
        once=bool(getattr(args, "once", False)),
        evidence_boost=eb,
    )
    return 0


def cmd_proxy_report(args: argparse.Namespace) -> int:
    """Print a human-readable tail summary or JSON bundle for ``logs/proxy_guard.jsonl``.

    Args:
        args: Namespace with ``proxy_report_tail`` (int, default 50), ``emit_json`` flag, ``repo_root``.

    Returns:
        ``0`` after printing.

    Side effects:
        Reads the entire JSONL file into memory to count rows—avoid on multi-gigabyte files.

    Data handling:
        Skips blank lines and invalid JSON quietly; summary counts apply only to successfully parsed dict rows in
        the trailing window.

    Audit Notes:
        Use ``--json`` for machine replay; plaintext mode surfaces aggregate high/medium risk counts only.
    """

    from .proxy_guard.audit import proxy_change_audit_jsonl_path

    repo = _repo_root(getattr(args, "repo_root", None))
    path = proxy_change_audit_jsonl_path(repo)
    rows: list[dict[str, Any]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    tail_n = max(1, int(getattr(args, "proxy_report_tail", 50)))
    tail = rows[-tail_n:]

    summary = {
        "path": str(path),
        "rows_total": len(rows),
        "rows_shown": len(tail),
        "risk_high": sum(1 for r in tail if isinstance(r.get("diff"), dict) and str(r["diff"].get("risk_level")) == "high"),
        "risk_medium": sum(1 for r in tail if isinstance(r.get("diff"), dict) and str(r["diff"].get("risk_level")) == "medium"),
    }

    if getattr(args, "emit_json", False):
        print(json.dumps({"summary": summary, "recent": tail}, indent=2, ensure_ascii=False, default=str))
        return 0

    lines = [
        "=== Proxy change report (logs/proxy_guard.jsonl) ===",
        f"Total rows scanned (tail subset): showing {len(tail)} newest",
        f"High-risk events (tail): {summary['risk_high']}",
        f"Medium-risk events (tail): {summary['risk_medium']}",
        "",
        "Replay with: python -m src proxy-watch --interval 5",
    ]
    print("\n".join(lines))
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
    if (code := exit_code_if_not_windows("proxy-monitor")) is not None:
        return code
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
    if (code := exit_code_if_not_windows("proxy-guard")) is not None:
        return code
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
    kg_raw = getattr(args, "known_good", None)
    known_snap = None
    if kg_raw:
        name = str(kg_raw).strip()
        known_snap = resolve_named_snapshot(repo, name)
        if known_snap is None:
            known_snap = snapshot_from_record(get_latest_named_record(repo, name))
        if known_snap is None:
            print(f"Named proxy snapshot not found: {kg_raw!r}", file=sys.stderr)
            return 2
    csv_raw = getattr(args, "proxy_guard_evidence_csv", None)
    csv_trim = str(csv_raw).strip() if csv_raw else None
    win_sec = int(getattr(args, "proxy_guard_attribution_seconds", 90))
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
        known_good_snapshot=known_snap,
        evidence_csv=csv_trim,
        attribution_since_seconds=win_sec,
        stdout_json=bool(getattr(args, "emit_json", False)),
    )
    run_proxy_guard_service(cfg)
    return 0


def cmd_proxy_watch_report(args: argparse.Namespace) -> int:
    """Print human-readable summary of ``reports/proxy_guard_watch.jsonl`` tail rows."""

    from .proxy_guard.audit import default_audit_paths
    from .proxy_guard.human_report import format_watch_report, load_watch_jsonl

    repo = _repo_root(getattr(args, "repo_root", None))
    watch_path = default_audit_paths(repo)["watch"]
    tail_n = max(1, int(getattr(args, "proxy_watch_tail", 10)))
    all_rows = load_watch_jsonl(watch_path, tail_n=10**9)
    tail = all_rows[-tail_n:] if tail_n else all_rows

    if getattr(args, "emit_json", False):
        print(
            json.dumps(
                {
                    "path": str(watch_path),
                    "rows_total": len(all_rows),
                    "rows_shown": len(tail),
                    "events": tail,
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )
        return 0

    print(
        format_watch_report(
            tail,
            path=watch_path,
            total_rows=len(all_rows),
            all_records_for_flip_flop=all_rows,
        )
    )
    return 0


def _reg_fields_for_proxy_disable(*, clear_server: bool, clear_autoconfig: bool) -> tuple[str, ...]:
    """Return the WinINET registry values the proxy-disable command proposes to mutate."""

    fields = ["ProxyEnable"]
    if clear_server:
        fields.append("ProxyServer")
    if clear_autoconfig:
        fields.append("AutoConfigURL")
    return tuple(fields)


def _proxy_disable_audit_row(
    *,
    event_kind: str,
    action_id: str,
    decision: str,
    dry_run: bool,
    mutated: bool,
    reason: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    action: dict[str, Any] | None = None,
    planned_action: dict[str, Any] | None = None,
    snapshot_id: str = "",
    verification_result: dict[str, Any] | None = None,
    rollback_plan: dict[str, Any] | None = None,
    results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one append-only audit record for proxy remediation control gates."""

    return {
        "audit_event_id": str(uuid.uuid4()),
        "type": "repair",
        "subtype": "proxy_disable",
        "event_kind": event_kind,
        "action_id": action_id,
        "decision": decision,
        "dry_run": dry_run,
        "mutated": mutated,
        "reason": reason,
        "timestamp": utc_now_iso(),
        "before": before,
        "after": after,
        "action": action or {},
        "planned_action": planned_action or {},
        "snapshot_id": snapshot_id,
        "verification_result": verification_result or {},
        "rollback_plan": rollback_plan or {},
        "results": results or [],
        "confirmation_method": "typed_phrase",
    }


def _append_proxy_disable_audit(repo: Path, row: dict[str, Any]) -> str:
    """Append a proxy-disable audit row and return its id."""

    append_jsonl_core(repo / "logs" / "repair_audit.jsonl", row)
    return str(row["audit_event_id"])


def cmd_proxy_disable(args: argparse.Namespace) -> int:
    """Preview or apply HKCU WinINET proxy disable mutations (structured ``reg`` argv only).

    Purpose:
        Surface current HKCU proxy state, summarize planned ``reg.exe`` mutations, optionally apply
        them after a typed phrase, then verify reads and emit append-only audit plus network-state
        correlation rows.

    Args:
        args: Typical fields:
            ``repo_root`` — optional toolkit root Path.
            ``dry_run`` — when True, print planned actions only (no snapshots or ``reg`` execution).
            ``clear_server`` — when True, include deleting the ``ProxyServer`` value path.

    Returns:
        ``0`` when dry-run exits cleanly or apply + verification succeeds.
        ``1`` when the operator declines the typed confirmation or verification warns (non-zero verification).
        ``2`` when not on Windows or ``assert_no_firewall_reset_in_preview`` rejects the plaintext plan.

    Raises:
        None intentionally; subprocess failures remain inside structured ``results`` in the audit row.

    Side effects:
        Dry-run: stdout only (no persistent writes beyond printing).
        Apply: persists ``logs/proxy_snapshots.jsonl`` rollback payload, executes ``apply_mutations``,
        appends ``logs/repair_audit.jsonl``, and emits related ``network_state`` JSONL envelopes.

    Idempotency:
        Re-disabling yields stable HKCU booleans absent external policy overwriting keys; reversing
        state uses documented rollback tooling, not this command blindly re-run.

    Audit Notes:
        Compare ``verification_result`` inside ``repair_audit.jsonl`` versus ``proxy-status``.
        Mis-verification indicates policy or tooling re-enabled proxy concurrently—investigate before retry.

        Recovery guidance: rerun ``proxy-status``, use ``proxy-rollback`` snapshot flow when available,
        expect enterprise policy software to recreate keys after remediation.
    """
    if (code := exit_code_if_not_windows("proxy-disable")) is not None:
        return code
    repo = _repo_root(args.repo_root)
    run = subprocess.run
    emit_json = bool(getattr(args, "emit_json", False))
    logs_dir = repo / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    reg_before_preview = read_proxy_registry(run=run)
    parsed = parse_proxy_server(reg_before_preview.proxy_server)
    merged_before_preview = registry_with_parsed(reg_before_preview, parsed)
    if not emit_json:
        print("Current WinINET (HKCU) view:")
        print(json.dumps(merged_before_preview, indent=2, ensure_ascii=False))
    clear_server = bool(getattr(args, "clear_server", True))
    clear_autoconfig = bool(getattr(args, "clear_autoconfig", True))
    mutations, human_lines = build_user_proxy_disable_mutations(
        clear_proxy_server_value=clear_server,
        clear_autoconfig_url=clear_autoconfig,
    )
    text = "\n".join(human_lines)
    if not emit_json:
        print("\nPlanned actions:\n" + text)
    try:
        assert_no_firewall_reset_in_preview(text)
    except ValueError as exc:
        if not emit_json:
            print(exc)
        row = _proxy_disable_audit_row(
            event_kind="blocked_dangerous_action",
            action_id="disable_wininet_proxy",
            decision="BLOCK",
            dry_run=True,
            mutated=False,
            reason=str(exc),
            before=merged_before_preview,
        )
        _append_proxy_disable_audit(repo, row)
        return 2
    if not emit_json:
        print("\nStructured reg argv preview:\n" + summarize_mutations_plaintext(mutations))
    dry = bool(getattr(args, "dry_run", True))
    action_id = str(getattr(args, "action_id", "disable_wininet_proxy") or "disable_wininet_proxy")
    confirmation = str(getattr(args, "confirm_phrase", "") or getattr(args, "confirm", "") or "")
    requested_fields = _reg_fields_for_proxy_disable(
        clear_server=clear_server,
        clear_autoconfig=clear_autoconfig,
    )
    decision, reason, action_model = validate_action_confirmation(
        action_id=action_id,
        dry_run=dry,
        confirmation=confirmation,
        requested_registry_fields=requested_fields,
    )
    action_blob = action_model.to_dict() if action_model else {"action_id": action_id}
    planned_action = {
        "human": list(human_lines),
        "mutation_argv": [list(m.argv) for m in mutations],
        "clear_server": clear_server,
        "clear_autoconfig": clear_autoconfig,
        "requested_registry_fields": list(requested_fields),
    }
    preview_row = _proxy_disable_audit_row(
        event_kind="preview_requested" if dry else "execute_requested",
        action_id=action_id,
        decision=decision,
        dry_run=dry,
        mutated=False,
        reason=reason,
        before=merged_before_preview,
        action=action_blob,
        planned_action=planned_action,
    )
    preview_audit_id = _append_proxy_disable_audit(repo, preview_row)

    if dry:
        payload = {
            "action_id": action_id,
            "decision": decision,
            "dry_run": True,
            "mutated": False,
            "reason": reason,
            "audit_event_id": preview_audit_id,
            "before": merged_before_preview,
            "after": None,
            "action": action_blob,
        }
        if emit_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("\n[dry-run] No registry writes or rollback snapshot persisted. Audit row appended.")
        return 0

    if decision != "ALLOW":
        blocked_row = _proxy_disable_audit_row(
            event_kind="blocked_missing_confirmation" if reason == "missing_confirmation" else "blocked_confirmation_or_policy",
            action_id=action_id,
            decision="BLOCK",
            dry_run=False,
            mutated=False,
            reason=reason,
            before=merged_before_preview,
            action=action_blob,
            planned_action=planned_action,
        )
        audit_event_id = _append_proxy_disable_audit(repo, blocked_row)
        payload = {
            "action_id": action_id,
            "decision": "BLOCK",
            "dry_run": False,
            "mutated": False,
            "reason": reason,
            "audit_event_id": audit_event_id,
            "before": merged_before_preview,
            "after": None,
            "action": action_blob,
        }
        if emit_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(f"Blocked: {reason}. Provide --dry-run false --confirm {CONFIRMATION_PHRASE}.")
        return 1

    capture_pre = capture_wininet_snapshot(run=run)
    rollback_plan = build_rollback_plan(capture_pre)
    append_proxy_snapshots_jsonl(repo, merge_snapshot_payload(capture_pre, rollback_plan))

    results = apply_mutations(mutations, dry_run=False)
    reg_after = read_proxy_registry(run=run)
    verification = verify_proxy_disabled(reg_after)
    merged_after = registry_with_parsed(reg_after, parse_proxy_server(reg_after.proxy_server))

    audit = {
        "audit_event_id": str(uuid.uuid4()),
        "type": "repair",
        "subtype": "proxy_disable",
        "event_kind": "successful_mutation",
        "action_id": action_id,
        "decision": "ALLOW",
        "dry_run": False,
        "mutated": True,
        "reason": "confirmed_allowlisted_action",
        "timestamp": utc_now_iso(),
        "snapshot_id": capture_pre.snapshot_id,
        "before": capture_pre.to_jsonable(),
        "action": action_blob,
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
    validation_row = _proxy_disable_audit_row(
        event_kind="post_change_validation",
        action_id=action_id,
        decision="ALLOW" if verification.ok else "BLOCK",
        dry_run=False,
        mutated=False,
        reason=verification.detail,
        before=capture_pre.to_jsonable(),
        after=merged_after,
        action=action_blob,
        planned_action=planned_action,
        snapshot_id=capture_pre.snapshot_id,
        verification_result=verification.to_dict(),
        rollback_plan=rollback_plan,
    )
    validation_audit_event_id = _append_proxy_disable_audit(repo, validation_row)

    # Reliability events (schema 2.0) alongside v1 repair_audit
    observed_pre = dict(capture_pre.values)
    proxy_s_raw = observed_pre.get("ProxyServer")
    proxy_s = proxy_s_raw if isinstance(proxy_s_raw, str) else ""
    incident = v2_incident_id_from_proxy(proxy_s if proxy_s else None)
    corr = v2_correlation_key(proxy_s if proxy_s else None)
    snapshot_eid = v2_log_snapshot(
        repo,
        observed=observed_pre,
        incident_id=incident,
        correlation_key_val=corr,
    )

    repair_primary_eid = ""
    for mutation, res in zip(mutations, results):
        argv_list = list(mutation.argv)
        action_type = "disable_wininet_hkcu_proxy"
        if argv_list[:2] == ["reg", "delete"]:
            action_type = "delete_wininet_proxyserver_value"
        rd = {
            "exit_code": res.returncode,
            "stdout": res.stdout[:4000] if res.stdout else "",
            "stderr": res.stderr[:4000] if res.stderr else "",
            "command_success": res.returncode == 0,
        }
        rid = v2_log_repair_attempt(
            repo,
            snapshot_event_id=snapshot_eid,
            incident_id=incident,
            correlation_key_val=corr,
            mutation_argv=argv_list,
            result=rd,
            action_type=action_type,
        )
        if not repair_primary_eid:
            repair_primary_eid = rid

    if not repair_primary_eid:
        repair_primary_eid = snapshot_eid

    obs_verif = {
        "ProxyEnable": reg_after.proxy_enable,
        "ProxyServer": reg_after.proxy_server,
    }
    v2_log_verification(
        repo,
        repair_event_id=repair_primary_eid,
        incident_id=incident,
        correlation_key_val=corr,
        expected={"ProxyEnable": verification.expected_proxy_enable},
        observed=dict(obs_verif),
        ok=verification.ok,
        interpretation=verification.detail,
        confidence=(0.99 if verification.ok else 0.4),
    )

    parsed_prev = v2_parse_observed_proxy(observed_pre)
    uniq_ports: list[int] = []
    if isinstance(parsed_prev.get("localhost_port"), int):
        uniq_ports.append(parsed_prev["localhost_port"])

    v2_update_incident_summary(
        repo,
        incident_id=incident,
        correlation_key_val=corr,
        symptom={
            "proxy_server": proxy_s or observed_pre.get("ProxyServer"),
            "proxy_mode": parsed_prev.get("proxy_mode"),
            # Drift summaries set this True when drift_detected rows exist for the incident.
            "proxy_reenabled_repeatedly": False,
        },
        counters_patch={
            "repair_attempts": len(results),
            "successful_repairs": (1 if verification.ok else 0),
            "unique_ports": uniq_ports,
        },
        assessment={
            "repair_effectiveness": ("temporary_success" if verification.ok else "failed_verify"),
            "root_cause_status": "unknown",
            "likely_category": "pending_investigation",
            "confidence": (0.75 if verification.ok else 0.35),
        },
        recommended_next_actions=list(_V2_REL_INCIDENT_HELP),
    )

    payload = {
        "action_id": action_id,
        "decision": "ALLOW" if verification.ok else "BLOCK",
        "dry_run": False,
        "mutated": True,
        "reason": "mutation_applied_validation_ok" if verification.ok else verification.detail,
        "audit_event_id": str(audit["audit_event_id"]),
        "validation_audit_event_id": validation_audit_event_id,
        "before": capture_pre.to_jsonable(),
        "after": merged_after,
        "action": action_blob,
    }

    if emit_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if verification.ok else 1

    print("Applied mutations; see logs\\repair_audit.jsonl for snapshot + verification.")

    if not verification.ok:
        print(
            f"WARNING: verification failed ({verification.detail}); re-check proxy-status.",
            file=sys.stderr,
        )
        return 1
    print("Verification: ProxyEnable reported disabled.")

    soak_minutes = float(getattr(args, "soak_minutes", 0) or 0)
    if soak_minutes > 0:
        from .proxy_guard.soak import run_remediation_soak

        print(f"\nSoak: monitoring ProxyEnable for {soak_minutes:g} minute(s) (no auto-reset loop)...")
        soak_result = run_remediation_soak(
            soak_minutes=soak_minutes,
            poll_seconds=float(getattr(args, "soak_poll_seconds", 5.0) or 5.0),
            run=run,
        )
        append_jsonl_core(
            repo / "logs" / "repair_audit.jsonl",
            {
                "type": "repair",
                "subtype": "proxy_disable_soak",
                "timestamp": utc_now_iso(),
                "soak": soak_result.to_dict(),
            },
        )
        if soak_result.status == "REMEDIATION_NOT_STICKY":
            print(f"\nSOAK RESULT: {soak_result.status}")
            print(soak_result.detail)
            print("Do not run reset_proxy in a loop. Identify the active reverter first.")
            return 1
        print(f"\nSOAK RESULT: {soak_result.status} — {soak_result.detail}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Capture a frozen ``LiveNetworkSnapshot`` JSON file and emit a locator JSONL row.

    Purpose:
        Operator-facing export of correlate-at-once probes + registry/socket/process context for audits
        without invoking v2 hypothesis scoring.

    Args:
        args: ``repo_root`` optional Path to toolkit checkout.

    Returns:
        ``0`` after persist; ``2`` when gated off Windows platforms.

    Side effects:
        Writes ``reports/snapshots/<UTC_ts>.json`` (timestamp from ``utc_now_iso`` slug) and appends one
        object to ``logs/network_snapshots.jsonl`` referencing that path plus a UUID ``snapshot_id``.

    Output guarantees:
        Snapshot dictionary matches ``LiveNetworkSnapshot.to_dict`` augmented with ``commands_executed``.
        Timestamp fields originate from ``utc_now_iso`` (UTC, ISO-like string consistency with other artefacts).

    Idempotency:
        Each invocation issues fresh probes; filenames differ per run even if host state repeats.

    Failure modes:
        Subprocess probes may fail softly inside ``collect_features``/netstat parity—inspect payload fields
        and stderr-equivalent booleans rather than assuming full transport success.

    Audit Notes:
        Pair file path printed on stdout with the JSONL append for incident tooling queries.
    """
    if (code := exit_code_if_not_windows("snapshot")) is not None:
        return code
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
    """Run live ``LiveNetworkSnapshot`` capture, deterministic v2 scoring, proof (optional), and policy export.

    Purpose:
        Materialize replayable artefacts: hypothesis ranks, ALLOW/PREVIEW/BLOCK rows, optional proof blob,
        trust and uncertainty aggregates, tiered recommendation dict, and append-only audits for review.

    Args:
        args: Expected attributes include:
            ``repo_root`` — optional toolkit root Path.
            ``replay_run_id`` — when truthy, short-circuit to offline ``cmd_replay_live_run`` (no probes).
            ``live_proofs`` — when True, invokes ``run_localhost_proxy_https_proof``; failures degrade trust.
            ``emit_json`` — when True without ``emit_both``, stdout receives live payload JSON only.
            ``emit_both`` — when True without ``emit_json``, stdout receives human explanatory text plus
            ``JSON_PAYLOAD_*`` wrappers around identical JSON.

    Returns:
        ``0`` on completed live run or replay. Non-zero values propagate from replay paths or gate helpers.

    Raises:
        None deliberately; malformed filesystem JSON raises during downstream replay tooling only.

    Side effects:
        Writes ``reports/snapshots/<diagnosis_uuid>.json`` (embedded observations JSON), overwrites
        ``reports/last_diagnosis_live.json``, appends rows to ``logs/network_snapshots.jsonl``,
        ``logs/decision_audit.jsonl``, and ``logs/decision_runs.jsonl``.

    Decision intent / constraints:
        Hypothesis confidences rank plausibility; policy mapping consumes proof outcomes and trust aggregates.
        Heuristic scores are not calibrated probabilities.

    Failure modes:
        Mutually exclusive stdout modes yield exit ``2`` when both ``emit_json`` and ``emit_both`` are set.

    Audit Notes:
        Cross-check ``hypotheses_ranked`` against ``reports/…/<uuid>.json`` observations and rerun
        ``python -m src replay RUN_ID`` for parity. Corrupt tails in append-only logs require line-skip parsers.

        Recovery guidance: rerun live diagnosis after remediation; duplicate ``run_id`` lines are unexpected—
        prefer append-only scanners that honour last matching row semantics used by replay finders.
    """
    replay_id = getattr(args, "replay_run_id", None)
    if replay_id:
        return cmd_replay_live_run(args)

    if getattr(args, "emit_json", False) and getattr(args, "emit_both", False):
        print("diagnose-live: use only one of --json or --both.", file=sys.stderr)
        return 2

    if (code := exit_code_if_not_windows("diagnose-live")) is not None:
        return code
    repo = _repo_root(args.repo_root)
    snapshot, cmds = build_live_network_snapshot(run=subprocess.run)
    ranked = score_live_snapshot(snapshot)
    proofs_enabled = bool(getattr(args, "live_proofs", False))
    localhost_proof = None
    proof_engine_error: str | None = None
    if proofs_enabled:
        try:
            localhost_proof = run_localhost_proxy_https_proof()
        except Exception as exc:  # noqa: BLE001 — surface proof-layer failure as degraded mode
            proof_engine_error = f"{type(exc).__name__}:{exc}"
    trust_bundle = assess_trust(
        snapshot,
        proof_result=localhost_proof,
        proofs_requested=proofs_enabled,
        proof_engine_error=proof_engine_error,
    )
    adversarial = adversarial_hints(snapshot)
    ranked_tuples = [(s.hypothesis, s.confidence, s.evidence) for s in ranked]
    hypothesis_decisions = build_hypothesis_decisions(
        ranked=ranked_tuples,
        localhost_proxy_proof=localhost_proof,
        proofs_enabled=proofs_enabled,
        trust_assessment=trust_bundle,
    )

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
    proof_engine_blob: dict[str, Any] = {}
    if proofs_enabled and localhost_proof is not None:
        proof_engine_blob["localhost_proxy_https_contrast"] = localhost_proof.to_dict()

    live_payload: dict[str, Any] = {
        "diagnosis_id": diagnosis_id,
        "generated_at_utc": utc_now_iso(),
        "engine": "live_v2",
        "script_version": SCRIPT_VERSION,
        "machine": _fingerprint(),
        "live_snapshot_ref": str(snap_path),
        "hypotheses_ranked": ranked_dicts(ranked),
        "hypothesis_decisions": hypothesis_decisions,
        "proof_engine": proof_engine_blob,
        "decision_policy": {
            "proofs_requested": proofs_enabled,
            "rules": (
                "CONFIRMED proof → ALLOW (safe-tier only; no auto-destructive). "
                "High confidence unproven → PREVIEW only. Low confidence → BLOCK. "
                "Uncertain band → PREVIEW with confirmation."
            ),
        },
        "uncertainty": {
            **trust_bundle.to_dict(),
            "adversarial_hints": list(adversarial),
        },
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

    primary_decision = hypothesis_decisions[0] if hypothesis_decisions else {}
    append_jsonl_core(
        repo / "logs" / "decision_audit.jsonl",
        {
            "type": "diagnosis_live",
            "timestamp": utc_now_iso(),
            "diagnosis_id": diagnosis_id,
            "script_version": SCRIPT_VERSION,
            "machine": live_payload["machine"],
            "hypotheses": live_payload["hypotheses_ranked"],
            "hypothesis_policy": {
                "decision": primary_decision.get("decision"),
                "proof_status": primary_decision.get("proof_status"),
                "proofs_requested": proofs_enabled,
                "trust_aggregate": trust_bundle.trust_aggregate,
                "degraded_mode": trust_bundle.degraded_mode,
            },
            "primary": top.hypothesis,
            "confidence": top.confidence,
            "safety_tier": "diagnose",
        },
    )
    append_jsonl_core(
        repo / "logs" / "decision_runs.jsonl",
        {
            "schema_version": "live_run_audit_v1",
            "type": "live_run_audit",
            "run_id": diagnosis_id,
            "timestamp_utc": live_payload["generated_at_utc"],
            "script_version": SCRIPT_VERSION,
            "machine": live_payload["machine"],
            "observations": snapshot.to_dict(),
            "hypotheses_ranked": live_payload["hypotheses_ranked"],
            "hypothesis_decisions": hypothesis_decisions,
            "proof_engine": proof_engine_blob,
            "proof_engine_error": proof_engine_error,
            "proofs_requested": proofs_enabled,
            "uncertainty": live_payload["uncertainty"],
            "commands_executed": list(cmds),
            "live_snapshot_ref": str(snap_path),
            "primary_hypothesis": top.hypothesis,
            "primary_confidence": top.confidence,
        },
    )

    if getattr(args, "emit_json", False):
        print(json.dumps(live_payload, indent=2, ensure_ascii=False))
        return 0
    print("=== Live diagnosis (v2) ===")
    print()
    print(
        "What this does: captures a read-only observability snapshot (registry, probes, listeners), "
        "ranks v2 hypotheses from those signals, attaches policy rows (ALLOW/PREVIEW/BLOCK), "
        "and writes reports/last_diagnosis_live.json plus append-only audit JSONL (replayable)."
    )
    if proofs_enabled:
        print(
            "Proof mode: ran the localhost-proxy HTTPS contrast (curl via proxy vs bypass) where applicable; "
            "see proof_engine and hypothesis_decisions in the saved JSON."
        )
    else:
        print(
            "Proof mode: off (proof_status may read UNPROVEN). For causal contrast, run: "
            "`python -m src diagnose --proof` or `python -m src diagnose-live --proofs`."
        )
    print()
    print(f"Diagnosis ID: {diagnosis_id}")
    print()
    print("Summary (primary hypothesis)")
    print("----------------------------")
    print(explain)
    print()
    print("Ranked hypotheses (top 10, deterministic scores — not calibrated probabilities)")
    print("--------------------------------------------------------------------")
    for row in live_payload["hypotheses_ranked"][:10]:
        print(f"  {row['rank']}. {row['hypothesis']}: {float(row['confidence']):.2f}")
        for ev in row.get("evidence") or []:
            print(f"      - {ev}")
    print(f"\nSnapshot: {snap_path}")
    print(f"Last live payload: {last_path}")
    if hypothesis_decisions:
        hd0 = hypothesis_decisions[0]
        print(
            f"\nPolicy (primary hypothesis): decision={hd0.get('decision')} "
            f"proof_status={hd0.get('proof_status')} (use hypothesis_decisions in JSON)",
        )
    ub = live_payload.get("uncertainty") or {}
    if ub:
        ta = float(ub.get("trust_aggregate") or 0.0)
        print(
            f"\nUncertainty: trust_aggregate={ta:.2f} degraded_mode={ub.get('degraded_mode')} "
            f"adversarial_hints={ub.get('adversarial_hints') or []}",
        )
    if getattr(args, "emit_both", False):
        print()
        print("JSON_PAYLOAD_START")
        print(json.dumps(live_payload, indent=2, ensure_ascii=False))
        print("JSON_PAYLOAD_END")
    return 0


def cmd_replay_live_run(args: argparse.Namespace) -> int:
    """Offline replay against ``live_run_audit_v1`` rows in ``logs/decision_runs.jsonl``.

    Purpose:
        Re-score embedded observations deterministically without live probes and compare recomputed ranks,
        confidences, and policy rows to archival values for forensic drift detection.

    Args:
        args: ``repo_root`` optional Path; ``replay_run_id`` non-empty run UUID; ``emit_json`` for JSON-only
            stdout wrapping ``replay_execution`` plus metadata; ``emit_both`` for human narration plus framed JSON.

    Returns:
        ``0`` when record located and formatted output emitted.
        ``1`` when schema row missing or log absent.
        ``2`` when run id omitted or incompatible stdout flags set.

    Side effects:
        None beyond reading JSONL lines from disk—no probes, writes, or network.

    Raises:
        None deliberately.

    Audit Notes:
        Proof curl steps archived in-record are not replayed live; divergence may indicate scorer changes,
        not host tampering. Treat mismatches as cues to rebuild baselines after intentional rule updates.

    Engineering Notes:
        ``find_decision_run`` prefers the last matching line for duplicate ids—tests rely on ordering when
        simulating corrections.
    """
    if getattr(args, "emit_json", False) and getattr(args, "emit_both", False):
        print("replay: use only one of --json or --both.", file=sys.stderr)
        return 2
    repo = _repo_root(args.repo_root)
    run_id = str(getattr(args, "replay_run_id", "") or "").strip()
    if not run_id:
        print(
            "replay: provide a run_id (e.g. `python -m src replay <uuid>`); "
            "matches diagnosis_id from logs/decision_runs.jsonl",
            file=sys.stderr,
        )
        return 2
    rec = find_decision_run(repo, run_id)
    if rec is None:
        print(
            f"replay: no {_REPLAY_SCHEMA_VERSION} record for run_id={run_id!r} in {repo / 'logs' / 'decision_runs.jsonl'}",
            file=sys.stderr,
        )
        return 1
    report = build_replay_report(rec)
    json_out = {
        "replay_execution": report,
        "stored_snapshot_ref": rec.get("live_snapshot_ref"),
        "stored_commands_count": len(rec.get("commands_executed") or []),
        "stored_script_version": rec.get("script_version"),
        "replay_script_version_now": SCRIPT_VERSION,
        "explain": {
            "what": "Offline replay re-scores hypotheses from the embedded observation blob only (no new probes).",
            "verify": "Compares replayed confidences, order, and policy fields to the stored audit row.",
        },
    }
    if getattr(args, "emit_json", False):
        print(json.dumps(json_out, indent=2, ensure_ascii=False))
        return 0
    print("=== Replay (offline) ===")
    print()
    print(
        "What this does: loads one `live_run_audit_v1` row from logs/decision_runs.jsonl by run_id, "
        "re-runs deterministic scoring on the frozen observations, and shows whether stored vs replayed "
        "results still match (confidence drift, order, decision fields)."
    )
    print(f"Run ID: {run_id}")
    print()
    print(format_replay_flow_text(report))
    if getattr(args, "emit_both", False):
        print()
        print("JSON_PAYLOAD_START")
        print(json.dumps(json_out, indent=2, ensure_ascii=False))
        print("JSON_PAYLOAD_END")
    return 0


def _read_live_or_legacy(repo: Path) -> tuple[dict[str, Any], str]:
    """Normalize access to persisted diagnosis artefacts (live v2 preferred over legacy).

    Args:
        repo: Toolkit root containing ``reports/``.

    Returns:
        Tuple ``(payload_dict, "live"|"legacy")`` describing which snapshot was sourced.

    Raises:
        ``FileNotFoundError`` when neither ``last_diagnosis_live.json`` nor ``last_diagnosis.json`` exists.

    Failure modes / malformed JSON:
        Propagate ``json.JSONDecodeError`` from callers if files are corrupt—repair by rerunning diagnoses.
    """
    live = repo / "reports" / "last_diagnosis_live.json"
    legacy = repo / "reports" / "last_diagnosis.json"
    if live.is_file():
        return json.loads(live.read_text(encoding="utf-8")), "live"
    if legacy.is_file():
        return json.loads(legacy.read_text(encoding="utf-8")), "legacy"
    raise FileNotFoundError(
        "No reports/last_diagnosis_live.json or reports/last_diagnosis.json - "
        "run `python -m src diagnose-live` or `python -m src diagnose` first."
    )


def _normalize_recommendations_blob(payload: dict[str, Any]) -> dict[str, Any]:
    """Isolate the recommendations tier dict from mixed diagnosis artefacts.

    Args:
        payload: Either legacy ``reports/last_diagnosis.json`` blob or ``engine=live_v2`` payloads.

    Returns:
        Nested dict containing ``diagnose``, ``repair_safe``, ``guided_repair``, ``advanced_repair`` keys when
        authored; defaults to empty mappings when tiers absent—callers iterate defensively.

    Constraints:
        Does not coerce missing scripts or validate casing; malformed lists surface when iterated by callers only.
    """
    if payload.get("engine") == "live_v2":
        return payload.get("recommendations") or {}
    return payload.get("recommendations") or {}


def cmd_repair_preview(args: argparse.Namespace) -> int:
    """Emit tiered repair suggestions from persisted diagnosis artefacts (read-only).

    Purpose:
        Surface ``diagnose``, ``repair_safe``, ``guided_repair``, ``advanced_repair`` entries so operators can
        plan next steps without executing scripts.

    Args:
        args: ``repo_root`` optional; ``emit_json_preview`` emits structured JSON tiers only;
            ``emit_both_preview`` appends framed JSON after human stdout.

    Returns:
        ``0`` normally; ``2`` when both structured-output flags contradict.

    Raises:
        ``FileNotFoundError`` propagates via ``_read_live_or_legacy`` when neither artefact exists.

    Side effects:
        stdout/stderr only—no subprocess launches or filesystem writes beyond reading diagnosis JSON files.

    Data handling:
        Accepts legacy v1 payloads and live v2 ``engine=live_v2`` shapes via ``_normalize_recommendations_blob``.

    Audit Notes:
        Always pair preview output with the underlying ``reports/last_diagnosis*.json`` timestamp before acting.
    """
    repo = _repo_root(args.repo_root)
    payload, source = _read_live_or_legacy(repo)
    blob = _normalize_recommendations_blob(payload)
    sections = ("diagnose", "repair_safe", "guided_repair", "advanced_repair")
    emit_json_preview = getattr(args, "emit_json_preview", False)
    emit_both_preview = getattr(args, "emit_both_preview", False)
    if emit_json_preview and emit_both_preview:
        print("preview: use only one of --json or --both.", file=sys.stderr)
        return 2

    explain_block = {
        "what": (
            "Lists recommended next steps by tier from the last diagnosis artefact — nothing is executed."
        ),
        "source": (
            "`live` means reports/last_diagnosis_live.json; `legacy` means reports/last_diagnosis.json (v1)."
        ),
    }
    tiers: dict[str, list[dict[str, Any]]] = {}
    for section in sections:
        tiers[section] = [dict(x) for x in blob.get(section, []) if isinstance(x, dict)]
    preview_json = {
        "cli": "preview",
        "artifact_source": source,
        "primary_hypothesis": payload.get("primary_hypothesis") or payload.get("selected_root_cause"),
        "explain": explain_block,
        "tiers": tiers,
    }

    json_only_preview = emit_json_preview and not emit_both_preview
    if json_only_preview:
        print(json.dumps(preview_json, indent=2, ensure_ascii=False))
        return 0
    print("=== Repair preview (read-only) ===")
    print()
    print(
        "What this does: shows scripted / guided repair suggestions from your last diagnose run. "
        "No commands are executed. Prefer `repair-safe --apply` only after reviewing LOW-risk items."
    )
    print(f"Source artefact: {source} (last_diagnosis_live.json preferred when present).")
    print()
    print(f"Repair preview source: {source}")
    print()
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
    if emit_both_preview:
        print()
        print("JSON_PAYLOAD_START")
        print(json.dumps(preview_json, indent=2, ensure_ascii=False))
        print("JSON_PAYLOAD_END")
    return 0


def cmd_repair_apply(args: argparse.Namespace) -> int:
    """Optionally launch the first eligible LOW-tier ``scripts/*.bat`` recommendation after confirmations.

    Purpose:
        Provide the same guarded elevation path historically exposed through ``repair-safe --apply``, while
        preferring live artefacts when present.

    Args:
        args: ``repo_root`` optional; ``dry_run`` suppresses subprocess launch entirely.

    Returns:
        ``0`` when dry-run exits, runnable script launches successfully, or no runnable LOW actions exist.
        ``1`` operator cancel/wrong passphrase where applicable downstream.
        ``2`` gated off Windows or path guard forbids elevation target.

    Side effects:
        Non-dry-run may spawn elevated PowerShell ``Start-Process`` and append ``logs/decision_feedback.jsonl``.

    Idempotency:
        Re-running may re-elevate batches if operator confirms ``RUN`` again—scripts themselves must be safe
        against duplicate application.

    Audit Notes:
        Skips ``proxy_disable`` action keys so HKCU remediation stays on the typed phrase CLI path—do not bypass.

        Evidence: correlate feedback JSON lines with rerun ``diagnose`` snapshots to judge effectiveness.
    """
    if (code := exit_code_if_not_windows("repair-apply")) is not None:
        return code
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
        print("Use `python -m src proxy disable --dry-run false --confirm DISABLE_WININET_PROXY` for HKCU disables.")
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
