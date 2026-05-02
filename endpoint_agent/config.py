"""Environment-driven defaults for optional agent HTTP uploads.

Module responsibility:
    Centralizes lookups for ``ENDPOINT_AGENT_API`` and ``ENDPOINT_AGENT_DRY_RUN`` so
    ``endpoint_agent.agent`` can share precedence rules with scripted demos.

Side effects:
    None beyond reading environment variables at call time.

Engineering Notes:
    ``endpoint_agent.agent`` also honors explicit CLI ``--api`` flags—these helpers are
    for modules that intentionally skip argparse.
"""

from __future__ import annotations

import os


def api_base_url() -> str | None:
    """Return ``ENDPOINT_AGENT_API`` when present, stripping trailing slashes.

    Returns:
        Absolute HTTP root such as ``http://127.0.0.1:8000``, or ``None`` when unset.
    """
    v = os.environ.get("ENDPOINT_AGENT_API")
    return v.rstrip("/") if v else None


def dry_run_default() -> bool:
    """Return ``True`` when outbound HTTP should be skipped per environment defaults.

    Returns:
        ``True`` when ``ENDPOINT_AGENT_DRY_RUN`` is unset (defaults to ``\"1\"``) or any
        string not equal to ``\"0\"``. ``False`` only when the variable is exactly ``\"0\"``.

    Engineering Notes:
        Aligns with README guidance: unset means “safe by default” for demo machines.
    """
    return os.environ.get("ENDPOINT_AGENT_DRY_RUN", "1") != "0"
