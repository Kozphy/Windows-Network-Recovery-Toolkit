"""Read-only local endpoint agent (Phase 2 enterprise hardening).

Collects normalized evidence, appends JSONL spool rows, and reports health/status.
No registry mutation, remediation, or blocked destructive actions.
"""

from windows_network_toolkit.agent.read_only import (
    collect_once,
    get_health_status,
    get_spool_status,
    run_agent_loop,
)

__all__ = [
    "collect_once",
    "get_health_status",
    "get_spool_status",
    "run_agent_loop",
]
