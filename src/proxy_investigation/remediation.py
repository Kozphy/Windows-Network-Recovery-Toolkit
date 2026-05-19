"""Preview-only remediation catalog — no auto-execution."""

from __future__ import annotations

from .models import PolicyOutcome, RemediationPreview


def remediation_previews() -> list[RemediationPreview]:
    return [
        RemediationPreview(
            action_id="disable_wininet_proxy",
            title="Disable WinINET user proxy (preview)",
            policy="PREVIEW",
            detail="Clears ProxyEnable and optional ProxyServer after LKG snapshot; requires DISABLE_WININET_PROXY.",
            command_preview="python -m src proxy disable",
        ),
        RemediationPreview(
            action_id="clear_winhttp_proxy",
            title="Reset WinHTTP proxy to direct (preview)",
            policy="PREVIEW",
            detail="netsh winhttp reset proxy — does not change WinINET user proxy.",
            command_preview="netsh winhttp reset proxy",
        ),
        RemediationPreview(
            action_id="restart_browser",
            title="Restart browser session (manual)",
            policy="ALLOW",
            detail="Close and reopen Edge/Chrome after proxy changes; no automated browser control.",
            command_preview=None,
        ),
        RemediationPreview(
            action_id="isolate_node_environment",
            title="Review Node/npm proxy environment (read-only)",
            policy="ALLOW",
            detail="Inspect npm config and env vars; stop dev proxy manually if unintended.",
            command_preview="npm config get proxy; npm config get https-proxy",
        ),
        RemediationPreview(
            action_id="kill_process",
            title="Kill processes",
            policy="BLOCK",
            detail="Automatic process termination is blocked from this investigation workflow.",
            command_preview=None,
        ),
        RemediationPreview(
            action_id="delete_certificates",
            title="Delete certificates",
            policy="BLOCK",
            detail="Certificate deletion is blocked without forensic workflow.",
            command_preview=None,
        ),
    ]
