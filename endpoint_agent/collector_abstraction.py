"""Protocol + default collector binding observe-only diagnostic cycles.

Module responsibility:
    Abstract *how* agent loops obtain ``collect_endpoint_cycle`` payloads so tests can swap fakes
    without editing service runner control flow.

System placement:
    Imported by :mod:`endpoint_agent.service_runner` alongside :mod:`endpoint_agent.collect`.

Key invariants:
    * Implementations must **never** spawn allowlisted repair ``.bat`` files or mutate WinINET keys.
    * ``FKSCycleCollector`` forwards to Failure Knowledge System probes—review that module for network reachability expectations.

Environment flags:
    ``ENDPOINT_AGENT_COLLECT`` when ``0|false|no`` emits synthetic skip rows (``skipped: True``).

Raises:
    Wrapped ``collect_endpoint_cycle`` exceptions surface inside returned dict envelopes per that function’s contract—this module does not translate them.

Side effects:
    None at import time; ``collect_cycle`` may trigger filesystem/network reads per Failure System rules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EndpointCollector(Protocol):
    """Structured interface for building per-cycle diagnostic bundles.

    Attributes:
        name: Human/log label identifying collector implementation for ``platform_signals.jsonl`` rows.

    Methods:
        collect_cycle(endpoint_id: str) -> dict[str, Any]: Mirrors :func:`~endpoint_agent.collect.collect_endpoint_cycle` envelope keys.
    """

    @property
    def name(self) -> str:
        ...

    def collect_cycle(self, endpoint_id: str) -> dict[str, Any]:
        """Return diagnostics payload for one agent iteration.

        Args:
            endpoint_id: Hashed endpoint identifier matching :func:`~endpoint_agent.heartbeat.build_identity`.

        Returns:
            Dict containing at minimum failure/snapshot keys—even when collectors degrade.

        Constraints:
            Repair-related keys should remain absent; contract consumers assume ``automatic_repair=False`` upstream.
        """

        ...


@dataclass
class FKSCycleCollector:
    """Delegated collector using Failure Knowledge probes when env allows.

    Attributes:
        name: Fixed tag written into emitted signal metadata for differentiation in metrics.

    Raises:
        Mirrors underlying ``collect_endpoint_cycle`` swallowed errors as ``error`` string fields (no bare raise here).
    """

    name: str = "failure_system_diag"

    def collect_cycle(self, endpoint_id: str) -> dict[str, Any]:
        from endpoint_agent.collect import collect_endpoint_cycle

        allow = os.environ.get("ENDPOINT_AGENT_COLLECT", "1").lower() not in ("0", "false", "no")
        if not allow:
            return {
                "endpoint_snapshot": {},
                "failure_event": {},
                "error": "collect_disabled_by_env",
                "skipped": True,
            }
        return collect_endpoint_cycle(endpoint_id)
