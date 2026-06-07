"""Stable agent identity helpers for fleet heartbeats."""

from __future__ import annotations

import hashlib
import platform
import socket
import uuid
from typing import Any

from platform_core.privacy import stable_endpoint_hash


def default_agent_version() -> str:
    return "endpoint-agent/0.2.0"


def derive_endpoint_id(*, hostname: str | None = None, salt: str = "fleet-v1") -> str:
    host = hostname or socket.gethostname()
    return stable_endpoint_hash(f"{host}|{salt}")


def build_heartbeat_identity(
    *,
    endpoint_id: str | None = None,
    hostname: str | None = None,
    os_name: str | None = None,
    agent_version: str | None = None,
) -> dict[str, Any]:
    host = hostname or socket.gethostname()
    eid = endpoint_id or derive_endpoint_id(hostname=host)
    return {
        "endpoint_id": eid,
        "hostname_hash": hashlib.sha256(host.encode("utf-8")).hexdigest()[:16],
        "hostname": host,
        "os_name": os_name or platform.system(),
        "agent_version": agent_version or default_agent_version(),
    }
