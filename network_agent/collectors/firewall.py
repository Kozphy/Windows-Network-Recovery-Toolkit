from __future__ import annotations

"""Firewall profile state collector.

This ingestion module samples firewall profile states to provide context for
security-path hypotheses in the decision engine.

Key invariants:
- Read-only command execution.
- Never triggers firewall reset or policy change.
"""

import subprocess


def _run(command: list[str], timeout: float = 20.0) -> tuple[int, str]:
    """Run a command and return status code with merged textual output.

    Args:
        command: Command sequence to execute.
        timeout: Maximum runtime in seconds.

    Returns:
        tuple[int, str]: Exit code and concatenated stdout/stderr output.

    Raises:
        None. Execution errors are encoded as `(1, message)`.

    Example:
        >>> _run(["netsh", "advfirewall", "show", "allprofiles"])[0] in (0, 1)
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
    """Collect firewall profile activation signals from Windows.

    Input assumptions:
        - `netsh advfirewall` output contains `State ON/OFF` markers.
        - Output language is English-like for `state on` heuristic counting.

    Output guarantees:
        - Returns keys: `firewall_profiles_enabled`, `firewall_output`.
        - `firewall_profiles_enabled` is an integer count >= 0.

    Side effects:
        Read-only command execution; no file writes or firewall changes.

    Idempotency:
        Idempotent unless firewall profile state changes between calls.

    Args:
        None.

    Returns:
        dict[str, object]: Firewall state snapshot for downstream scoring.

    Raises:
        None.

    Example:
        >>> payload = collect()
        >>> "firewall_profiles_enabled" in payload
        True
    """
    _, out = _run(["netsh", "advfirewall", "show", "allprofiles"])
    lowered = out.lower()
    enabled_profiles = lowered.count("state on")
    return {
        "firewall_profiles_enabled": enabled_profiles,
        "firewall_output": out.strip(),
    }
