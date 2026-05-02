"""Blocking service loop coordinating agents, JSONL telemetry, and optional HTTP synchronization.

Module responsibility:
    Mirrors long-running Windows service ergonomics for demos—periodically executes collectors,
    records heartbeats inside ``platform_data/endpoints.jsonl``, emits KPI signals, and forwards
    payloads to FastAPI routes when credentials allow.

System placement:
    Imported through :func:`~endpoint_agent.agent.main` when ``--service`` CLI flag supplied; complements
    one-shot ``run_cycle`` without sharing thread pools.

Key invariants:
    * Runner never invokes ``POST /platform/remediation/*`` nor local repair binaries.
    * Shutdown hooks rely on ``signal.SIGINT`` universally and ``SIGTERM`` where POSIX semantics exist.
    * Sleeping slices into 1s waits so Ctrl+C reacts promptly—does **not** guarantee sub-second teardown on Windows services hosting future wrappers.

Side effects:
    Repeatedly append JSONL artifacts (signals, snapshots, endpoint agent logs) each interval.

Input assumptions:
    Operators configure ``ENDPOINT_AGENT_API``, ``ENDPOINT_AGENT_INTERVAL``, ``ENDPOINT_AGENT_DRY_RUN``, ``ENDPOINT_AGENT_DRY_COLLECTORS`` externally.

Output guarantees:
    Processes exit ``0`` from CLI shim once loop stops—errors captured into JSONL rows rather than nonzero exits.

Failure modes:
    HTTP sync failures annotate ``endpoint_agent_events`` rows but continue looping—inspect ``phase=api_sync_failed``.

Recovery guidance:
    Inspect recent JSONL tails + backend RBAC rejection logs when heartbeats cease—often stale ``X-Operator-*`` roles after policy updates.

Audit Notes:
    Correlate ``append_platform_signal`` KPI counts with dashboard ``GET /platform/metrics`` deltas; divergence implies alternate writers clobbering shared JSONL concurrently.

Engineering Notes:
    Single-threaded asyncio-free design favors clarity over throughput—adequate for single-host demos (<100 endpoints).
"""

from __future__ import annotations

import os
import signal
import threading
from dataclasses import dataclass
from typing import Any

from endpoint_agent.local_events import append_agent_event

from platform_core.models import utc_now_iso
from platform_core.storage import append_platform_signal, append_snapshot, upsert_endpoint

from .collector_abstraction import EndpointCollector, FKSCycleCollector
from .heartbeat import build_identity


@dataclass(slots=True)
class AgentLoopConfig:
    """Frozen runtime tuning structure consumed by :func:`run_service_loop`.

    Attributes:
        interval_seconds: Minimal sleep between loop iterations (seconds, clamped upstream).
        api_base: Optional sanitized FastAPI root (**no** trailing slash semantics enforced downstream).
        skip_http_posts: Mirrors CLI/env dry-run disabling outbound POST bodies.
        agent_version: Semver-ish label embedded into identity payloads.
        dry_run_collectors: Skip Failure Knowledge probes while still emitting heartbeats/signals locally.
    """

    interval_seconds: float
    api_base: str | None
    skip_http_posts: bool
    agent_version: str
    dry_run_collectors: bool


def load_loop_config(cli_api: str | None = None, *, cli_dry_run: bool = False) -> AgentLoopConfig:
    """Hydrate loop configuration overlaying CLI vs environment precedence.

    Args:
        cli_api: Explicit ``--api`` wins over ``ENDPOINT_AGENT_API``.
        cli_dry_run: CLI ``--dry-run`` flag promoting HTTP suppression combined with env truthy tokens.

    Returns:
        Fully populated :class:`AgentLoopConfig`.

    Raises:
        ``ValueError`` if ``ENDPOINT_AGENT_INTERVAL`` contains a non-numeric string.

    Environment variables:
        • ``ENDPOINT_AGENT_INTERVAL`` (seconds)
        • ``ENDPOINT_AGENT_DRY_COLLECTORS``
        • ``ENDPOINT_AGENT_VERSION`` / ``AGENT_VERSION``

    Limitations:
        Ignores fractional intervals below five-second clamp enforced via ``max``—caller CLI duplicates identical clamp prior to invocation for parity.
    """

    def _skip_http(cli_flag: bool) -> bool:
        if cli_flag:
            return True
        return os.environ.get("ENDPOINT_AGENT_DRY_RUN", "").lower() in ("1", "true", "yes")

    def _base() -> str | None:
        if cli_api:
            return cli_api.rstrip("/")
        env = os.environ.get("ENDPOINT_AGENT_API")
        return env.rstrip("/") if env else None

    interval = float(os.environ.get("ENDPOINT_AGENT_INTERVAL", "") or "30")
    interval = max(5.0, interval)
    dry_collect = os.environ.get("ENDPOINT_AGENT_DRY_COLLECTORS", "").lower() in ("1", "true", "yes")
    ver = os.environ.get("ENDPOINT_AGENT_VERSION") or os.environ.get("AGENT_VERSION") or "0.2.0-service"
    return AgentLoopConfig(
        interval_seconds=interval,
        api_base=_base(),
        skip_http_posts=_skip_http(cli_dry_run),
        agent_version=str(ver),
        dry_run_collectors=dry_collect or cli_dry_run,
    )


class _ShutdownCoordinator:
    """Thread-safe cooperative shutdown latch wired to POSIX signals."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request(self, *_args: object) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, seconds: float) -> bool:
        return self._event.wait(timeout=max(0.0, seconds))


def run_service_loop(
    collector: EndpointCollector | None,
    *,
    config: AgentLoopConfig | None = None,
    cfg_override: AgentLoopConfig | None = None,
) -> None:
    """Execute heartbeat/collection cadence until shutdown triggers.

    Never invokes remediation / repair tooling from this runner.

    Appends sanitized local JSONL (`endpoint_agent_events.jsonl`) plus ``platform_signals.jsonl`` KPI rows each cycle.

    Args:
        collector: Optional :class:`~endpoint_agent.collector_abstraction.EndpointCollector`; defaults to :class:`FKSCycleCollector`.
        config: Baseline configuration when ``cfg_override`` absent.
        cfg_override: Hard override used by CLI shim to merge explicit API base.

    Returns:
        ``None`` always—errors recorded into JSONL envelopes.

    Raises:
        Possible ``OSError`` from storage append helpers if disk full (uncaught—propagates to terminate loop).

    Retry behavior:
        HTTP transport errors swallow and annotate per cycle—no exponential backoff by design (demo scope).

    Audit Notes:
        ``phase=shutdown`` marker finalizes JSONL timelines—absence after crash signals killed process without ``finally`` executing.
    """

    cfg = cfg_override or config or load_loop_config()
    coll = collector or FKSCycleCollector()

    coordinator = _ShutdownCoordinator()
    if os.name != "nt":
        try:
            signal.signal(signal.SIGTERM, coordinator.request)
            signal.signal(signal.SIGINT, coordinator.request)
        except ValueError:
            pass
    else:
        try:
            signal.signal(signal.SIGINT, coordinator.request)
        except ValueError:
            pass

    try:
        while not coordinator.is_set():
            cycle: dict[str, Any] | None = None
            ident = build_identity(agent_version=cfg.agent_version)

            heartbeat_payload = ident.model_dump()
            heartbeat_payload["last_seen_at"] = utc_now_iso()
            upsert_endpoint(heartbeat_payload)

            append_platform_signal(
                {
                    "kind": "heartbeat",
                    "endpoint_id": ident.endpoint_id,
                    "collector": getattr(coll, "name", coll.__class__.__name__),
                },
            )

            if cfg.dry_run_collectors:
                append_agent_event(
                    {
                        "phase": "collect_skipped_dry_run",
                        "collector": getattr(coll, "name", ""),
                        "endpoint_id": ident.endpoint_id,
                    },
                )
            elif hasattr(coll, "collect_cycle"):
                cycle = coll.collect_cycle(ident.endpoint_id)
                snap = cycle.get("endpoint_snapshot") if cycle else None
                if isinstance(snap, dict) and snap:
                    append_snapshot(snap)
                append_agent_event(
                    {
                        "phase": "cycle_complete",
                        "endpoint_id": ident.endpoint_id,
                        "collector": getattr(coll, "name", ""),
                        "health": "ok" if not (cycle or {}).get("error") else "degraded",
                        "skipped": (cycle or {}).get("skipped"),
                    },
                )

            append_agent_event(
                {
                    "phase": "heartbeat",
                    "endpoint_id": ident.endpoint_id,
                    "http_suppressed": bool(cfg.skip_http_posts or not cfg.api_base),
                },
            )

            if (
                cfg.api_base
                and not cfg.skip_http_posts
                and not cfg.dry_run_collectors
                and isinstance(cycle, dict)
            ):
                try:
                    from endpoint_agent.client import post_json

                    post_json(cfg.api_base, "/platform/agent/heartbeat", heartbeat_payload)
                    es = cycle.get("endpoint_snapshot")
                    if isinstance(es, dict) and es:
                        post_json(cfg.api_base, "/platform/snapshots", es)
                    fe = cycle.get("failure_event")
                    if isinstance(fe, dict) and fe:
                        post_json(cfg.api_base, "/platform/failure-events/ingest", fe)
                except Exception as exc:  # noqa: BLE001 — service loop survives transport errors
                    append_agent_event(
                        {
                            "phase": "api_sync_failed",
                            "error": type(exc).__name__,
                            "endpoint_id": ident.endpoint_id,
                        },
                    )

            remaining = cfg.interval_seconds
            while remaining > 0 and not coordinator.is_set():
                step = min(1.0, remaining)
                if coordinator.wait(step):
                    break
                remaining -= step
            if coordinator.is_set():
                break
    finally:
        append_agent_event({"phase": "shutdown", "reason": "shutdown_coordinator"})
        append_platform_signal({"kind": "agent_shutdown_notice"})


def run_service(cli_api: str | None = None, *, dry_run_http: bool = False) -> int:
    """Entry point used by ``python -m endpoint_agent --service``.

    Args:
        cli_api: Mirrors CLI ``--api`` string or ``None``.
        dry_run_http: Propagates dry-run suppression for outbound HTTP POST fan-out.

    Returns:
        Literal ``0`` after cooperative shutdown—errors remain inside persisted JSON artifacts.

    Side effects:
        Invokes blocking :func:`run_service_loop` until interrupt.
    """

    cfg = load_loop_config(cli_api=cli_api, cli_dry_run=dry_run_http)
    merged = AgentLoopConfig(
        interval_seconds=cfg.interval_seconds,
        api_base=(cli_api.rstrip("/") if cli_api else cfg.api_base),
        skip_http_posts=cfg.skip_http_posts,
        agent_version=cfg.agent_version,
        dry_run_collectors=cfg.dry_run_collectors,
    )
    run_service_loop(None, cfg_override=merged)
    return 0
