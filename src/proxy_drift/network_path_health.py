"""Detect broken IPv6 with healthy IPv4 (YouTube/browser spin class).

Module responsibility:
    Read-only dual-stack path probes plus a **preview-default** Prefer-IPv4 remediation
    gated by ``PREFER_IPV4_OVER_IPV6`` (registry Prefer IPv4 + disable Wi-Fi IPv6 binding).

System placement:
    ``python -m src network-path-health`` and ``fix-network-path.cmd`` / ``fix-youtube.cmd``.

Key invariants:
    * Dry-run by default; live apply requires typed confirm.
    * Does not claim ISP root cause or malware.
    * Does not re-enable corporate proxies or touch WinINET ProxyEnable.
"""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.logging.audit import append_jsonl

CONFIRM_PREFER_IPV4 = "PREFER_IPV4_OVER_IPV6"
_SCHEMA = "network_path_health.v1"

DEFAULT_PROBES: tuple[tuple[str, str], ...] = (
    ("youtube_204", "https://www.youtube.com/generate_204"),
    ("googlevideo", "https://redirector.googlevideo.com/report_mapping"),
    ("google_204", "https://www.google.com/generate_204"),
)

_LIMITATIONS = [
    "IPv4-ok + IPv6-fail is path observation — not proof of ISP misconfiguration root cause.",
    "Prefer-IPv4 / disabling adapter IPv6 can affect IPv6-only services until reverted.",
    "Browser QUIC may still stall until Edge/Chrome is restarted with QUIC disabled.",
    "Does not modify WinINET ProxyEnable; use proxy-guardian / contain-localhost-rewriter for rewrite.",
]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _curl_code(
    url: str,
    *,
    ip_version: str | None,
    run: Callable[..., Any],
    timeout: float = 10.0,
) -> dict[str, Any]:
    cmd = ["curl.exe", "-s", "-o", "NUL", "-w", "%{http_code}|%{time_total}", "--connect-timeout", "8"]
    if ip_version == "4":
        cmd.append("-4")
    elif ip_version == "6":
        cmd.extend(["-6", "--connect-timeout", "4"])
    cmd.append(url)
    try:
        proc = run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "http_code": 0, "time_s": None, "error": str(exc)}
    raw = (proc.stdout or "").strip()
    code = 0
    time_s: float | None = None
    if "|" in raw:
        left, right = raw.split("|", 1)
        try:
            code = int(left)
        except ValueError:
            code = 0
        try:
            time_s = float(right)
        except ValueError:
            time_s = None
    else:
        try:
            code = int(raw)
        except ValueError:
            code = 0
    ok = 200 <= code < 400 or code == 204
    return {"ok": ok, "http_code": code, "time_s": time_s, "error": None}


def _wifi_ipv6_enabled(run: Callable[..., Any], interface: str = "Wi-Fi") -> bool | None:
    if platform.system() != "Windows":
        return None
    ps = (
        f"$b = Get-NetAdapterBinding -Name '{interface}' -ComponentID ms_tcpip6 "
        "-ErrorAction SilentlyContinue; if ($null -eq $b) { 'MISSING' } "
        "else { [string]$b.Enabled }"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (proc.stdout or "").strip().lower()
    if text == "missing" or not text:
        return None
    return text in {"true", "1"}


def _prefer_ipv4_set(run: Callable[..., Any]) -> bool | None:
    if platform.system() != "Windows":
        return None
    ps = (
        "$p='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters'; "
        "try { [int](Get-ItemProperty $p -Name DisabledComponents -EA Stop).DisabledComponents } "
        "catch { 'NONE' }"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (proc.stdout or "").strip()
    if text == "NONE" or not text:
        return False
    try:
        val = int(text)
    except ValueError:
        return None
    return bool(val & 0x20)


def _proxy_enable(run: Callable[..., Any]) -> int | None:
    if platform.system() != "Windows":
        return None
    ps = (
        "[int](Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings' "
        "-Name ProxyEnable -EA SilentlyContinue).ProxyEnable"
    )
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        return int((proc.stdout or "").strip() or "0")
    except ValueError:
        return None


def assess_network_path(
    *,
    probes: dict[str, dict[str, Any]] | None = None,
    wifi_ipv6_enabled: bool | None = None,
    prefer_ipv4_set: bool | None = None,
    proxy_enable: int | None = None,
    run: Callable[..., Any] | None = None,
    interface: str = "Wi-Fi",
) -> dict[str, Any]:
    """Classify dual-stack path health from injected or live probes."""
    subprocess_run = run if run is not None else subprocess.run
    probe_rows: dict[str, Any] = {}
    if probes is not None:
        probe_rows = probes
    else:
        for name, url in DEFAULT_PROBES:
            probe_rows[name] = {
                "url": url,
                "v4": _curl_code(url, ip_version="4", run=subprocess_run),
                "v6": _curl_code(url, ip_version="6", run=subprocess_run, timeout=6.0),
                "default": _curl_code(url, ip_version=None, run=subprocess_run),
            }

    if wifi_ipv6_enabled is None:
        wifi_ipv6_enabled = _wifi_ipv6_enabled(subprocess_run, interface)
    if prefer_ipv4_set is None:
        prefer_ipv4_set = _prefer_ipv4_set(subprocess_run)
    if proxy_enable is None:
        proxy_enable = _proxy_enable(subprocess_run)

    v4_ok = any(bool((row.get("v4") or {}).get("ok")) for row in probe_rows.values())
    v6_fail = any(
        (row.get("v6") or {}).get("ok") is False and (row.get("v6") or {}).get("http_code") == 0
        for row in probe_rows.values()
    )
    v6_any_ok = any(bool((row.get("v6") or {}).get("ok")) for row in probe_rows.values())
    default_ok = any(bool((row.get("default") or {}).get("ok")) for row in probe_rows.values())

    broken_v6_healthy_v4 = bool(v4_ok and v6_fail and not v6_any_ok)
    mitigated = bool(
        broken_v6_healthy_v4 and prefer_ipv4_set is True and wifi_ipv6_enabled is False and default_ok
    )

    if proxy_enable == 1:
        classification = "PROXY_ENABLED_CHECK_GUARDIAN"
        rationale = "WinINET ProxyEnable=1 — dual-stack path secondary; run proxy-guardian / contain first."
        recommended = "python -m src proxy-guardian --once --hold-direct --json"
    elif not v4_ok and not default_ok:
        classification = "PATH_UNREACHABLE"
        rationale = "IPv4 and default HTTPS probes failed for sample targets."
        recommended = "Check Wi-Fi gateway/DNS (dns-health) and upstream connectivity."
    elif broken_v6_healthy_v4 and mitigated:
        classification = "IPV6_BROKEN_MITIGATED"
        rationale = (
            "IPv6 probes fail while IPv4 works; Prefer-IPv4 and Wi-Fi IPv6-disable already applied; "
            "default path OK."
        )
        recommended = (
            "If browser still spins: fix-youtube.cmd (Edge --disable-quic) after full Edge quit. "
            f"Revert later with confirm {CONFIRM_PREFER_IPV4} docs / fix-network-path.cmd revert."
        )
    elif broken_v6_healthy_v4:
        classification = "IPV6_BROKEN_IPV4_OK"
        rationale = (
            "IPv6 HTTPS probes fail (http_code 0) while IPv4 succeeds — common YouTube/Edge stall pattern."
        )
        recommended = (
            f"Preview/apply Prefer IPv4: python -m src network-path-health "
            f"--confirm {CONFIRM_PREFER_IPV4} --dry-run false --json"
        )
    else:
        classification = "PATH_OK"
        rationale = "Dual-stack or IPv4 default path looks healthy for sample probes."
        recommended = "No Prefer-IPv4 change recommended from this heuristic."

    return {
        "schema_version": _SCHEMA,
        "timestamp_utc": _now(),
        "classification": classification,
        "rationale": rationale,
        "match_broken_ipv6": broken_v6_healthy_v4,
        "mitigated": mitigated,
        "probes": probe_rows,
        "wifi_ipv6_enabled": wifi_ipv6_enabled,
        "prefer_ipv4_set": prefer_ipv4_set,
        "proxy_enable": proxy_enable,
        "interface": interface,
        "recommended_action": recommended,
        "confirmation_required": CONFIRM_PREFER_IPV4,
        "limitations": list(_LIMITATIONS),
    }


def _apply_prefer_ipv4(
    *,
    interface: str,
    run: Callable[..., Any],
) -> dict[str, Any]:
    details: dict[str, Any] = {"steps": [], "errors": []}
    if platform.system() != "Windows":
        details["errors"].append("Prefer-IPv4 apply requires Windows.")
        return details

    ps = f"""
$ErrorActionPreference = 'Continue'
$p = 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip6\\Parameters'
if (-not (Test-Path $p)) {{ New-Item -Path $p -Force | Out-Null }}
New-ItemProperty -Path $p -Name DisabledComponents -PropertyType DWord -Value 0x20 -Force | Out-Null
Write-Output 'SET_PREFER_IPV4'
try {{
  Disable-NetAdapterBinding -Name '{interface}' -ComponentID ms_tcpip6 -ErrorAction Stop
  Write-Output 'DISABLED_WIFI_IPV6'
}} catch {{
  Write-Output ('DISABLE_IPV6_FAIL=' + $_.Exception.Message)
}}
ipconfig /flushdns | Out-Null
Write-Output 'FLUSHED_DNS'
"""
    try:
        proc = run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        details["errors"].append(str(exc))
        return details

    out = proc.stdout or ""
    details["stdout"] = out.strip()
    if "SET_PREFER_IPV4" in out:
        details["steps"].append("DisabledComponents=0x20 (Prefer IPv4)")
    if "DISABLED_WIFI_IPV6" in out:
        details["steps"].append(f"Disabled IPv6 binding on {interface}")
    if "FLUSHED_DNS" in out:
        details["steps"].append("Flushed DNS")
    for line in out.splitlines():
        if line.startswith("DISABLE_IPV6_FAIL="):
            details["errors"].append(line.split("=", 1)[1])
    if proc.returncode not in (0, None) and not details["steps"]:
        details["errors"].append(f"powershell exit {proc.returncode}: {(proc.stderr or '').strip()}")
    return details


def run_network_path_health(
    *,
    dry_run: bool = True,
    confirm: str = "",
    interface: str = "Wi-Fi",
    repo_root: Path | None = None,
    probes: dict[str, dict[str, Any]] | None = None,
    wifi_ipv6_enabled: bool | None = None,
    prefer_ipv4_set: bool | None = None,
    proxy_enable: int | None = None,
    run: Callable[..., Any] | None = None,
    apply_fn: Callable[..., dict[str, Any]] | None = None,
    audit_path: Path | None = None,
) -> dict[str, Any]:
    """Detect dual-stack path issues; optionally apply Prefer-IPv4 mitigation."""
    subprocess_run = run if run is not None else subprocess.run
    root = (repo_root or Path.cwd()).resolve()
    log_path = audit_path or (root / "logs" / "network_path_health.jsonl")

    assessment = assess_network_path(
        probes=probes,
        wifi_ipv6_enabled=wifi_ipv6_enabled,
        prefer_ipv4_set=prefer_ipv4_set,
        proxy_enable=proxy_enable,
        run=subprocess_run,
        interface=interface,
    )
    result: dict[str, Any] = {
        **assessment,
        "dry_run": dry_run,
        "action_taken": "none",
        "reason": assessment.get("rationale") or "",
        "planned_steps": [
            "Set HKLM Tcpip6 DisabledComponents=0x20 (Prefer IPv4 over IPv6)",
            f"Disable IPv6 binding on adapter {interface}",
            "ipconfig /flushdns",
            "Recommend Edge --disable-quic via fix-youtube.cmd if player still spins",
        ],
    }

    needs_apply = assessment["classification"] == "IPV6_BROKEN_IPV4_OK"
    if assessment["classification"] == "IPV6_BROKEN_MITIGATED":
        result["action_taken"] = "none"
        result["reason"] = assessment["rationale"]
        append_jsonl(log_path, {"event": "network_path_health_mitigated", **result})
        return result

    if not needs_apply:
        append_jsonl(log_path, {"event": "network_path_health_idle", **result})
        return result

    if dry_run:
        result["action_taken"] = "preview_only"
        result["reason"] = "Broken IPv6 with healthy IPv4 — dry-run; no registry/adapter changes."
        append_jsonl(log_path, {"event": "network_path_health_preview", **result})
        return result

    if confirm != CONFIRM_PREFER_IPV4:
        result["action_taken"] = "blocked"
        result["reason"] = f"Confirmation required: {CONFIRM_PREFER_IPV4}"
        append_jsonl(log_path, {"event": "network_path_health_blocked", **result})
        return result

    apply = apply_fn if apply_fn is not None else _apply_prefer_ipv4
    # Non-elevated python often cannot write HKLM — apply via elevated script from operator cmd.
    # When called elevated (or with apply_fn), mutate here.
    details = apply(interface=interface, run=subprocess_run)
    result["apply"] = details
    if details.get("errors") and not details.get("steps"):
        result["action_taken"] = "failed"
        result["reason"] = "Prefer-IPv4 apply failed (elevation may be required)."
    else:
        result["action_taken"] = "remediated" if not details.get("errors") else "remediated_with_errors"
        result["reason"] = "Prefer IPv4 mitigation applied."
    append_jsonl(log_path, {"event": "network_path_health_apply", **result})
    return result


def format_human(result: dict[str, Any]) -> str:
    lines = [
        f"Classification: {result.get('classification')}",
        f"Rationale: {result.get('rationale')}",
        f"Action: {result.get('action_taken')} — {result.get('reason')}",
        f"Wi-Fi IPv6 enabled: {result.get('wifi_ipv6_enabled')}",
        f"Prefer IPv4 set: {result.get('prefer_ipv4_set')}",
        f"ProxyEnable: {result.get('proxy_enable')}",
        f"Recommended: {result.get('recommended_action')}",
    ]
    return "\n".join(lines)
