"""CLI handlers for ``python -m src`` proxy drift commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.windows_cli import exit_code_if_not_windows
from src.proxy_drift.boot_trace import run_boot_trace_loop
from src.proxy_drift.guardian import run_dead_proxy_guardian_loop, run_dead_proxy_guardian_once
from src.proxy_drift.guardian_task import (
    install_guardian_task,
    preview_install_guardian_task,
    uninstall_guardian_task,
)
from src.proxy_drift.proxy_fix import apply_proxy_fix
from src.proxy_drift.safe_search import safe_search
from src.proxy_drift.startup_inventory import collect_startup_inventory, format_startup_table


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_startup_inventory(args: argparse.Namespace) -> int:
    """Targeted startup inventory (no full profile recursion)."""
    if (code := exit_code_if_not_windows("startup-inventory")) is not None:
        return code
    repo = Path.cwd()
    audit = repo / "logs" / "startup_inventory.jsonl"
    payload = collect_startup_inventory(repo_root=repo, audit_path=audit)
    if getattr(args, "emit_json", False):
        _print_json(payload)
    else:
        print(format_startup_table(payload))
        print(f"Audit: {audit.resolve()}")
    return 0


def cmd_proxy_boot_trace(args: argparse.Namespace) -> int:
    """Post-login proxy boot trace with delta detection."""
    if (code := exit_code_if_not_windows("proxy-boot-trace")) is not None:
        return code
    result = run_boot_trace_loop(
        duration_seconds=float(args.boot_trace_duration),
        interval_seconds=float(args.boot_trace_interval),
    )
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        print(f"Boot trace complete — {result.get('samples_collected')} samples")
        print(f"Audit: {result.get('audit_path')}")
    return 0


def cmd_proxy_guardian_drift(args: argparse.Namespace) -> int:
    """Dead localhost proxy guardian (dry-run by default)."""
    if (code := exit_code_if_not_windows("proxy-guardian")) is not None:
        return code
    dry_run = bool(getattr(args, "dry_run", True))
    once = bool(getattr(args, "once", True)) and not bool(getattr(args, "guardian_loop", False))
    confirm = str(getattr(args, "confirm_phrase", "") or "")
    interval = float(getattr(args, "interval", 60.0))
    if once:
        result = run_dead_proxy_guardian_once(dry_run=dry_run, confirm=confirm)
    else:
        result = run_dead_proxy_guardian_loop(
            interval_seconds=interval,
            once=False,
            dry_run=dry_run,
            confirm=confirm,
        )
    display = result if once else result.get("last_result", result)
    if getattr(args, "emit_json", False):
        _print_json(display)
    else:
        print(f"Classification: {display.get('classification')}")
        print(f"Action: {display.get('action_taken')} — {display.get('reason')}")
        print("Audit: logs/proxy_guardian.jsonl")
    return 0


def cmd_install_guardian_task(args: argparse.Namespace) -> int:
    """Preview or install WNRT-DeadProxyGuardian scheduled task."""
    if (code := exit_code_if_not_windows("install-guardian-task")) is not None:
        return code
    interval = int(getattr(args, "interval", 60))
    dry_run = bool(getattr(args, "dry_run", True))
    confirm = str(getattr(args, "confirm_phrase", "") or "")
    if dry_run and not confirm:
        result = preview_install_guardian_task(interval=interval)
    else:
        result = install_guardian_task(interval=interval, confirm=confirm, dry_run=dry_run)
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        print(f"Task: {result.get('task_name')}")
        print(f"Command: {result.get('command')}")
        print(f"schtasks: {result.get('schtasks_command')}")
        print(f"Action: {result.get('action_taken', 'preview')} — {result.get('reason', '')}")
        if result.get("confirmation_required"):
            print(f"Confirm with: --confirm {result['confirmation_required']} --dry-run false")
    return 0 if result.get("action_taken") != "failed" else 1


def cmd_uninstall_guardian_task(args: argparse.Namespace) -> int:
    """Preview or remove WNRT-DeadProxyGuardian scheduled task."""
    if (code := exit_code_if_not_windows("uninstall-guardian-task")) is not None:
        return code
    dry_run = bool(getattr(args, "dry_run", True))
    confirm = str(getattr(args, "confirm_phrase", "") or "")
    result = uninstall_guardian_task(confirm=confirm, dry_run=dry_run)
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        print(f"schtasks: {result.get('schtasks_command')}")
        print(f"Action: {result.get('action_taken')} — {result.get('reason')}")
    return 0 if result.get("action_taken") != "failed" else 1


def cmd_proxy_fix(args: argparse.Namespace) -> int:
    """Emergency HKCU WinINET proxy fix (localhost server clear only)."""
    if (code := exit_code_if_not_windows("proxy-fix")) is not None:
        return code
    dry_run = bool(getattr(args, "dry_run", True))
    confirm = str(getattr(args, "confirm_phrase", "") or "")
    clear_pac = bool(getattr(args, "clear_pac", False))
    result = apply_proxy_fix(dry_run=dry_run, confirm=confirm, clear_pac=clear_pac)
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        for line in result.get("planned_changes") or []:
            print(line)
        print(result.get("reason") or "")
    return 0 if result.get("action_allowed") or dry_run else 1


def cmd_safe_search(args: argparse.Namespace) -> int:
    """Timeout-safe targeted file search."""
    result = safe_search(
        query=str(getattr(args, "search_query", "") or ""),
        target=str(getattr(args, "search_target", "project") or "project"),
        repo_root=Path.cwd(),
        max_seconds=float(getattr(args, "search_max_seconds", 20.0)),
        max_files=int(getattr(args, "search_max_files", 3000)),
    )
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        print(f"Scanned {result['scanned_files']} files — {result['match_count']} matches")
        if result.get("timed_out"):
            print("(stopped: timeout or file cap)")
        for row in result.get("matches") or []:
            print(row.get("path"))
    return 0


def cmd_auto_fix_proxy(args: argparse.Namespace) -> int:
    """One-shot dead localhost proxy auto-fix + guardian install."""
    if (code := exit_code_if_not_windows("auto-fix-proxy")) is not None:
        return code
    from src.proxy_drift.auto_fix import run_auto_fix_proxy

    dry_run = bool(getattr(args, "dry_run", False))
    result = run_auto_fix_proxy(
        dry_run=dry_run,
        skip_guardian_install=bool(getattr(args, "skip_guardian_install", False)),
        skip_cursor_fix=bool(getattr(args, "skip_cursor_fix", False)),
        guardian_interval_seconds=int(getattr(args, "guardian_interval", 60)),
        repo_root=Path.cwd(),
    )
    if getattr(args, "emit_json", False):
        _print_json(result)
    else:
        print(f"Outcome: {result.get('outcome')}")
        print(f"Classification: {result.get('classification')} (legacy: {result.get('legacy_classification')})")
        if result.get("outcome") == "healthy":
            print("OK: Proxy path is clean. Restart your browser.")
        elif result.get("outcome") == "still_dead":
            print("WARN: Still dead — try scripts/fix-wininet-proxy.cmd")
        elif dry_run:
            print("Dry-run preview — no registry changes or guardian install.")
    outcome = str(result.get("outcome") or "")
    if outcome == "still_dead":
        return 1
    if outcome == "unsupported":
        return 2
    return 0
