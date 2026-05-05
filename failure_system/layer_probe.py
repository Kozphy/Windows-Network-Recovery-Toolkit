"""Layer-aware, read-only signal collection for Windows network diagnosis.

Module responsibility:
    Execute cross-layer probe commands and normalize outputs into typed-ish booleans/fields used
    by :mod:`failure_system.layer_decision`.

System placement:
    Called by ``failure_system.layer_decision.run_layer_diagnosis`` as the observation layer.
    Proxy-specific fields are delegated to :mod:`failure_system.proxy_probe`.

Key invariants:
    - Commands run with ``shell=False`` and bounded timeouts.
    - Probe failures degrade gracefully into non-OK rows instead of exceptions.
    - Returned map always includes core booleans consumed by decision rules.

Audit Notes:
    ``raw_probes`` contains truncated command output for operator replay. Treat it as local
    diagnostic evidence and redact before sharing externally.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any

from failure_system.proxy_probe import collect_proxy_signals


def _run(argv: list[str], timeout: float = 30.0) -> tuple[int, str]:
    """Execute one probe command and return merged output.

    Args:
        argv: Argument vector passed to ``subprocess.run``.
        timeout: Maximum execution time in seconds.

    Returns:
        tuple[int, str]: Exit code and merged stdout/stderr text.

    Failure modes:
        OS errors and timeouts return ``(1, str(exc))`` to keep collection resilient.
    """
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, shell=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return int(proc.returncode), (proc.stdout or "") + (proc.stderr or "")


def _ok_from_text(name: str, code: int, out: str) -> bool:
    """Infer semantic probe success from output text.

    Args:
        name: Probe key identifying parser rules.
        code: Raw subprocess exit code.
        out: Merged command output text.

    Returns:
        bool: Semantic pass/fail used by layer decision rules.

    Constraints:
        Text heuristics are intentionally conservative and may vary by locale/tool version.
    """
    lower = out.lower()
    if name == "ping_8_8_8_8":
        return code == 0 and "ttl=" in lower and "reply from" in lower
    if name == "nslookup_google":
        return code == 0 and "address" in lower and "can't find" not in lower
    if name == "tcp_443_google":
        return "tcptestsucceeded" in lower and "true" in lower
    if name in {"curl_google_https", "curl_ms_https"}:
        return code == 0 and "http/" in lower
    return code == 0


def _parse_adapter_down(get_netadapter_out: str) -> bool:
    """Detect adapter-down style indicators from ``Get-NetAdapter`` output."""
    lower = get_netadapter_out.lower()
    if not lower.strip():
        return False
    # Conservative: treat explicit disconnected/down as signal.
    return "disconnected" in lower or re.search(r"\bdown\b", lower) is not None


def _parse_default_gateway(ipconfig_out: str) -> str | None:
    """Extract first IPv4 default gateway from ``ipconfig /all`` text."""
    m = re.search(r"Default Gateway[ .:]*([0-9]{1,3}(?:\.[0-9]{1,3}){3})", ipconfig_out, re.I)
    return m.group(1) if m else None


def _recommended_next_test(signals: dict[str, Any]) -> str:
    """Map coarse layer hints to operator-friendly next tests."""
    if signals.get("layer_hint") == "L1_L2":
        return "Check adapter cable/Wi-Fi state and verify Default Gateway is assigned."
    if signals.get("layer_hint") == "L3":
        return "Ping your Default Gateway and run traceroute to confirm route path."
    if signals.get("layer_hint") == "L4":
        return "Test alternate TCP ports and verify local/edge firewall policy."
    if signals.get("layer_hint") == "L7":
        return "Compare WinINET proxy settings with direct curl and browser behavior."
    if signals.get("layer_hint") == "INFRA":
        return "Validate other devices on same network and check router/ISP status."
    return "Re-run diagnosis and collect additional endpoint evidence over time."


def collect_layer_signals() -> dict[str, Any]:
    """Collect normalized cross-layer signals without mutating system state.

    Returns:
        dict[str, Any]: Signal map including connectivity booleans, adapter/gateway fields,
        proxy fields, raw probe outputs, and a coarse ``layer_hint``.

    Side effects:
        Executes local diagnostic commands (ping/nslookup/powershell/curl/route/ipconfig).

    Idempotency:
        Function is read-only but not value-idempotent in real time; repeated runs may differ as
        network state changes.

    Safe recovery guidance:
        If a command is unavailable (for example older hosts lacking a utility), inspect
        ``raw_probes`` and rerun with alternative tooling before concluding root cause.
    """
    probes: dict[str, dict[str, Any]] = {}
    commands = {
        "ping_8_8_8_8": ["ping", "-n", "2", "8.8.8.8"],
        "nslookup_google": ["nslookup", "google.com"],
        "tcp_443_google": [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Test-NetConnection google.com -Port 443 | Select-Object -ExpandProperty TcpTestSucceeded",
        ],
        "curl_google_https": ["curl", "-I", "https://www.google.com"],
        "curl_ms_https": ["curl", "-I", "https://www.microsoft.com"],
        "route_print": ["route", "print"],
        "ipconfig_all": ["ipconfig", "/all"],
        "get_netadapter": [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "Get-NetAdapter | Format-Table -Auto Name,Status,LinkSpeed,MediaType",
        ],
    }
    for name, argv in commands.items():
        code, out = _run(argv)
        probes[name] = {
            "ok": _ok_from_text(name, code, out),
            "returncode": code,
            "stdout": out[:4000],
        }

    gateway = _parse_default_gateway(probes["ipconfig_all"]["stdout"])
    adapter_down = _parse_adapter_down(probes["get_netadapter"]["stdout"])
    media_disconnected = "media disconnected" in probes["ipconfig_all"]["stdout"].lower()
    proxy = collect_proxy_signals()
    base = {
        "ping_ip_ok": probes["ping_8_8_8_8"]["ok"],
        "nslookup_ok": probes["nslookup_google"]["ok"],
        "tcp_443_ok": probes["tcp_443_google"]["ok"],
        "curl_google_ok": probes["curl_google_https"]["ok"],
        "curl_ms_ok": probes["curl_ms_https"]["ok"],
        "route_print_ok": probes["route_print"]["ok"],
        "ipconfig_ok": probes["ipconfig_all"]["ok"],
        "get_netadapter_ok": probes["get_netadapter"]["ok"],
        "media_disconnected": media_disconnected,
        "adapter_down": adapter_down,
        "default_gateway": gateway,
        "gateway_present": gateway is not None,
        "multi_device_failure_reported": False,
        "intermittent_snapshot": False,
        "raw_probes": probes,
    }
    base.update(proxy)
    # Optional coarse hint for UI/report helpers only; authoritative decision happens downstream.
    base["layer_hint"] = "UNKNOWN"
    if base["media_disconnected"] or base["adapter_down"] or not base["gateway_present"]:
        base["layer_hint"] = "L1_L2"
    elif not base["ping_ip_ok"]:
        base["layer_hint"] = "L3"
    elif base["ping_ip_ok"] and not base["tcp_443_ok"]:
        base["layer_hint"] = "L4"
    elif base["tcp_443_ok"] and (not base["curl_google_ok"] or not base["curl_ms_ok"]):
        base["layer_hint"] = "L7"
    base["recommended_next_test_hint"] = _recommended_next_test(base)
    return base

