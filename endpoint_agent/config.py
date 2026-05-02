"""Agent runtime flags from environment."""

from __future__ import annotations

import os


def api_base_url() -> str | None:
    """Backend base URL (e.g. http://127.0.0.1:8000) or None."""
    v = os.environ.get("ENDPOINT_AGENT_API")
    return v.rstrip("/") if v else None


def dry_run_default() -> bool:
    return os.environ.get("ENDPOINT_AGENT_DRY_RUN", "1") != "0"
