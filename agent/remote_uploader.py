"""Optional HTTP sync agent for posting local diagnostics to backend API.

This module sits outside the local repair path and is intended for API-backed
monitoring/demo workflows.

Key invariants:
    - Uses read-only local probes before sending payloads.
    - Never executes repair scripts.
    - Request authentication is caller-provided bearer token.
"""

import argparse
import json
import subprocess
import time
from typing import Any

import requests


def run_command(command: list[str]) -> tuple[int, str]:
    """Execute local command and capture merged stdout/stderr text."""
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            timeout=20,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def count_in_netstat(keyword: str) -> int:
    """Count matching netstat lines for a given connection state keyword."""
    code, out = run_command(["netstat", "-an"])
    if code != 0:
        return 0
    return sum(1 for line in out.splitlines() if keyword in line)


def collect_proxy_enabled() -> bool:
    """Infer whether WinHTTP or user proxy settings are active."""
    _, winhttp = run_command(["netsh", "winhttp", "show", "proxy"])
    if "Direct access" not in winhttp:
        return True

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
        return True

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
            return True

    return False


def collect_diagnostics() -> dict[str, Any]:
    """Collect backend-compatible diagnostic payload from local machine.

    Returns:
        dict[str, Any]: Payload aligned with `/diagnose` request schema.
    """
    ping_ok = run_command(["ping", "-n", "1", "8.8.8.8"])[0] == 0
    dns_ok = run_command(["nslookup", "google.com"])[0] == 0
    https_ok = run_command(["curl", "-I", "--max-time", "10", "https://www.google.com"])[0] == 0
    proxy_enabled = collect_proxy_enabled()
    time_wait = count_in_netstat("TIME_WAIT")
    established = count_in_netstat("ESTABLISHED")
    return {
        "ping": ping_ok,
        "dns": dns_ok,
        "https": https_ok,
        "proxy": proxy_enabled,
        "time_wait": time_wait,
        "established": established,
    }


def run_once(base_url: str, token: str, project_id: str | None) -> None:
    """Send one diagnose + monitor cycle to backend API.

    Side effects:
        - Outbound HTTP calls to `/diagnose` and `/monitor`.
        - Console output for operator visibility.

    Args:
        base_url: Backend API base URL.
        token: Bearer JWT token; may be empty for local bypass mode.
        project_id: Optional project scope.

    Raises:
        requests.HTTPError: If API returns non-success status.
        requests.RequestException: On transport/timeout errors.
    """
    payload = collect_diagnostics()
    if project_id:
        payload["project_id"] = project_id
    print("Collected diagnostics:")
    print(json.dumps(payload, indent=2))
    print()

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    diag_resp = requests.post(f"{base_url}/diagnose", json=payload, headers=headers, timeout=20)
    diag_resp.raise_for_status()
    print("Diagnosis result:")
    print(json.dumps(diag_resp.json(), indent=2))
    print()

    monitor_payload = {"time_wait": payload["time_wait"], "established": payload["established"]}
    if project_id:
        monitor_payload["project_id"] = project_id
    mon_resp = requests.post(
        f"{base_url}/monitor",
        json=monitor_payload,
        headers=headers,
        timeout=20,
    )
    mon_resp.raise_for_status()
    print("Monitor result:")
    print(json.dumps(mon_resp.json(), indent=2))


def main() -> None:
    """Parse CLI args and run single-cycle or looping upload mode."""
    parser = argparse.ArgumentParser(description="Windows Network Recovery Toolkit SaaS Agent")
    parser.add_argument("--api", default="http://localhost:8000", help="Base API URL")
    parser.add_argument("--token", default="", help="Supabase access token (JWT)")
    parser.add_argument("--project-id", default="", help="Tenant project ID")
    parser.add_argument("--loop", action="store_true", help="Send data continuously")
    parser.add_argument("--interval", type=int, default=10, help="Loop interval in seconds")
    args = parser.parse_args()

    if not args.token:
        print("Warning: no token provided. API may reject requests unless AUTH_BYPASS_USER_ID is set.")

    if not args.loop:
        run_once(args.api, args.token, args.project_id or None)
        return

    print("Starting loop mode. Press Ctrl+C to stop.")
    while True:
        try:
            run_once(args.api, args.token, args.project_id or None)
        except Exception as exc:  # noqa: BLE001
            print(f"Agent error: {exc}")
        print(f"\nSleeping {args.interval} seconds...\n")
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()
