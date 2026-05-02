"""Endpoint agent CLI — local diagnostic cycle with optional sync to ``/platform`` HTTP API.

Module responsibility:
    Orchestrates :mod:`endpoint_agent.collect` probes, persists JSONL snapshots/failure events via
    ``platform_core.storage`` (local-first), builds policy previews, and optionally POSTs payloads
    through :mod:`endpoint_agent.client`.

System placement:
    Invoked as ``python -m endpoint_agent``. Complements ``backend/platform_routes.py`` but runs
    standalone without the FastAPI service.

Key invariants:
    * Never launches repair subprocesses from this module—``automatic_repair`` stays ``False``.
    * ``--service`` forwards to :mod:`endpoint_agent.service_runner` loops without altering remediation posture.
    * Dry-run via CLI or ``ENDPOINT_AGENT_DRY_RUN`` suppresses outbound HTTP only; local JSONL
      appends still occur unless refactored externally.

Side effects:
    Appends to ``platform_data/{snapshots,failure_events}.jsonl`` each cycle; HTTP posts when
    ``--api`` / ``ENDPOINT_AGENT_API`` resolves and dry-run is false.

Audit Notes:
    Local JSONL precedes remote ingestion—if API sync fails, operator evidence still exists under
    ``PLATFORM_DATA_DIR``.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from platform_core.policy import build_preview
from platform_core.storage import append_failure_event, append_snapshot, platform_data_dir

from .client import post_json_with_retry
from .collect import collect_endpoint_cycle
from .heartbeat import build_identity


def _skip_http_posts(cli_dry_run: bool) -> bool:
    """Return True when CLI or env flags request no outbound HTTP (local JSONL still written)."""
    if cli_dry_run:
        return True
    return os.environ.get("ENDPOINT_AGENT_DRY_RUN", "").lower() in ("1", "true", "yes")


def api_base(cli_api: str | None) -> str | None:
    """Resolve backend base URL precedence: explicit CLI ``--api`` over ``ENDPOINT_AGENT_API``."""

    if cli_api:
        return cli_api.rstrip("/")
    env = os.environ.get("ENDPOINT_AGENT_API")
    return env.rstrip("/") if env else None


def run_cycle(*, base_api: str | None, skip_http: bool) -> dict[str, object]:
    """Execute one ``collect → JSONL append → policy preview → optional HTTP sync → stdout`` pass.

    Args:
        base_api: Optional ``http://127.0.0.1:8000`` style root; when ``None``, HTTP sync is skipped.
        skip_http: Force-disable POSTs even when ``base_api`` is set (dry-run family).

    Returns:
        Structured status dict including hypotheses, policy preview allowance, and nested ``api_sync``
        responses when HTTP ran.

    Side effects:
        Appends snapshot + failure-event JSONL rows, prints JSON summary, may issue three POSTs.

    Failure modes:
        HTTP failures return error-shaped dict leaves from :func:`~endpoint_agent.client.post_json_with_retry`;
        collectors may emit placeholder failure events when imports/platforms error (handled inside
        :func:`~endpoint_agent.collect.collect_endpoint_cycle`).
    """
    ident = build_identity()
    cycle = collect_endpoint_cycle(ident.endpoint_id)
    append_snapshot(cycle["endpoint_snapshot"])
    append_failure_event(cycle["failure_event"])

    from platform_core.models import FailureEvent

    fe = FailureEvent.model_validate(cycle["failure_event"])
    rec = fe.recommended_action_key or "inspect_proxy"
    preview = build_preview(fe, rec)

    out: dict[str, object] = {
        "endpoint_id": ident.endpoint_id,
        "health": "ok" if not cycle.get("error") else "degraded",
        "top_hypothesis": cycle.get("top_hypothesis"),
        "confidence": cycle.get("confidence"),
        "failure_block_id": cycle.get("failure_block_id"),
        "remediation_recommended": bool(cycle.get("failure_block_id")),
        "policy_allows_preview": preview.allowed_by_policy,
        "automatic_repair": False,
        "data_dir": str(platform_data_dir()),
    }

    sync: dict[str, object] | None = None
    if base_api and not skip_http:
        sync = {
            "heartbeat": post_json_with_retry(base_api, "/platform/ingest/heartbeat", ident.model_dump()),
            "snapshot": post_json_with_retry(base_api, "/platform/ingest/snapshot", cycle["endpoint_snapshot"]),
            "failure_event": post_json_with_retry(base_api, "/platform/ingest/failure-event", cycle["failure_event"]),
        }
        out["api_sync"] = sync

    print(json.dumps(out, indent=2, default=str))
    return out


def main(argv: list[str] | None = None) -> int:
    """Parse CLI flags then run once or loop with ``--interval`` until interrupted.

    Returns:
        Process exit code ``0`` — errors surface inside printed JSON payloads, not nonzero codes.
    """
    p = argparse.ArgumentParser(description="Endpoint reliability agent (no auto-repair).")
    p.add_argument("--once", action="store_true", help="Run single cycle (default if --loop omitted).")
    p.add_argument("--loop", action="store_true", help="Repeat cycles until Ctrl+C.")
    p.add_argument(
        "--service",
        action="store_true",
        help="Service-style heartbeat loop with safe shutdown (uses endpoint_agent/service_runner.py).",
    )
    p.add_argument("--interval", type=float, default=30.0)
    p.add_argument("--api", default=None, help="Backend base URL, e.g. http://127.0.0.1:8000")
    p.add_argument("--dry-run", action="store_true", help="Do not POST to API.")
    ns = p.parse_args(argv)

    if ns.service:
        from endpoint_agent.service_runner import run_service

        os.environ["ENDPOINT_AGENT_INTERVAL"] = str(max(5.0, ns.interval))
        return run_service(cli_api=api_base(ns.api), dry_run_http=ns.dry_run)

    base = api_base(ns.api)
    skip = _skip_http_posts(ns.dry_run)

    if ns.loop:
        while True:
            run_cycle(base_api=base, skip_http=skip)
            time.sleep(max(5.0, ns.interval))
    else:
        run_cycle(base_api=base, skip_http=skip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
