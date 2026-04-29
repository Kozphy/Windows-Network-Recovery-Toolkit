"""Evidence collection using local subprocess calls (Windows). No credential capture."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .schemas import DiagnosticEvidence


def run_command(command: list[str], timeout: float = 25.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def count_in_netstat(keyword: str) -> int:
    code, out = run_command(["netstat", "-an"])
    if code != 0:
        return 0
    return sum(1 for line in out.splitlines() if keyword in line)


def _winhttp_summary() -> str:
    _, winhttp = run_command(["netsh", "winhttp", "show", "proxy"])
    return winhttp.strip()


def _user_proxy_enabled_and_server() -> tuple[bool, str | None]:
    _, winhttp = run_command(["netsh", "winhttp", "show", "proxy"])
    if "Direct access" not in winhttp:
        return True, None

    code, proxy_enable = run_command(
        [
            "reg",
            "query",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            "/v",
            "ProxyEnable",
        ]
    )
    if code == 0 and "0x1" in proxy_enable:
        sv_code, proxy_server = run_command(
            [
                "reg",
                "query",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "/v",
                "ProxyServer",
            ]
        )
        server_val = None
        if sv_code == 0:
            for line in proxy_server.splitlines():
                if "ProxyServer" in line:
                    parts = line.split()
                    if parts:
                        server_val = parts[-1]
        return True, server_val

    for key in ["ProxyServer", "AutoConfigURL"]:
        code, _ = run_command(
            [
                "reg",
                "query",
                r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                "/v",
                key,
            ]
        )
        if code == 0:
            return True, None

    return False, None


def _test_tcp_443() -> bool:
    ps = (
        "try { "
        "$t = Test-NetConnection -ComputerName 'www.google.com' -Port 443 "
        "-WarningAction SilentlyContinue -ErrorAction Stop; "
        "$t.TcpTestSucceeded } catch { $false }"
    )
    code, out = run_command(
        ["powershell", "-NoProfile", "-Command", ps],
        timeout=35.0,
    )
    if code != 0:
        return False
    lines = out.strip().splitlines()
    return "True" in (lines[-1] if lines else "")


def _https_and_tls_hints() -> tuple[bool, bool]:
    """HTTPS HEAD check; TLS/cert hints from stderr patterns only."""
    code, out = run_command(
        ["curl", "-I", "--max-time", "12", "https://www.google.com"],
        timeout=20.0,
    )
    joined = out.lower()
    tls_hint = any(
        x in joined
        for x in (
            "certificate",
            "ssl_connect",
            "tls",
            "cert verify",
            "unable to get local issuer",
            "handshake failure",
        )
    )
    return code == 0, tls_hint


def _firewall_suspicion_heuristic(proxy_summary: str, tcp_ok: bool, https_ok: bool) -> bool:
    """Conservative flag — never implies automatic firewall reset."""
    if tcp_ok and not https_ok:
        return True
    if "blocked" in proxy_summary.lower():
        return True
    return False


def collect_evidence(repo_root: Path | None = None) -> DiagnosticEvidence:
    """Run live checks on Windows. Safe read-only probes only."""
    _ = repo_root  # reserved for future script-relative resolution
    ping_ok = run_command(["ping", "-n", "1", "8.8.8.8"])[0] == 0
    dns_ok = run_command(["nslookup", "google.com"])[0] == 0
    tcp_443_ok = _test_tcp_443()
    https_ok, tls_hint = _https_and_tls_hints()

    proxy_summary = _winhttp_summary()
    user_proxy, server = _user_proxy_enabled_and_server()

    time_wait = count_in_netstat("TIME_WAIT")
    established = count_in_netstat("ESTABLISHED")

    recent: list[str] = []
    _, proc_out = run_command(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process | Sort-Object StartTime -Descending "
            "| Select-Object -First 5 -ExpandProperty ProcessName",
        ],
        timeout=15.0,
    )
    if proc_out.strip():
        recent = [ln.strip() for ln in proc_out.splitlines() if ln.strip()][:5]

    firewall_guess = _firewall_suspicion_heuristic(proxy_summary, tcp_443_ok, https_ok)

    notes_parts: list[str] = []
    if not tcp_443_ok and https_ok:
        notes_parts.append(
            "TCP 443 probe failed while HTTPS probe succeeded; interpret tcp_signal cautiously.",
        )
    evidence = DiagnosticEvidence(
        ping_ok=ping_ok,
        dns_ok=dns_ok,
        tcp_443_ok=tcp_443_ok,
        https_ok=https_ok,
        winhttp_proxy_summary=proxy_summary[:4000],
        user_proxy_enabled=user_proxy,
        user_proxy_server=server,
        tls_cert_issue_detected=tls_hint,
        firewall_blocking_suspected=firewall_guess,
        time_wait_count=time_wait,
        established_count=established,
        recent_processes=recent,
        notes=" ".join(notes_parts),
    )
    return evidence


def load_evidence_from_json(path: Path) -> DiagnosticEvidence:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Fixture root must be a JSON object.")
    return DiagnosticEvidence.from_dict(data)


def evidence_from_mapping(data: dict[str, Any]) -> DiagnosticEvidence:
    return DiagnosticEvidence.from_dict(data)
