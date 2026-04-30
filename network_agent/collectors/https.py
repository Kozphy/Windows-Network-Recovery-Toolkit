from __future__ import annotations

"""HTTPS and TLS error signal collector.

This ingestion module runs a lightweight HTTPS HEAD request and extracts
certificate/TLS error fingerprints to separate transport failures from trust
chain or SSL interception issues.

Key invariants:
- No state mutation on host networking.
- Returns stable schema consumed by decision logic.
"""

import subprocess


def _run(command: list[str], timeout: float = 20.0) -> tuple[int, str]:
    """Execute a command and capture combined process output.

    Args:
        command: Command list for `subprocess.run`.
        timeout: Maximum command duration in seconds.

    Returns:
        tuple[int, str]: Return code and merged stdout/stderr text.

    Raises:
        None. Exceptions are transformed into `(1, error_message)`.

    Example:
        >>> _run(["curl", "--version"])[0] in (0, 1)
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
    """Collect HTTPS reachability and certificate anomaly signals.

    Input assumptions:
        - `curl` is available in PATH.
        - HTTPS endpoint accessibility may vary by captive portals/proxies.

    Output guarantees:
        - Returns keys: `https_ok`, `cert_issue_detected`, `https_probe_output`.
        - `cert_issue_detected` uses keyword heuristics over command output.

    Side effects:
        Performs one outbound HTTPS probe; no local persistent writes.

    Idempotency:
        Idempotent for static network conditions but intentionally reflects
        real-time network and TLS state.

    Known failure modes:
        - Non-certificate HTTPS failures can still include TLS-like text.
        - Localized command output language may reduce keyword recall.

    Args:
        None.

    Returns:
        dict[str, object]: HTTPS health and certificate signal payload.

    Raises:
        None.

    Example:
        >>> result = collect()
        >>> isinstance(result["cert_issue_detected"], bool)
        True
    """
    code, out = _run(["curl", "-I", "--max-time", "12", "https://www.google.com"])
    lowered = out.lower()
    cert_issue = any(
        marker in lowered
        for marker in (
            "certificate",
            "ssl_connect",
            "tls",
            "cert verify",
            "unable to get local issuer",
            "handshake failure",
        )
    )
    return {
        "https_ok": code == 0,
        "cert_issue_detected": cert_issue,
        "https_probe_output": out.strip(),
    }
