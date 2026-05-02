"""Local endpoint collector for the optional Endpoint Reliability Platform prototype.

Module responsibility:
    Surfaces ``endpoint_agent.agent`` as the primary entry when operators run
    ``python -m endpoint_agent`` — a loop that gathers Failure Knowledge System
    probes, persists sanitized rows under ``PLATFORM_DATA_DIR``, evaluates policy previews,
    and optionally POSTs JSON to a localhost FastAPI base URL.

System placement:
    Sits beside ``failure_system`` (signals) and ``platform_core.storage`` (JSONL sinks).
    The beginner ``scripts/*.bat`` toolkit does not import this package.

Key invariants:
    * Automatic repair subprocesses remain disabled in the agent codebase.
    * ``ENDPOINT_AGENT_DRY_RUN`` and CLI ``--dry-run`` suppress HTTP only—local snapshot and
      failure-event JSONL appends inside ``endpoint_agent.agent.run_cycle`` still occur unless
      refactored by callers.

Side effects:
    None at import time; running the CLI appends snapshots/failure-events per cycle.

Audit Notes:
    Correlate appended ``platform_data/*.jsonl`` rows with backend ``GET /platform/*``
    responses when validating demos — network failures surface as structured error leaves
    in cycle output, not as silent drops of local writes.

See Also:
    ``README.md`` platform section and ``docs/endpoint_reliability_platform.md``.
"""
