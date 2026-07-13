from __future__ import annotations

"""DNS and basic reachability signal collector.

This module belongs to the ingestion layer of the hybrid agent pipeline. It
samples Windows networking signals needed for DNS-related diagnosis.

Key invariants:
- Uses read-only system commands.
- Never mutates system network configuration.
- Returns normalized keys expected by the decision engine.
"""

import subprocess


def _run(command: list[str], timeout: float = 20.0) -> tuple[int, str]:
    """Execute a command and return status code plus merged output text.

    Args:
        command: Command and arguments passed to `subprocess.run`.
        timeout: Maximum runtime in seconds before command termination.

    Returns:
        tuple[int, str]: Process return code and combined stdout/stderr.

    Raises:
        None. Exceptions are converted into non-zero status with message text.

    Example:
        >>> _run(["ping", "-n", "1", "8.8.8.8"])[0] in (0, 1)
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
    """Collect DNS and ICMP signals for diagnosis.

    Input assumptions:
        - Runs on Windows with `ping` and `nslookup` available in PATH.
        - Network access may be restricted; failures are expected signals.

    Output guarantees:
        - Returns keys: `ping_ip_ok`, `ping_domain_ok`, `nslookup_ok`,
          `dns_lookup_output`.
        - Values are JSON-serializable primitives suitable for reporting.

    Side effects:
        Executes subprocess commands only; no file writes or system mutation.

    Idempotency:
        Function is operationally idempotent but may return different values as
        live network conditions change.

    Args:
        None.

    Returns:
        dict[str, object]: Normalized DNS-related signal snapshot.

    Raises:
        None.

    Example:
        >>> data = collect()
        >>> "nslookup_ok" in data
        True
    """
    ping_ip_code, _ = _run(["ping", "-n", "1", "-w", "2000", "8.8.8.8"])
    ping_domain_code, _ = _run(["ping", "-n", "1", "-w", "3000", "google.com"])
    nslookup_code, nslookup_out = _run(["nslookup", "google.com"])

    return {
        "ping_ip_ok": ping_ip_code == 0,
        "ping_domain_ok": ping_domain_code == 0,
        "nslookup_ok": nslookup_code == 0,
        "dns_lookup_output": nslookup_out.strip(),
    }
