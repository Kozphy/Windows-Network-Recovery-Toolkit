"""Proxy Guard public surface — primarily ``parse_proxy_server`` for deterministic proxy maps.

Prefer importing richer modules (``registry``, ``owner``, ``watcher``) from call sites that orchestrate probes.
"""

from .parser import parse_proxy_server

__all__ = ["parse_proxy_server"]
