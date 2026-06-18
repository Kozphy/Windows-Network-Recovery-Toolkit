"""Proxy watch facade — read-only drift polling with reverter detection."""

from __future__ import annotations

import platform
import subprocess
import time
from datetime import UTC, datetime
from typing import Any

from windows_network_toolkit.audit_store import append_audit_dict
from windows_network_toolkit.proxy_state import collect_proxy_state_model


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_key(state: dict[str, Any]) -> str:
    return f"{state.get('wininet_proxy_enabled')}:{state.get('wininet_proxy_server')}:{state.get('wininet_auto_config_url')}"


def run_proxy_watch(
    *,
    duration: int = 900,
    interval: float = 2.0,
    inject_sequence: list[dict[str, Any]] | None = None,
    run: Any = None,
) -> dict[str, Any]:
    """Poll proxy state; log changes to .audit/proxy-watch.jsonl."""
    if platform.system() != "Windows" and inject_sequence is None:
        return {
            "unsupported_platform": True,
            "platform": platform.system(),
            "message": "proxy-watch requires Windows or inject_sequence fixture.",
        }

    run_fn = run or subprocess.run
    events: list[dict[str, Any]] = []
    prior: dict[str, Any] | None = None
    start = time.monotonic()
    polls = 0

    def _poll(inject: dict[str, Any] | None = None) -> dict[str, Any]:
        nonlocal prior, polls
        state = collect_proxy_state_model(run=run_fn, inject=inject).to_dict()
        polls += 1
        event: dict[str, Any] = {
            "timestamp_utc": _now(),
            "event": "poll",
            "state": state,
        }
        if prior is not None and _state_key(prior) != _state_key(state):
            elapsed = round(time.monotonic() - start, 1)
            event["event"] = "proxy_change"
            event["old_state"] = prior
            event["new_state"] = state
            event["elapsed_seconds"] = elapsed
            if prior.get("wininet_proxy_enabled") is False and state.get("wininet_proxy_enabled"):
                event["reverter_suspected"] = True
                event["classification_hint"] = "REVERTER_SUSPECTED"
                event["confidence"] = 0.75
            append_audit_dict(event, log_name="proxy-watch.jsonl")
        elif prior is None:
            event["event"] = "initial_poll"
            append_audit_dict(event, log_name="proxy-watch.jsonl")
        events.append(event)
        prior = state
        return event

    if inject_sequence is not None:
        for row in inject_sequence:
            _poll(inject=row)
        return {"polls": polls, "events": events, "duration_seconds": 0}

    deadline = time.monotonic() + duration
    first = _poll()
    while time.monotonic() < deadline:
        time.sleep(interval)
        _poll()

    return {
        "polls": polls,
        "events": events,
        "duration_seconds": duration,
        "initial_poll": first,
    }
