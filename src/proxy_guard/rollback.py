"""Low-risk, reversible proxy rollback helpers (WinINET HKCU + WinHTTP reset).

Only these surfaces are automated by Proxy Guard; other network stack mutations stay manual.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

from ..repair.executor import RegApplyResult, apply_mutations
from .remediation import build_user_proxy_disable_mutations


def run_netsh_winhttp_reset_proxy(
    *,
    dry_run: bool,
    run: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Run ``netsh winhttp reset proxy`` (idempotent reset of WinHTTP proxy).

    Args:
        dry_run: When True, do not invoke ``netsh``; return a synthetic success row.
        run: ``subprocess.run`` injector for tests.

    Returns:
        JSON-serializable dict with ``argv``, ``returncode``, ``stdout``, ``stderr``.
    """
    argv = ("netsh", "winhttp", "reset", "proxy")
    if dry_run:
        return {
            "argv": list(argv),
            "returncode": 0,
            "stdout": "[dry-run] netsh not executed",
            "stderr": "",
        }
    try:
        proc = run(
            list(argv),
            capture_output=True,
            text=True,
            shell=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "argv": list(argv),
            "returncode": -1,
            "stdout": "",
            "stderr": str(exc),
        }
    return {
        "argv": list(argv),
        "returncode": int(proc.returncode),
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def reg_results_to_audit(rows: tuple[RegApplyResult, ...]) -> list[dict[str, Any]]:
    """Flatten registry apply results for JSONL."""
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "argv": list(r.argv),
                "returncode": r.returncode,
                "stdout": r.stdout,
                "stderr": r.stderr,
            },
        )
    return out


def wininet_user_proxy_already_cleared(reg_dict: dict[str, Any]) -> bool:
    """Return True when WinINET user keys appear already disabled (idempotent no-op target).

    Unknown ``proxy_enable`` (``None``) returns False so callers still attempt remediation
    when registry reads were partial.

    Args:
        reg_dict: Keys like ``registry_proxy_snapshot.to_dict()`` output.

    Returns:
        True only when ``ProxyEnable`` is definitively ``0`` and ``ProxyServer`` is absent/empty.
    """
    if reg_dict.get("proxy_enable") != 0:
        return False
    ps = reg_dict.get("proxy_server")
    return ps is None or str(ps).strip() == ""


def execute_low_risk_proxy_rollback(
    *,
    dry_run: bool,
    clear_proxy_server_value: bool = True,
    reset_winhttp: bool = True,
    run: Callable[..., Any] = subprocess.run,
    current_wininet_reg: dict[str, Any] | None = None,
    skip_wininet_if_already_cleared: bool = True,
) -> dict[str, Any]:
    """Disable HKCU WinINET user proxy and optionally reset WinHTTP proxy.

    Order:
        1. ``reg add`` / ``reg delete`` mutations from :mod:`remediation` (may be skipped).
        2. ``netsh winhttp reset proxy`` when ``reset_winhttp`` is True.

    Idempotency:
        Re-running after a successful rollback yields **no WinINET argv** when
        ``current_wininet_reg`` reflects an already-cleared state (still runs WinHTTP reset
        when enabled — ``netsh winhttp reset proxy`` is safe to repeat).

    Args:
        dry_run: Skip real subprocess I/O (preview only).
        clear_proxy_server_value: Pass through to ``build_user_proxy_disable_mutations``.
        reset_winhttp: When False, skip WinHTTP reset (testing / strict WinINET-only rollback).
        run: ``subprocess.run`` injector.
        current_wininet_reg: Optional HKCU mapping before rollback (for skip optimization).
        skip_wininet_if_already_cleared: When True and state already cleared, omit ``reg.exe``.

    Returns:
        Structured audit blob suitable for ``rollback_detail`` in control-plane JSONL.
    """
    wininet_audit: list[dict[str, Any]]
    skipped = False
    if (
        skip_wininet_if_already_cleared
        and current_wininet_reg is not None
        and wininet_user_proxy_already_cleared(current_wininet_reg)
    ):
        wininet_audit = []
        skipped = True
    else:
        mutations, _ = build_user_proxy_disable_mutations(clear_proxy_server_value=clear_proxy_server_value)
        reg_results = apply_mutations(mutations, dry_run=dry_run)
        wininet_audit = reg_results_to_audit(reg_results)

    winhttp: dict[str, Any] | None = None
    if reset_winhttp:
        winhttp = run_netsh_winhttp_reset_proxy(dry_run=dry_run, run=run)
    out: dict[str, Any] = {
        "wininet_reg": wininet_audit,
        "winhttp_reset": winhttp,
        "wininet_skipped_already_cleared": skipped,
    }
    return out
