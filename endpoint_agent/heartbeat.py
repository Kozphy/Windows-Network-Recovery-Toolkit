"""Build sanitized EndpointIdentity payload."""

from __future__ import annotations

import platform as plat

from platform_core.models import EndpointIdentity
from platform_core.privacy import stable_endpoint_hash


def build_identity(agent_version: str = "0.1.0") -> EndpointIdentity:
    """Create identity using hashed endpoint id (hostname only participates in hash)."""
    os_ver = plat.release()
    eid = stable_endpoint_hash(plat.node(), os_ver, None)
    return EndpointIdentity(
        endpoint_id=eid,
        os_family="Windows" if plat.system() == "Windows" else plat.system(),
        os_version=os_ver,
        agent_version=agent_version,
    )
