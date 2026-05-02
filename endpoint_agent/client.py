"""HTTP POST helpers for localhost backend (requires httpx)."""

from __future__ import annotations

from typing import Any


def post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """POST JSON; returns dict or {\"error\": ...} on failure."""
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
