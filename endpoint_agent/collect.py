"""One-shot diagnostic ingestion bridging Failure Knowledge System signals into platform models.

Module responsibility:
    Runs read-only probes through ``failure_system`` (when available), evaluates rules, synthesizes a
    :class:`~platform_core.models.FailureEvent`, and emits a sanitized
    :class:`~platform_core.models.EndpointSnapshot`.

System placement:
    Consumed exclusively by ``endpoint_agent.agent``. Does not invoke ``backend`` HTTP directly.

Side effects:
    None on disk inside this module—callers persist returned dict payloads.

Failure modes:
    Missing ``failure_system`` dependencies or unsupported platforms raise internally; callers catch
    and synthesize degraded ``FailureEvent`` rows with ``summary=collector_unavailable:*``.

Data shape:
    Returned dict exposes ``endpoint_snapshot``, ``failure_event``, optional ``failure_block`` dump,
    hypotheses, numeric confidence, and ``error`` string when degraded.
"""

from __future__ import annotations

import uuid
from typing import Any

from platform_core.models import EndpointSnapshot, FailureEvent
from platform_core.privacy import redact_text


def _category_from_rule(rule_id: str) -> str:
    if "dns" in rule_id:
        return "dns"
    if "proxy" in rule_id:
        return "proxy"
    if "https" in rule_id:
        return "tcp_tls"
    return "unknown"


def collect_endpoint_cycle(endpoint_id: str) -> dict[str, Any]:
    """Run one Failure Knowledge System diagnostic pass; never executes repair tooling.

    Args:
        endpoint_id: Stable caller-provided endpoint identifier echoed into models.

    Returns:
        Dict with ``endpoint_snapshot`` / ``failure_event`` dumps plus diagnostic metadata described
        in the module docstring.

    Note:
        Exceptions do not propagate—``except Exception`` synthesizes degraded failure events with
        ``summary=collector_unavailable:*``.

    Side effects:
        Invokes Failure System collectors/rules on supported hosts (potential subprocess/network
        reads per those modules).

    Engineering Notes:
        Recommended action preference is heuristic (``dns`` vs default ``inspect_proxy``); aligns with
        portfolio demos rather than exhaustive policy coverage.
    """
    try:
        from failure_system.collector import collect_diagnostics
        from failure_system.generator import build_failure_block
        from failure_system.rules import RuleEngine

        snap = collect_diagnostics(intermittent_reported=False)
        outcomes = RuleEngine().evaluate(snap)
        block = build_failure_block(snap, outcomes)
        top = outcomes[0] if outcomes else None
        cat = _category_from_rule(top.rule_id if top else "unknown")
        conf = float(top.confidence) if top else 0.0
        summary = redact_text(top.explanation[:500]) if top else "No rule fired."
        event_id = str(uuid.uuid4())
        rec_action = "reset_dns" if cat == "dns" else "inspect_proxy"
        fe = FailureEvent(
            event_id=event_id,
            endpoint_id=endpoint_id,
            failure_block_id=str(block.id),
            severity="medium" if conf > 0.7 else "low",
            category=cat,  # type: ignore[arg-type]
            confidence=conf,
            summary=summary,
            recommended_action_key=rec_action,
        )
        es = EndpointSnapshot(
            endpoint_id=endpoint_id,
            network_state={
                "ping_ip_ok": snap.ping_ip_ok,
                "nslookup_ok": snap.nslookup_ok,
                "curl_https_ok": snap.curl_https_ok,
            },
            proxy_state={
                "winhttp_direct": snap.winhttp_direct,
                "proxy_server_line_present": snap.proxy_server_line_present,
            },
            dns_state={"nslookup_ok": snap.nslookup_ok},
            tcp_state={"curl_https_ok": snap.curl_https_ok},
            browser_path_state={},
            process_clues={},
            raw_data_redacted=True,
        )
        return {
            "endpoint_snapshot": es.model_dump(),
            "failure_event": fe.model_dump(),
            "failure_block": block.model_dump(mode="json"),
            "top_hypothesis": top.cause if top else "unknown",
            "confidence": conf,
            "failure_block_id": str(block.id),
        }
    except Exception as exc:  # noqa: BLE001 — CI / non-Windows
        fe = FailureEvent(
            event_id=str(uuid.uuid4()),
            endpoint_id=endpoint_id,
            severity="low",
            category="unknown",
            confidence=0.0,
            summary=f"collector_unavailable:{type(exc).__name__}",
        )
        es = EndpointSnapshot(endpoint_id=endpoint_id)
        return {
            "endpoint_snapshot": es.model_dump(),
            "failure_event": fe.model_dump(),
            "failure_block": {},
            "top_hypothesis": "unavailable",
            "confidence": 0.0,
            "failure_block_id": "",
            "error": str(exc),
        }
