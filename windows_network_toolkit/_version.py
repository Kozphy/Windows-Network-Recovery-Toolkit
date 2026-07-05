"""Package version resolution — prefers installed distribution metadata."""

from __future__ import annotations

_FALLBACK_VERSION = "0.2.0"
_PACKAGE_NAME = "windows-network-recovery-toolkit"


def resolve_version() -> str:
    """Return ``pyproject.toml`` version when installed; fallback for editable dev trees."""
    try:
        from importlib.metadata import version

        return version(_PACKAGE_NAME)
    except Exception:
        return _FALLBACK_VERSION
