from __future__ import annotations

"""Proxy configuration signal collector for user and WinHTTP scopes.

This ingestion module reads proxy state from WinHTTP and user registry keys to
support proxy-misconfiguration diagnosis.

Key invariants:
- Read-only command execution (`netsh`, `reg query`).
- No registry mutation.
- Output schema remains stable for decision-engine consumers.
"""

import subprocess


def _run(command: list[str], timeout: float = 15.0) -> tuple[int, str]:
    """Execute a command and return exit status with merged output.

    Args:
        command: Command sequence to execute.
        timeout: Timeout in seconds for subprocess completion.

    Returns:
        tuple[int, str]: Return code and merged stdout/stderr output.

    Raises:
        None. Exceptions are encoded as `(1, error_message)`.

    Example:
        >>> _run(["netsh", "winhttp", "show", "proxy"])[0] in (0, 1)
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
    """Collect proxy-related state from system and user configuration.

    Input assumptions:
        - Windows registry path for Internet Settings exists for current user.
        - Missing keys indicate disabled/unconfigured settings, not fatal error.

    Output guarantees:
        - Returns keys: `winhttp_proxy_enabled`, `user_proxy_enabled`,
          `proxy_enabled`, `winhttp_output`.
        - `proxy_enabled` is logical OR of WinHTTP and user-level findings.

    Side effects:
        Executes read-only shell commands; no persistent writes.

    Idempotency:
        Idempotent for a stable host configuration; changes when registry or
        WinHTTP settings change.

    Args:
        None.

    Returns:
        dict[str, object]: Normalized proxy signal payload for diagnosis.

    Raises:
        None.

    Example:
        >>> data = collect()
        >>> isinstance(data["proxy_enabled"], bool)
        True
    """
    _, winhttp = _run(["netsh", "winhttp", "show", "proxy"])
    winhttp_proxy_enabled = "direct access" not in winhttp.lower()

    key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    code_enable, out_enable = _run(["reg", "query", key, "/v", "ProxyEnable"])
    code_server, _ = _run(["reg", "query", key, "/v", "ProxyServer"])
    code_auto, _ = _run(["reg", "query", key, "/v", "AutoConfigURL"])

    user_proxy_enabled = (
        (code_enable == 0 and "0x1" in out_enable.lower())
        or code_server == 0
        or code_auto == 0
    )

    return {
        "winhttp_proxy_enabled": winhttp_proxy_enabled,
        "user_proxy_enabled": user_proxy_enabled,
        "proxy_enabled": winhttp_proxy_enabled or user_proxy_enabled,
        "winhttp_output": winhttp.strip(),
    }
