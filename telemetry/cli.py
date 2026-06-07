"""CLI for registry writer telemetry parsing and evidence fusion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from telemetry.audit import append_registry_writer_evidence_audit
from telemetry.models import RegistryWriteEvent
from telemetry.registry_writer_fusion import fuse_registry_writer_evidence
from telemetry.sysmon_parser import parse_sysmon_registry_event


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _emit(payload: dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def cmd_parse_sysmon_fixture(args: argparse.Namespace) -> int:
    raw = _load_json(Path(args.path))
    rows = raw if isinstance(raw, list) else [raw]
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        event = parse_sysmon_registry_event(row)
        if event is not None:
            parsed.append(event.to_dict(include_raw=args.include_raw))
    _emit({"events": parsed, "count": len(parsed)}, pretty=args.pretty)
    return 0


def cmd_fuse_registry_writer_evidence(args: argparse.Namespace) -> int:
    events_raw = _load_json(Path(args.events))
    if not isinstance(events_raw, list):
        events_raw = [events_raw]

    events: list[RegistryWriteEvent] = []
    for item in events_raw:
        if isinstance(item, dict) and "timestamp_utc" in item and "registry_path" in item:
            events.append(RegistryWriteEvent.from_dict(item))
            continue
        if isinstance(item, dict):
            parsed = parse_sysmon_registry_event(item)
            if parsed is not None:
                events.append(parsed)

    listener: dict[str, Any] | None = None
    if args.listener:
        listener = _load_json(Path(args.listener))
        if not isinstance(listener, dict):
            listener = None

    proxy_change_time = datetime.fromisoformat(args.proxy_change_time.replace("Z", "+00:00"))
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=proxy_change_time,
        telemetry_events=events,
        listener_attribution=listener,
        window_before_seconds=args.window_before,
        window_after_seconds=args.window_after,
    )
    evidence_dict = evidence.to_dict(include_raw=args.include_raw)
    if args.audit:
        append_registry_writer_evidence_audit(
            evidence,
            proxy_change_time=proxy_change_time,
            include_raw=args.include_raw,
        )
    _emit(evidence_dict, pretty=args.pretty)
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    payload = _load_json(Path(args.path))
    if not isinstance(payload, dict):
        print(json.dumps({"error": "expected evidence JSON object"}, ensure_ascii=False))
        return 2

    if args.pretty:
        lines = [
            "Registry Writer Evidence Summary",
            "--------------------------------",
            f"evidence_level: {payload.get('evidence_level')}",
            f"confidence_rank: {payload.get('confidence_rank')}",
            "",
            "limitations:",
        ]
        for item in payload.get("limitations") or []:
            lines.append(f"- {item}")
        lines.extend(["", "recommended_next_steps:"])
        for item in payload.get("recommended_next_steps") or []:
            lines.append(f"- {item}")
        writers = payload.get("candidate_writers") or []
        if writers:
            lines.extend(["", "candidate_writers:"])
            for writer in writers:
                lines.append(f"- pid={writer.get('process_id')} path={writer.get('process_path')}")
        print("\n".join(lines))
    else:
        summary = {
            "evidence_level": payload.get("evidence_level"),
            "confidence_rank": payload.get("confidence_rank"),
            "matched_event_count": len(payload.get("matched_events") or []),
            "candidate_writer_count": len(payload.get("candidate_writers") or []),
            "limitations": payload.get("limitations") or [],
            "recommended_next_steps": payload.get("recommended_next_steps") or [],
        }
        _emit(summary, pretty=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="telemetry.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse-sysmon-fixture", help="Parse Sysmon fixture JSON into events.")
    p_parse.add_argument("path", help="Path to JSON fixture (object or list).")
    p_parse.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    p_parse.add_argument("--include-raw", action="store_true", help="Include raw_event in output.")
    p_parse.set_defaults(func=cmd_parse_sysmon_fixture)

    p_fuse = sub.add_parser(
        "fuse-registry-writer-evidence", help="Fuse telemetry with listener attribution."
    )
    p_fuse.add_argument(
        "--events", required=True, help="JSON path (raw Sysmon rows or parsed events)."
    )
    p_fuse.add_argument(
        "--proxy-change-time", required=True, help="ISO-8601 UTC proxy change timestamp."
    )
    p_fuse.add_argument("--listener", help="Optional listener attribution JSON path.")
    p_fuse.add_argument("--window-before", type=int, default=120)
    p_fuse.add_argument("--window-after", type=int, default=30)
    p_fuse.add_argument("--pretty", action="store_true")
    p_fuse.add_argument("--include-raw", action="store_true")
    p_fuse.add_argument(
        "--audit", action="store_true", help="Append summary to logs/registry_writer_evidence.jsonl"
    )
    p_fuse.set_defaults(func=cmd_fuse_registry_writer_evidence)

    p_explain = sub.add_parser("explain", help="Summarize fused evidence JSON.")
    p_explain.add_argument("path", help="Evidence JSON path.")
    p_explain.add_argument("--pretty", action="store_true", help="Human-readable summary.")
    p_explain.set_defaults(func=cmd_explain)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
