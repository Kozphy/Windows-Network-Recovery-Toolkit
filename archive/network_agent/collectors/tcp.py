from __future__ import annotations

"""TCP connectivity signal collector for HTTPS transport diagnostics.

This ingestion module probes TCP reachability to port 443 using PowerShell's
`Test-NetConnection`, providing a low-level signal independent of HTTP/TLS.

Key invariants:
- Read-only probing; no network configuration changes.
- Returns normalized keys expected by the decision engine.
"""

import subprocess


def _run(command: list[str], timeout: float = 25.0) -> tuple[int, str]:
    """Run a subprocess command and collect status/output.

    Args:
        command: Command sequence to execute.
        timeout: Timeout in seconds before force termination.

    Returns:
        tuple[int, str]: Process return code and merged stdout/stderr.

    Raises:
        None. Runtime exceptions are folded into `(1, message)`.

    Example:
        >>> _run(["powershell", "-NoProfile", "-Command", "$true"])[0] in (0, 1)
        True
    """
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def collect() -> dict[str, object]:
    """Collect TCP 443 connectivity signal via PowerShell probe.

    Input assumptions:
        - `powershell` executable is available.
        - `Test-NetConnection` may be restricted in locked-down environments.

    Output guarantees:
        - Returns keys: `tcp_443_ok`, `tcp_probe_output`.
        - `tcp_443_ok` is derived from explicit terminal `True` output.

    Side effects:
        Launches a read-only PowerShell command; no file or registry writes.

    Idempotency:
        Idempotent for stable network state; result changes with connectivity.

    Args:
        None.

    Returns:
        dict[str, object]: TCP-layer probe result payload.

    Raises:
        None.

    Example:
        >>> "tcp_443_ok" in collect()
        True
    """
    ps = (
        "try { "
        "$t = Test-NetConnection -ComputerName 'www.google.com' -Port 443 "
        "-WarningAction SilentlyContinue -ErrorAction Stop; "
        "$t.TcpTestSucceeded } catch { $false }"
    )
    code, out = _run(["powershell", "-NoProfile", "-Command", ps], timeout=35.0)
    lines = out.strip().splitlines()
    tcp_443_ok = code == 0 and bool(lines) and "true" in lines[-1].lower()
    return {"tcp_443_ok": tcp_443_ok, "tcp_probe_output": out.strip()}
