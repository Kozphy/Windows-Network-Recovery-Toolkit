"""Heartbeat identity synthesis for ``endpoint_agent`` cycles.

Module responsibility:
    Derives :class:`~platform_core.models.EndpointIdentity` rows from local OS facts
    using :func:`~platform_core.privacy.stable_endpoint_hash` so JSONL payloads never
    store raw ``platform.node()`` strings.

System placement:
    Imported by ``endpoint_agent.agent`` ahead of collector runs.

Output guarantees:
    Returned models are JSON-serializable via Pydantic; ``endpoint_id`` is a deterministic
    truncated SHA-256 label for a fixed (hostname, release, hint) triple.

Raises:
    None under normal hosts; hashing uses UTF-8 replace semantics internally.
"""

from __future__ import annotations

import platform as plat

from platform_core.models import EndpointIdentity
from platform_core.privacy import stable_endpoint_hash


def build_identity(agent_version: str = "0.1.0") -> EndpointIdentity:
    """Build a privacy-preserving :class:`~platform_core.models.EndpointIdentity`.

    Args:
        agent_version: Semver-style label embedded in outbound payloads for dashboards.

    Returns:
        Endpoint row where ``endpoint_id`` hashes ``platform.node()`` together with OS
        release metadata—never echoes the hostname verbatim.

    Side effects:
        Reads OS metadata via :mod:`platform` only.
    """
    os_ver = plat.release()
    eid = stable_endpoint_hash(plat.node(), os_ver, None)
    return EndpointIdentity(
        endpoint_id=eid,
        os_family="Windows" if plat.system() == "Windows" else plat.system(),
        os_version=os_ver,
        agent_version=agent_version,
    )
