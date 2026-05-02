"""CLI: one collection cycle or loop; optional POST to localhost; never executes repairs."""

from __future__ import annotations

import argparse
import json
import os
import time

from platform_core.policy import build_preview
from platform_core.storage import append_failure_event, append_snapshot, platform_data_dir

from .client import post_json
from .collect import collect_endpoint_cycle
from .heartbeat import build_identity


def _skip_http_posts(cli_dry_run: bool) -> bool:
    if cli_dry_run:
        return True
    return os.environ.get("ENDPOINT_AGENT_DRY_RUN", "").lower() in ("1", "true", "yes")


def api_base(cli_api: str | None) -> str | None:
    if cli_api:
        return cli_api.rstrip("/")
    env = os.environ.get("ENDPOINT_AGENT_API")
    return env.rstrip("/") if env else None


def run_cycle(*, base_api: str | None, skip_http: bool) -> dict[str, object]:
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
            "heartbeat": post_json(base_api, "/platform/agent/heartbeat", ident.model_dump()),
            "snapshot": post_json(base_api, "/platform/snapshots", cycle["endpoint_snapshot"]),
            "failure_event": post_json(base_api, "/platform/failure-events/ingest", cycle["failure_event"]),
        }
        out["api_sync"] = sync

    print(json.dumps(out, indent=2, default=str))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Endpoint reliability agent (no auto-repair).")
    p.add_argument("--once", action="store_true", help="Run single cycle (default if --loop omitted).")
    p.add_argument("--loop", action="store_true", help="Repeat cycles until Ctrl+C.")
    p.add_argument("--interval", type=float, default=30.0)
    p.add_argument("--api", default=None, help="Backend base URL, e.g. http://127.0.0.1:8000")
    p.add_argument("--dry-run", action="store_true", help="Do not POST to API.")
    ns = p.parse_args(argv)

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
