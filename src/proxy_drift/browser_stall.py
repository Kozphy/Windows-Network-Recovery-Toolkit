"""Operator-gated Chromium cold-start for IPv6/QUIC browser-spin.

Module responsibility:
    When Prefer-IPv4 is already applied but Edge/Chrome still spins, the running
    browser process ignores ``--disable-quic``. This module **previews** then
    (with ``RESTART_BROWSER_DISABLE_QUIC``) stops Edge/Chrome, clears Edge
    Network Persistent State, flushes DNS, and relaunches with QUIC disabled.

System placement:
    ``python -m src fix-browser-stall`` and ``fix-browser-stall.cmd``.
    Distinct from ``KILL_PROXY_PROCESS`` (still blocked) — this only restarts
    the user browser after typed confirm.

Key invariants:
    * Dry-run / preview default.
    * Does not claim malware or ISP root cause.
    * Does not kill WebView2 (other apps) unless ``include_webview`` is set.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.logging.audit import append_jsonl

CONFIRM_RESTART_BROWSER = "RESTART_BROWSER_DISABLE_QUIC"
_SCHEMA = "browser_stall.v1"

_LIMITATIONS = [
    "Restarting the browser is correlation relief for QUIC/Happy-Eyeballs stall — not proof of root cause.",
    "Does not kill generic proxy processes; KILL_PROXY_PROCESS remains blocked.",
    "Existing Edge windows must be fully quit; attaching a new window to a live process ignores --disable-quic.",
    "Does not modify WinINET ProxyEnable.",
]

_DEFAULT_BROWSERS = ("msedge.exe", "chrome.exe")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _edge_paths() -> list[str]:
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    return [
        str(Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
        str(Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
    ]


def _chrome_paths() -> list[str]:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    local = os.environ.get("LOCALAPPDATA", "")
    paths = [str(Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe")]
    if local:
        paths.append(str(Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    return paths


def _network_persistent_state() -> Path:
    local = os.environ.get("LOCALAPPDATA", "")
    return Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Network Persistent State"


def planned_browser_stall_steps(*, include_webview: bool = False) -> list[str]:
    steps = [
        "Stop msedge.exe (required so --disable-quic is not ignored)",
        "Stop chrome.exe if present",
        "Flush DNS",
        "Delete Edge Network Persistent State (Happy Eyeballs / QUIC cache)",
        "Cold-start Edge with --disable-quic --disable-features=AsyncDns,UseDnsHttpsSvcb,DnsOverHttps",
    ]
    if include_webview:
        steps.insert(2, "Stop msedgewebview2.exe (optional; can affect other apps)")
    return steps


def _apply_browser_stall(
    *,
    run: Callable[..., Any],
    include_webview: bool = False,
    open_url: str = "https://www.youtube.com",
) -> dict[str, Any]:
    details: dict[str, Any] = {"steps": [], "errors": [], "launched": None}
    targets = list(_DEFAULT_BROWSERS)
    if include_webview:
        targets.append("msedgewebview2.exe")
    for name in targets:
        try:
            proc = run(
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if proc.returncode == 0:
                details["steps"].append(f"Stopped {name}")
            else:
                details["steps"].append(f"{name} not running or already stopped")
        except (OSError, subprocess.TimeoutExpired) as exc:
            details["errors"].append(f"taskkill {name}: {exc}")

    try:
        run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=15, check=False)
        details["steps"].append("Flushed DNS")
    except (OSError, subprocess.TimeoutExpired) as exc:
        details["errors"].append(f"flushdns: {exc}")

    state = _network_persistent_state()
    try:
        if state.exists():
            state.unlink()
            details["steps"].append("Cleared Edge Network Persistent State")
        else:
            details["steps"].append("Edge Network Persistent State absent")
    except OSError as exc:
        details["errors"].append(f"clear network state: {exc}")

    edge = next((p for p in _edge_paths() if Path(p).exists()), None)
    chrome = next((p for p in _chrome_paths() if Path(p).exists()), None)
    launcher = edge or chrome
    if not launcher:
        details["errors"].append("Neither Edge nor Chrome executable found.")
        return details
    escaped = launcher.replace("'", "''")
    url = open_url.replace("'", "''")
    ps = (
        f"Start-Process -FilePath '{escaped}' -ArgumentList "
        f"'--disable-quic',"
        f"'--disable-features=AsyncDns,UseDnsHttpsSvcb,DnsOverHttps',"
        f"'--no-first-run','{url}'"
    )
    try:
        run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        details["steps"].append(f"Launched {Path(launcher).name} with --disable-quic")
        details["launched"] = launcher
    except (OSError, subprocess.TimeoutExpired) as exc:
        details["errors"].append(f"start: {exc}")
    return details


def run_browser_stall_fix(
    *,
    dry_run: bool = True,
    confirm: str = "",
    include_webview: bool = False,
    open_url: str = "https://www.youtube.com",
    repo_root: Path | None = None,
    run: Callable[..., Any] | None = None,
    apply_fn: Callable[..., dict[str, Any]] | None = None,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """Preview or apply Chromium cold-start for QUIC/IPv6 browser stall."""
    subprocess_run = run if run is not None else subprocess.run
    root = (repo_root or Path.cwd()).resolve()
    log_path = audit_path or (root / "logs" / "browser_stall.jsonl")
    planned = planned_browser_stall_steps(include_webview=include_webview)
    result: dict[str, Any] = {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "dry_run": dry_run,
        "include_webview": include_webview,
        "open_url": open_url,
        "planned_steps": planned,
        "confirmation_required": CONFIRM_RESTART_BROWSER,
        "action_taken": "none",
        "reason": "",
        "recommended_action": (
            f"Apply: python -m src fix-browser-stall --confirm {CONFIRM_RESTART_BROWSER} "
            "--dry-run false --json"
        ),
        "limitations": list(_LIMITATIONS),
    }

    if dry_run:
        result["action_taken"] = "preview_only"
        result["reason"] = (
            "Browser stall relief is preview-only; running Edge ignores --disable-quic until fully quit."
        )
        append_jsonl(log_path, {"event": "browser_stall_preview", **result})
        return result

    if confirm != CONFIRM_RESTART_BROWSER:
        result["action_taken"] = "blocked"
        result["reason"] = f"Confirmation required: {CONFIRM_RESTART_BROWSER}"
        append_jsonl(log_path, {"event": "browser_stall_blocked", **result})
        return result

    apply = apply_fn if apply_fn is not None else _apply_browser_stall
    details = apply(run=subprocess_run, include_webview=include_webview, open_url=open_url)
    result["apply"] = details
    if details.get("errors") and not details.get("steps"):
        result["action_taken"] = "failed"
        result["reason"] = "Browser stall apply failed."
    else:
        result["action_taken"] = "remediated" if not details.get("errors") else "remediated_with_errors"
        result["reason"] = "Browser cold-started with QUIC disabled."
    append_jsonl(log_path, {"event": "browser_stall_apply", **result})
    return result
