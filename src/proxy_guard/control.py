"""Compatibility shim for Proxy Guard control — implementation is in :mod:`service`."""

from __future__ import annotations

from .service import run_proxy_guard_from_legacy as run_proxy_guard_control

__all__ = ["run_proxy_guard_control"]
