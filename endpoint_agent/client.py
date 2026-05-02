"""Minimal synchronous HTTP POST helper for syncing agent payloads with ``backend`` FastAPI.

Module responsibility:
    Wraps optional ``httpx`` dependency for JSON POST bodies with tolerant error reporting.

System placement:
    Used by ``endpoint_agent.agent`` when ``base_api`` is configured and dry-run is disabled.

Side effects:
    Performs outbound HTTP only when ``httpx`` imports successfully.

Failure modes:
    Missing dependency, transport errors, and HTTP 4xx/5xx yield dict leaves with ``error`` keys
    rather than raising—callers must inspect responses.
"""

from __future__ import annotations

from typing import Any


def post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """POST JSON to ``base_url + path`` with a structured success or failure dict.

    Args:
        base_url: Scheme/host/port root without trailing slash requirement (normalized internally).
        path: Absolute path beginning with ``/``.
        payload: JSON-serializable mapping posted as request body.

    Returns:
        Parsed JSON object for 2xx responses (empty dict for empty bodies), or an ``{"error": ...}``
        shaped dict—including ``httpx_not_installed``—when prerequisites or transport fail.

    Side effects:
        One HTTP request when ``httpx`` is installed.

    Note:
        Non-JSON success bodies coerce to ``{"raw": ...}``.
    """
    try:
        import httpx
    except ImportError:
        return {"error": "httpx_not_installed"}
    url = base_url.rstrip("/") + path
    try:
        r = httpx.post(url, json=payload, timeout=30.0)
        if r.status_code >= 400:
            return {"error": r.text or "request_failed", "status_code": r.status_code}
        if not r.content:
            return {}
        return dict(r.json()) if isinstance(r.json(), dict) else {"raw": r.json()}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
