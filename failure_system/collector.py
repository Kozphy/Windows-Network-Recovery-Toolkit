"""Safe, read-only Windows network diagnostic collection.

Collectors normalize subprocess output into ``DiagnosticSnapshot`` booleans consumed by
``failure_system.rules.RuleEngine``. **No repair scripts** (``netsh`` resets, ``reg`` edits,
``.bat`` launches) run from this module.

System placement:
    Invoked by ``failure_system.cli.cmd_diagnose``, ``failure_system.api.create_app`` POST
    ``/diagnose``, and tests.

Key invariants:
    - Commands execute with ``shell=False`` and argv lists only.
    - Stdout/stderr merge is truncated to ``_MAX_OUT`` characters per probe.
    - Semantic ``ok`` flags derive from substring heuristics (see ``_ping_public_ip_ok``).

Side effects:
    Spawns local subprocesses that may emit ICMP/DNS/HTTPS traffic and read adapter config.

Audit Notes:
    Captured text may include adapter GUIDs or DHCP identifiers—treat persisted ``FailureBlock``
    payloads as operator-private unless redacted.

Failure modes:
    Missing binaries (``curl`` on older hosts), permission errors, or timeouts map to non-zero
    exit codes and synthetic stderr strings without raising Python exceptions.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Final

from failure_system.models import DiagnosticCommandResult, DiagnosticSnapshot

_MAX_OUT: Final[int] = 12_000


def run_command(command: list[str], timeout: float = 45.0) -> tuple[int, str]:
    """Execute one subprocess and capture merged streams.

    Args:
        command: Argument vector passed to ``subprocess.run`` with ``shell=False``.
        timeout: Seconds before the OS terminates the child process.

    Returns:
        Tuple of ``(exit_code, merged_stdout_stderr_text)`` truncated to ``_MAX_OUT``.

    Raises:
        None; subprocess exceptions convert to ``(1, str(exc))`` for probe stability.
    """
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out[:_MAX_OUT]
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)[:_MAX_OUT]


def _truncate(text: str, limit: int = _MAX_OUT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n...[truncated]"


def _ping_public_ip_ok(stdout: str, exit_code: int) -> bool:
    """Heuristic: Windows ping success shows 'Reply from' and TTL."""
    s = stdout.lower()
    if "reply from" in s and "ttl=" in s:
        return True
    if exit_code == 0 and "bytes=" in s:
        return True
    return False


def _nslookup_ok(stdout: str, exit_code: int) -> bool:
    if exit_code != 0:
        return False
    lower = stdout.lower()
    if "can't find" in lower or "non-existent domain" in lower:
        return False
    return bool(re.search(r"name:\s+", lower)) or "address:" in lower


def _curl_https_ok(stdout: str, exit_code: int) -> bool:
    if exit_code != 0:
        return False
    # curl prints headers/body; HTTP 200 often appears in verbose modes
    lower = stdout.lower()
    if "connection refused" in lower or "timed out" in lower or "could not resolve" in lower:
        return False
    return True


def _parse_winhttp(summary: str) -> tuple[bool, bool]:
    """Return (direct_access, proxy_server_line_present)."""
    lower = summary.lower()
    if "direct access" in lower and "no proxy server" in lower:
        return True, False
    if re.search(r"proxy server\(s\)\s*:\s*\S", lower):
        return False, True
    if "proxy server" in lower:
        return False, True
    return True, False


def collect_diagnostics(intermittent_reported: bool = False) -> DiagnosticSnapshot:
    """Run all bundled probes and assemble a ``DiagnosticSnapshot``.

    Args:
        intermittent_reported: Surfaces operator suspicion of flaky connectivity into both the
            snapshot and downstream rules (no extra probes).

    Returns:
        Normalized booleans plus raw ``DiagnosticCommandResult`` entries keyed by probe name.

    Raises:
        None; failures degrade into failing booleans and captured stderr text.

    Engineering Notes:
        ``ping`` switches between Windows ``-n`` and POSIX ``-c`` flags based on ``sys.platform``.
    """
    raw: dict[str, DiagnosticCommandResult] = {}

    # ICMP — Windows uses -n for count
    ping_cmd = ["ping", "-n", "2", "8.8.8.8"]
    if sys.platform != "win32":
        ping_cmd = ["ping", "-c", "2", "8.8.8.8"]
    code, out = run_command(ping_cmd)
    raw["ping_8_8_8_8"] = DiagnosticCommandResult(
        command=ping_cmd,
        exit_code=code,
        stdout=_truncate(out),
        ok=_ping_public_ip_ok(out, code),
    )

    code, out = run_command(["nslookup", "google.com"])
    raw["nslookup_google_com"] = DiagnosticCommandResult(
        command=["nslookup", "google.com"],
        exit_code=code,
        stdout=_truncate(out),
        ok=_nslookup_ok(out, code),
    )

    code, out = run_command(["curl", "-sS", "-m", "25", "-L", "https://example.com"])
    raw["curl_example_com"] = DiagnosticCommandResult(
        command=["curl", "-sS", "-m", "25", "-L", "https://example.com"],
        exit_code=code,
        stdout=_truncate(out),
        ok=_curl_https_ok(out, code),
    )

    code, out = run_command(["ipconfig", "/all"])
    raw["ipconfig_all"] = DiagnosticCommandResult(
        command=["ipconfig", "/all"],
        exit_code=code,
        stdout=_truncate(out),
        ok=code == 0,
    )

    code, out = run_command(["netsh", "winhttp", "show", "proxy"])
    winhttp_text = _truncate(out)
    direct, proxy_line = _parse_winhttp(winhttp_text)
    raw["netsh_winhttp_show_proxy"] = DiagnosticCommandResult(
        command=["netsh", "winhttp", "show", "proxy"],
        exit_code=code,
        stdout=winhttp_text,
        ok=code == 0,
    )

    code, out = run_command(["route", "print"])
    raw["route_print"] = DiagnosticCommandResult(
        command=["route", "print"],
        exit_code=code,
        stdout=_truncate(out),
        ok=code == 0,
    )

    return DiagnosticSnapshot(
        ping_ip_ok=raw["ping_8_8_8_8"].ok,
        nslookup_ok=raw["nslookup_google_com"].ok,
        curl_https_ok=raw["curl_example_com"].ok,
        winhttp_direct=direct,
        proxy_server_line_present=proxy_line,
        intermittent_reported=intermittent_reported,
        raw=raw,
    )
