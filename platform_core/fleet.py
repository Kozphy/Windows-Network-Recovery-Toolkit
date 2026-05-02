"""Fleet extension placeholders (no remote control in the local prototype).

Future: signed policy bundles, mTLS agent auth, multi-tenant routing — see
``docs/fleet_architecture.md``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FleetConfigStub:
    """Reserved for future fleet policy sync (content-addressed bundles)."""

    enabled: bool = False
