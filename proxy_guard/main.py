"""CLI orchestration for Proxy Hijack & MITM Risk Detection Engine.

Module responsibility:
    Coordinate collectors, attribution, inference, and reporting into scan/report/watch command
    surfaces for ``python -m proxy_guard``.

System placement:
    Entrypoint layer above collector/inference modules; no scoring logic lives here.

Key invariants:
    - Every scan appends one JSONL audit event.
    - Commands remain diagnostic-only (no auto remediation).
    - Watch mode emits change events based on proxy registry tuple deltas.

Audit Notes:
    If watch output disagrees with audit JSONL, prioritize ``logs/proxy_hijack_audit.jsonl`` as
    authoritative evidence and verify command execution errors in collector limitations.
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from .certificate_checker import collect_certificate_indicators
from .persistence_checker import collect_persistence_indicators
from .port_process_attribution import attribute_proxy_port
from .proxy_risk_inference import infer_proxy_risk
from .proxy_signal_collector import collect_proxy_signals
from .reporter import append_audit_event, build_report_payload, format_json_report, format_text_report


def _scan_once() -> dict[str, Any]:
    """Run one full diagnostic scan and persist audit evidence.

    Returns:
        dict[str, Any]: Full report payload with raw signals, attribution, and inference.

    Side effects:
        Appends one audit row to ``logs/proxy_hijack_audit.jsonl``.

    Idempotency:
        Not idempotent by design because each call writes a new timestamped audit event.
    """
    proxy = collect_proxy_signals()
    parsed = proxy.get("parsed_proxy") or {}
    attribution = attribute_proxy_port(parsed.get("localhost_port"))
    persistence = collect_persistence_indicators()
    certificates = collect_certificate_indicators()
    risk = infer_proxy_risk(
        proxy_signals=proxy,
        attribution=attribution,
        persistence=persistence,
        certificates=certificates,
    )
    payload = build_report_payload(
        raw_signals=proxy,
        attribution=attribution,
        persistence=persistence,
        certificates=certificates,
        risk=risk,
    )
    append_audit_event(payload)
    return payload


def _watch(interval_seconds: float) -> int:
    """Continuously poll proxy posture and emit lightweight change events.

    Args:
        interval_seconds: Polling interval in seconds (minimum 1 second enforced).

    Returns:
        int: Never returns under normal operation; loop is continuous.

    Side effects:
        Repeatedly runs scans (including audit writes) and prints JSON change events to stdout.
    """
    last_key = None
    while True:
        payload = _scan_once()
        raw = payload.get("raw_signals") or {}
        key = (
            raw.get("proxy_enable"),
            raw.get("proxy_server"),
            raw.get("auto_config_url"),
        )
        if key != last_key:
            print(
                json.dumps(
                    {
                        "timestamp": payload.get("timestamp"),
                        "event": "proxy_registry_change_detected",
                        "proxy_enable": raw.get("proxy_enable"),
                        "proxy_server": raw.get("proxy_server"),
                        "classification": (payload.get("inference") or {}).get("classification"),
                    },
                    ensure_ascii=False,
                )
            )
            last_key = key
        time.sleep(max(1.0, float(interval_seconds)))


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and dispatch scan/report/watch workflows.

    Args:
        argv: Optional argv list for tests; defaults to process argv when ``None``.

    Returns:
        int: ``0`` for successful command execution, ``2`` for unsupported dispatch branch.

    Raises:
        ``SystemExit`` may be raised by argparse on invalid CLI usage.
    """
    parser = argparse.ArgumentParser(prog="proxy_guard")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="Collect signals, infer risk, append audit, print text report.")
    s.set_defaults(func="scan")

    r = sub.add_parser("report", help="Collect signals and print report.")
    r.add_argument("--json", dest="emit_json", action="store_true", help="Print JSON report.")
    r.set_defaults(func="report")

    w = sub.add_parser("watch", help="Poll proxy posture and emit change events.")
    w.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds.")
    w.set_defaults(func="watch")

    args = parser.parse_args(argv)
    if args.func in {"scan", "report"}:
        payload = _scan_once()
        if getattr(args, "emit_json", False):
            print(format_json_report(payload))
        else:
            print(format_text_report(payload))
        return 0
    if args.func == "watch":
        return _watch(args.interval)
    return 2

