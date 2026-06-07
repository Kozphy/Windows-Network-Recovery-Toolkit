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
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from telemetry.audit import append_registry_writer_evidence_audit
from telemetry.models import RegistryWriteEvent
from telemetry.sysmon_parser import parse_sysmon_registry_event

from .certificate_checker import collect_certificate_indicators
from .persistence_checker import collect_persistence_indicators
from .port_process_attribution import attribute_proxy_port
from .proxy_risk_inference import infer_proxy_risk
from .proxy_signal_collector import collect_proxy_signals
from .reporter import (
    append_audit_event,
    build_report_payload,
    format_json_report,
    format_text_report,
)
from .watch_registry import (
    build_writer_report,
    explain_event,
    format_writer_report_markdown,
    import_procmon_trace,
    load_writer_audit_events,
    watch_writer,
)


def _load_telemetry_events(path: Path | None) -> list[RegistryWriteEvent]:
    if path is None or not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else [raw]
    events: list[RegistryWriteEvent] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "timestamp_utc" in row and "registry_path" in row:
            events.append(RegistryWriteEvent.from_dict(row))
            continue
        parsed = parse_sysmon_registry_event(row)
        if parsed is not None:
            events.append(parsed)
    return events


def _scan_once(
    *,
    append_audit: bool = True,
    telemetry_events_path: Path | None = None,
    proxy_change_time: datetime | None = None,
    append_writer_audit: bool = True,
) -> dict[str, Any]:
    """Run one full diagnostic scan and persist audit evidence.

    Args:
        append_audit: Whether to append the report payload to the JSONL audit ledger.

    Returns:
        dict[str, Any]: Full report payload with raw signals, attribution, and inference.

    Side effects:
        Appends one audit row to ``logs/proxy_hijack_audit.jsonl`` when ``append_audit`` is true.

    Idempotency:
        Not idempotent when audit append is enabled because each call writes a timestamped event.
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
    telemetry_events = _load_telemetry_events(telemetry_events_path)
    payload = build_report_payload(
        raw_signals=proxy,
        attribution=attribution,
        persistence=persistence,
        certificates=certificates,
        risk=risk,
        telemetry_events=telemetry_events or None,
        proxy_change_time=proxy_change_time,
    )
    if append_writer_audit and payload.get("registry_writer_evidence"):
        append_registry_writer_evidence_audit(
            payload["registry_writer_evidence"],
            proxy_change_time=proxy_change_time,
        )
    if append_audit:
        append_audit_event(payload)
    return payload


def _watch(interval_seconds: float) -> int:
    """Continuously poll proxy posture and emit lightweight change events.

    Args:
        interval_seconds: Polling interval in seconds (minimum 1 second enforced).

    Returns:
        int: Never returns under normal operation; loop is continuous.

    Side effects:
        Polls WinINET proxy state and runs full audited scans when the proxy tuple changes.
    """
    last_key = None
    while True:
        raw = collect_proxy_signals()
        key = (
            raw.get("proxy_enable"),
            raw.get("proxy_server"),
            raw.get("auto_config_url"),
        )
        if key != last_key:
            payload = _scan_once(append_audit=True)
            raw = payload.get("raw_signals") or raw
            event_name = (
                "proxy_registry_snapshot" if last_key is None else "proxy_registry_change_detected"
            )
            print(
                json.dumps(
                    {
                        "timestamp": payload.get("timestamp"),
                        "event": event_name,
                        "proxy_enable": raw.get("proxy_enable"),
                        "proxy_server": raw.get("proxy_server"),
                        "auto_config_url": raw.get("auto_config_url"),
                        "classification": (payload.get("inference") or {}).get("classification"),
                        "risk_score": (payload.get("inference") or {}).get("risk_score"),
                        "confidence": (payload.get("inference") or {}).get("confidence"),
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
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(prog="proxy_guard")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="Collect signals, infer risk, append audit, print text report.")
    s.add_argument(
        "--telemetry-events",
        default=None,
        help="Optional Sysmon/EventLog fixture JSON for registry writer fusion.",
    )
    s.add_argument(
        "--proxy-change-time",
        default=None,
        help="Optional ISO-8601 UTC timestamp for telemetry fusion window anchor.",
    )
    s.set_defaults(func="scan")

    r = sub.add_parser("report", help="Collect signals and print report.")
    r.add_argument("--json", dest="emit_json", action="store_true", help="Print JSON report.")
    r.add_argument(
        "--telemetry-events",
        default=None,
        help="Optional Sysmon/EventLog fixture JSON for registry writer fusion.",
    )
    r.add_argument(
        "--proxy-change-time",
        default=None,
        help="Optional ISO-8601 UTC timestamp for telemetry fusion window anchor.",
    )
    r.set_defaults(func="report")

    w = sub.add_parser("watch", help="Poll proxy posture and emit change events.")
    w.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds.")
    w.set_defaults(func="watch")

    ww = sub.add_parser(
        "watch-writer", help="Watch WinINET proxy changes and attribute registry writer evidence."
    )
    ww.add_argument("--interval", type=float, default=5.0, help="Polling interval seconds.")
    ww.add_argument(
        "--since-seconds", type=int, default=120, help="Telemetry look-back window around a change."
    )
    ww.add_argument(
        "--procmon-csv", default=None, help="Optional Procmon CSV export to correlate with changes."
    )
    ww.add_argument("--audit-path", default=None, help="Optional proxy writer audit JSONL path.")
    ww.add_argument(
        "--once",
        action="store_true",
        help="Capture and print one observed-state snapshot without appending.",
    )
    ww.set_defaults(func="watch_writer")

    wr = sub.add_parser("writer-report", help="Read proxy writer audit JSONL and print a report.")
    wr.add_argument(
        "--json", dest="emit_json", action="store_true", help="Print machine-readable JSON."
    )
    wr.add_argument(
        "--markdown", dest="emit_markdown", action="store_true", help="Print Markdown report."
    )
    wr.add_argument("--audit-path", default=None, help="Optional proxy writer audit JSONL path.")
    wr.set_defaults(func="writer_report")

    ip = sub.add_parser(
        "import-procmon", help="Import a Procmon CSV export as writer-proof evidence."
    )
    ip.add_argument("path", help="Path to Procmon CSV export.")
    ip.add_argument("--audit-path", default=None, help="Optional proxy writer audit JSONL path.")
    ip.set_defaults(func="import_procmon")

    ee = sub.add_parser(
        "explain-event", help="Explain one proxy writer attribution event by event_id."
    )
    ee.add_argument("event_id", help="Event id from logs/proxy_writer_audit.jsonl.")
    ee.add_argument("--audit-path", default=None, help="Optional proxy writer audit JSONL path.")
    ee.set_defaults(func="explain_event")

    wr2 = sub.add_parser(
        "watch-report",
        help="Human-readable report for reports/proxy_guard_watch.jsonl.",
    )
    wr2.add_argument("--tail", type=int, default=10, help="Last N events (default 10).")
    wr2.add_argument("--json", dest="emit_json", action="store_true", help="Print raw JSON.")
    wr2.set_defaults(func="watch_report")

    args = parser.parse_args(argv)
    telemetry_path = (
        Path(args.telemetry_events) if getattr(args, "telemetry_events", None) else None
    )
    change_time = None
    if getattr(args, "proxy_change_time", None):
        change_time = datetime.fromisoformat(str(args.proxy_change_time).replace("Z", "+00:00"))
    if args.func in {"scan", "report"}:
        payload = _scan_once(
            append_audit=True,
            telemetry_events_path=telemetry_path,
            proxy_change_time=change_time,
        )
        if getattr(args, "emit_json", False):
            print(format_json_report(payload))
        else:
            print(format_text_report(payload))
        return 0
    if args.func == "watch":
        return _watch(args.interval)
    if args.func == "watch_writer":
        return watch_writer(
            interval_seconds=args.interval,
            audit_path=Path(args.audit_path) if args.audit_path else None,
            since_seconds=args.since_seconds,
            procmon_csv_path=args.procmon_csv,
            once=args.once,
        )
    if args.func == "writer_report":
        audit_path = Path(args.audit_path) if args.audit_path else None
        events = load_writer_audit_events(audit_path)
        report = build_writer_report(events, audit_path=audit_path)
        if getattr(args, "emit_json", False):
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(format_writer_report_markdown(report))
        return 0
    if args.func == "import_procmon":
        payload = import_procmon_trace(
            args.path, audit_path=Path(args.audit_path) if args.audit_path else None
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    if args.func == "explain_event":
        print(
            explain_event(
                args.event_id, audit_path=Path(args.audit_path) if args.audit_path else None
            )
        )
        return 0
    if args.func == "watch_report":
        repo = Path(__file__).resolve().parent.parent
        from src.proxy_guard.audit import default_audit_paths
        from src.proxy_guard.human_report import format_watch_report, load_watch_jsonl

        watch_path = default_audit_paths(repo)["watch"]
        tail_n = max(1, int(getattr(args, "tail", 10)))
        all_rows = load_watch_jsonl(watch_path, tail_n=10**9)
        tail = all_rows[-tail_n:]
        if getattr(args, "emit_json", False):
            print(
                json.dumps(
                    {"path": str(watch_path), "rows_total": len(all_rows), "events": tail},
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(format_watch_report(tail, path=watch_path, total_rows=len(all_rows)))
        return 0
    return 2
