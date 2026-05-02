"""HKCU WinINET drift polling with process correlation and probabilistic attribution.

Module responsibility:
    Runs the ``python -m src proxy-watch`` polling loop: capture WinINET snapshots, classify
    transitions, collect process inventory, rank attribution candidates, append audit JSONL, and print
    human-readable alerts to stderr.

System placement:
    Called from :func:`~src.command_handlers.cmd_proxy_watch`. Depends on
    :mod:`~src.proxy_guard.state`, :mod:`~src.proxy_guard.wininet_change_diff`,
    :mod:`~src.proxy_guard.process_inventory`, :mod:`~src.proxy_guard.change_attribution`, and
    :func:`~src.proxy_guard.audit.emit_proxy_change_detected_audit`.

Key invariants:
    * This module never mutates the registry or network stack.
    * ``auto_rollback`` read from policy never performs a live rollback here—only emits an advisory
      stderr banner pointing operators to gated restore commands.

Input assumptions:
    * ``prior_state`` starts as ``None`` so the initial poll establishes baseline without logging drift.

Output guarantees:
    * Emits one JSON document to stdout on the first poll: ``{"event": "initial_poll", ...}`` with
      ``timestamp_utc`` from :func:`~src.core.time_utils.utc_now_iso`.
    * One JSONL audit row per detected drift cycle (schema in :mod:`~src.proxy_guard.audit`).

Side effects:
    * Indirect subprocess execution via injected ``run`` into snapshot/inventory callers (typically
      ``reg query``, PowerShell, and argv-only probing per those modules—not ``shell=True`` here).

Failure modes:
    * Unreadable policy JSON files are skipped; defaults apply (see ``load_watch_policy``).
    * Attribution confidence may be near zero when CIM snapshots or listener probes fail downstream.

Audit Notes:
    * Review ``logs/proxy_guard.jsonl`` beside stderr banners when investigating unexpected proxy
      flips—timestamps tie human output to persisted ``diff``/``attribution`` payloads without claiming
      registry-write proof (see attribution ``limitations`` in nested JSON).

Engineering Notes:
    * Keeps attribution and policy separate: risk tiering stays in ``diff_wininet_states`` outputs;
      ``evidence_boost`` adjusts scoring mass only inside ``attribute_proxy_change``.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import subprocess

from ..core.time_utils import utc_now_iso
from .audit import emit_proxy_change_detected_audit
from .change_attribution import attribute_proxy_change
from .process_inventory import capture_process_inventory
from .state import snapshot_wininet_state
from .wininet_change_diff import diff_wininet_states


def load_watch_policy(repo_root: Path) -> dict[str, Any]:
    """Resolve operator policy for ``proxy-watch`` drift decisions and attribution nudges.

    Args:
        repo_root: Toolkit checkout root containing ``config/`` / ``shared/``.

    Returns:
        Dictionary with ``allowed_process_names``, ``allowed_exe_paths``, ``blocked_process_names``,
        ``allowed_proxy_ports``, ``deny_unknown_localhost_proxy``, ``auto_rollback``
        (and any extra keys callers forward—unknown keys are ignored by this module unless used
        downstream). Returns conservative defaults when no readable JSON exists.

    Side effects:
        Reads up to four candidate paths; opens each at most once. Never writes policy files.

    Failure modes:
        Missing files or ``JSONDecodeError`` skip that path; ``OSError`` on read skips that path.

    Raises:
        None intentionally—always returns a dict suitable for ``diff_wininet_states`` /
        ``attribute_proxy_change``.
    """

    candidates = [
        repo_root / "config" / "proxy_policy.json",
        repo_root / "config" / "proxy_policy.example.json",
        repo_root / "shared" / "proxy_policy.example.json",
    ]
    seen: Path | None = None
    for p in candidates:
        if not p.is_file():
            continue
        try:
            blob = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(blob, dict):
            seen = p
            return dict(blob)
    _ = seen
    return {
        "allowed_process_names": [],
        "allowed_exe_paths": [],
        "blocked_process_names": [],
        "allowed_proxy_ports": [],
        "deny_unknown_localhost_proxy": True,
        "auto_rollback": False,
    }


def _decide_action(policy: dict[str, Any], diff: dict[str, Any]) -> dict[str, str]:
    """Map classifier ``risk_level`` plus policy knobs into opaque ``decision`` JSON for audit logs.

    Args:
        policy: Loaded watch policy blob (typically includes ``auto_rollback`` bool).
        diff: Structured diff containing ``changed`` and ``risk_level``.

    Returns:
        Dict with string keys ``action`` ∈ ``observe`` | ``alert`` | ``rollback_recommended``
        (when ``auto_rollback`` is true alongside high risk, without executing rollback) and
        ``reason`` explaining the coarse operator hint.

    Side effects:
        None—pure branching on provided dict contents.

    Audit Notes:
        Values are persisted verbatim under JSONL ``decision``; they do **not** trigger automated
        repair paths in ``run_proxy_watch_loop``.
    """
    changed = bool(diff.get("changed"))
    risk = str(diff.get("risk_level") or "low")

    auto_rb = bool(policy.get("auto_rollback"))
    if not changed:
        return {"action": "observe", "reason": "no_proxy_core_change"}

    if auto_rb and risk == "high":
        return {
            "action": "rollback_recommended",
            "reason": "policy_auto_rollback_flag_set_but_execution_remains_confirmation_gated_elsewhere",
        }
    if risk == "high":
        return {"action": "alert", "reason": "high_risk_proxy_transition"}
    if risk == "medium":
        return {"action": "alert", "reason": diff.get("reason") or "medium_risk_proxy_transition"}
    return {"action": "observe", "reason": diff.get("reason") or "low_risk_transition"}


def _print_human_banner(
    *,
    diff: dict[str, Any],
    attribution: dict[str, Any],
    decision: dict[str, str],
) -> None:
    """Format drift, attribution envelope, and policy decision onto stderr for terminal operators.

    Args:
        diff: Structured diff including ``changed_fields``, ``risk_level``, ``before``/``after`` slices.
        attribution: Output of :func:`~src.proxy_guard.change_attribution.attribute_proxy_change`.
        decision: Output of :func:`_decide_action` (``action`` / ``reason``).

    Returns:
        None.

    Side effects:
        Prints multiple lines to ``sys.stderr`` only (stdout reserved for machine JSON elsewhere).
    """

    before = diff.get("before") or {}
    after = diff.get("after") or {}
    msg = ["", "[PROXY CHANGE DETECTED]"]
    if "ProxyServer" in (diff.get("changed_fields") or []):
        msg.append("ProxyServer changed:")
        msg.append(f"  before: {before.get('proxy_server')}")
        msg.append(f"  after: {after.get('proxy_server')}")
    if "ProxyEnable" in (diff.get("changed_fields") or []):
        msg.append(f"ProxyEnable: {before.get('proxy_enable')} -> {after.get('proxy_enable')}")
    msg.append("")
    msg.append(f"Risk: {str(diff.get('risk_level') or 'unknown').upper()}")

    suspect = attribution.get("primary_suspect") if isinstance(attribution, dict) else None
    msg.append("")
    msg.append("Likely process:")
    if isinstance(suspect, dict):
        msg.append(f"  PID: {suspect.get('pid')}")
        msg.append(f"  Name: {suspect.get('name')}")
        msg.append(f"  Path: {suspect.get('exe')}")
        msg.append(f"  Parent: {suspect.get('parent_name')}")
        msg.append(f"  Confidence: {attribution.get('confidence')}")
    else:
        msg.append("  (no confident scorer match — see attribution JSON)")
    msg.append("")
    msg.append("Evidence:")
    for line in attribution.get("evidence") or []:
        msg.append(f"- {line}")
    msg.append("")
    msg.append(f"Recommended policy action: {decision.get('action')} — {decision.get('reason')}")
    print("\n".join(msg), file=sys.stderr)


def run_proxy_watch_loop(
    *,
    repo_root: Path,
    interval_seconds: float,
    once: bool,
    run: Callable[..., Any] = subprocess.run,
    evidence_boost: float = 0.0,
) -> None:
    """Poll WinINET snapshots until interrupted; on drift, inventory processes and persist audit rows.

    Args:
        repo_root: Toolkit root hosting ``logs/`` for JSONL sinks and ``config/`` for optional policy.
        interval_seconds: Sleep between polls; clamped downstream to ``>= 1.0`` seconds.
        once: When True, terminates after baseline plus one drift-check cycle (still prints
            ``initial_poll`` once).
        run: Injectable ``subprocess.run`` surrogate for tests (passed through to snapshot/inventory).
        evidence_confidence_boost: Additive score mass forwarded to ``attribute_proxy_change``
            (typically from optional Procmon CSV path parsed by CLI before calling this routine).

    Returns:
        ``None``. Loop runs until ``KeyboardInterrupt`` in normal interactive use unless ``once``.

    Side effects:
        Writes append-only NDJSON lines to ``logs/proxy_guard.jsonl`` via
        ``emit_proxy_change_detected_audit`` whenever ``diff.changed`` is true (after baseline).
        Writes human summaries to stderr. First iteration emits JSON to stdout once.

    Raises:
        None by design—subprocess faults are swallowed within snapshot/inventory layers.

    Audit Notes:
        Correlate stdout ``initial_poll`` ``state`` with subsequent JSONL timestamps when narrowing
        which configuration transition caused user-visible breakage.
    """

    policy = load_watch_policy(repo_root)
    prior_state: dict[str, Any] | None = None
    printed_poll = False
    while True:
        now_state = snapshot_wininet_state(run=run)
        if prior_state is not None:
            diff = diff_wininet_states(prior_state, now_state, policy=policy)
            if diff.get("changed"):
                parsed = now_state.get("parsed_proxy_server") or {}
                port_hint = parsed.get("localhost_port")
                port_int = None
                if isinstance(port_hint, int):
                    port_int = port_hint
                elif isinstance(port_hint, str) and port_hint.strip().isdigit():
                    port_int = int(port_hint.strip())

                inventory = capture_process_inventory(proxy_localhost_port=port_int, run=run)
                attribution = attribute_proxy_change(
                    proxy_diff=diff,
                    current_state=now_state,
                    inventory=inventory,
                    policy=policy,
                    evidence_confidence_boost=evidence_boost,
                )

                decision = _decide_action(policy, diff)
                emit_proxy_change_detected_audit(
                    repo_root,
                    diff=diff,
                    attribution=attribution,
                    decision=decision,
                )
                _print_human_banner(diff=diff, attribution=attribution, decision=decision)

                if bool(policy.get("auto_rollback")):
                    banner = "[policy] auto_rollback=true but proxy-watch never executes live rollback here — use proxy-guard or typed restores."
                    print(banner, file=sys.stderr)

        prior_state = now_state

        if not printed_poll:
            print(
                json.dumps({"event": "initial_poll", "timestamp_utc": utc_now_iso(), "state": prior_state}, indent=2),
                flush=True,
            )
            printed_poll = True

        if once:
            break
        time.sleep(max(1.0, interval_seconds))
