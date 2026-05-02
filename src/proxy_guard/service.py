"""Proxy Guard service loop — orchestration only; policy and pure logic live elsewhere."""

from __future__ import annotations

import copy
import json
import sys
import time
from typing import Any

from ..core.jsonl import append_jsonl
from .config import ProxyGuardServiceConfig
from .events import proxy_guard_control_event
from .owner import attribution_payload
from .parser import parse_proxy_server
from .planning import listen_port_for_attribution, normalize_registry_view, registry_views_equal
from .policy import PolicyDecision, ProxyGuardPolicy
from .probes import read_proxy_registry_with_retries
from .rollback import execute_low_risk_proxy_rollback
from .rollback_limits import RollbackLimiter
from .structured_log import emit_structured_log

_LOGGER = "proxy_guard.service"


def _safe_attribution(
    port: int | None,
    *,
    run: Any,
    structured_log_path: Any,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Resolve port ownership; never raises — failures become empty owners + notes."""
    if port is None:
        return (
            {
                "port": None,
                "owners": [],
                "notes": ["no_listen_port_for_attribution"],
            },
            (),
        )
    try:
        return attribution_payload(int(port), run=run), ()
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        emit_structured_log(
            logger=_LOGGER,
            level="WARNING",
            event="attribution_subprocess_failed",
            file_path=structured_log_path,
            extra={"error": str(exc), "port": port},
        )
        return (
            {
                "port": port,
                "owners": [],
                "notes": ["attribution_failure", str(exc)],
            },
            ("attribution_failure",),
        )


def run_proxy_guard_service(cfg: ProxyGuardServiceConfig) -> None:
    """Poll HKCU proxy keys; evaluate policy; optional rollback with rate limits; audit JSONL.

    See :class:`~src.proxy_guard.config.ProxyGuardServiceConfig` for tunables.
    """
    prior: dict[str, Any] | None = None
    registry_change_events = 0
    limiter = RollbackLimiter(cfg.rollback_limits)

    while True:
        t0 = time.perf_counter()
        snap, probe_notes = read_proxy_registry_with_retries(
            run=cfg.run,
            settings=cfg.probe,
        )
        duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)

        emit_structured_log(
            logger=_LOGGER,
            level="INFO" if not probe_notes else "WARNING",
            event="registry_probe_complete",
            file_path=cfg.structured_log_path,
            extra={
                "duration_ms": duration_ms,
                "probe_notes": list(probe_notes),
                "proxy_enable": snap.proxy_enable,
            },
        )

        reg_d = snap.to_dict()
        parsed = parse_proxy_server(snap.proxy_server)
        view = normalize_registry_view(reg_d, parsed.to_dict())

        if prior is None:
            ev = proxy_guard_control_event(
                event_type="initial",
                previous_registry_view={},
                current_registry_view=copy.deepcopy(view),
                attribution={"port": None, "owners": [], "notes": ["initial_snapshot"]},
                policy_source=str(cfg.policy.source_path),
                decision="informational",
                decision_detail="baseline_before_monitoring",
                action="none",
                matched_rule=None,
                primary_process_name=None,
                rollback_detail=None,
                post_rollback_registry_view=None,
                probe_notes=probe_notes if probe_notes else None,
                rollback_suppressed_reason=None,
            )
            append_jsonl(cfg.jsonl_path, ev)
            print(json.dumps(view, indent=2, ensure_ascii=False))
            prior = view
            if cfg.once:
                return
            time.sleep(cfg.interval_seconds)
            continue

        if registry_views_equal(prior, view):
            if cfg.once:
                return
            time.sleep(cfg.interval_seconds)
            continue

        print("[proxy-guard] registry change detected", file=sys.stderr)
        emit_structured_log(
            logger=_LOGGER,
            level="INFO",
            event="registry_change_detected",
            file_path=cfg.structured_log_path,
            extra={"duration_ms": duration_ms},
        )

        previous_registry_view = copy.deepcopy(prior)
        current_registry_view = copy.deepcopy(view)

        port = listen_port_for_attribution(parsed)
        if parsed.is_localhost_proxy and port is not None:
            owners_payload, attr_fail_notes = _safe_attribution(
                port,
                run=cfg.run,
                structured_log_path=cfg.structured_log_path,
            )
            attr_notes = tuple(attr_fail_notes) + tuple(probe_notes)
        else:
            owners_payload = {
                "port": port,
                "owners": [],
                "notes": [
                    "no_localhost_listen_port_for_attribution",
                    *list(probe_notes),
                ],
            }
            attr_notes = tuple(probe_notes)

        owner_rows = list(owners_payload.get("owners") or [])
        pd: PolicyDecision = cfg.policy.evaluate(owner_rows)

        decision_label = "allowed" if pd.allowed else "blocked"
        action = "none"
        rollback_detail: dict[str, Any] | None = None
        post_rollback_view: dict[str, Any] | None = None
        suppressed_reason: str | None = None

        if not pd.allowed and cfg.auto_rollback:
            ok, reason = limiter.evaluate()
            if not ok:
                action = "suppressed"
                suppressed_reason = reason
                emit_structured_log(
                    logger=_LOGGER,
                    level="WARNING",
                    event="rollback_suppressed",
                    file_path=cfg.structured_log_path,
                    extra={"reason": reason},
                )
                prior = view
            else:
                action = "rollback"
                target_reg = {k: reg_d[k] for k in ("proxy_enable", "proxy_server", "auto_config_url", "auto_detect") if k in reg_d}
                rollback_detail = execute_low_risk_proxy_rollback(
                    dry_run=cfg.dry_run_rollback,
                    clear_proxy_server_value=True,
                    reset_winhttp=True,
                    run=cfg.run,
                    current_wininet_reg=target_reg,
                    skip_wininet_if_already_cleared=True,
                )
                limiter.record_rollback()
                snap_after, probe_after = read_proxy_registry_with_retries(
                    run=cfg.run,
                    settings=cfg.probe,
                )
                if probe_after:
                    emit_structured_log(
                        logger=_LOGGER,
                        level="WARNING",
                        event="registry_post_rollback_probe_notes",
                        file_path=cfg.structured_log_path,
                        extra={"notes": list(probe_after)},
                    )
                reg_after = snap_after.to_dict()
                parsed_after = parse_proxy_server(snap_after.proxy_server)
                post_rollback_view = normalize_registry_view(reg_after, parsed_after.to_dict())
                prior = post_rollback_view
        else:
            prior = view

        ev = proxy_guard_control_event(
            event_type="registry_change",
            previous_registry_view=previous_registry_view,
            current_registry_view=current_registry_view,
            attribution=owners_payload,
            policy_source=str(cfg.policy.source_path),
            decision=decision_label,
            decision_detail=pd.reason,
            action=action,
            matched_rule=pd.matched_rule,
            primary_process_name=pd.primary_process_name,
            rollback_detail=rollback_detail,
            post_rollback_registry_view=post_rollback_view,
            probe_notes=attr_notes if attr_notes else None,
            rollback_suppressed_reason=suppressed_reason,
        )
        append_jsonl(cfg.jsonl_path, ev)
        registry_change_events += 1
        print(
            json.dumps(
                {
                    "decision": decision_label,
                    "action": action,
                    "detail": pd.reason,
                    "rollback_suppressed_reason": suppressed_reason,
                },
                indent=2,
                ensure_ascii=False,
            ),
        )

        if cfg.exit_after_registry_change_events is not None:
            if registry_change_events >= cfg.exit_after_registry_change_events:
                return

        if cfg.once:
            return
        time.sleep(cfg.interval_seconds)


def run_proxy_guard_from_legacy(
    *,
    interval: float,
    once: bool,
    auto_rollback: bool,
    policy: ProxyGuardPolicy,
    jsonl_path: Any,
    dry_run_rollback: bool,
    run: Any,
    exit_after_registry_change_events: int | None = None,
) -> None:
    """Adapter for tests and older call sites (maps to :class:`ProxyGuardServiceConfig`)."""
    from .config import legacy_control_kwargs_to_config

    cfg = legacy_control_kwargs_to_config(
        interval=interval,
        once=once,
        auto_rollback=auto_rollback,
        policy=policy,
        jsonl_path=jsonl_path,
        dry_run_rollback=dry_run_rollback,
        run=run,
        exit_after_registry_change_events=exit_after_registry_change_events,
    )
    run_proxy_guard_service(cfg)
