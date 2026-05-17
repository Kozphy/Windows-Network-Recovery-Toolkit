"""Human-readable formatters for proxy guard watch / change audit JSONL rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_watch_jsonl(path: Path, *, tail_n: int = 10) -> list[dict[str, Any]]:
    """Load the last *tail_n* JSON objects from a watch JSONL file."""

    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    if tail_n < 1:
        return rows
    return rows[-tail_n:]


def _proxy_on_label(value: Any) -> str:
    if value is None:
        return "unknown"
    try:
        return "ON" if int(value) == 1 else "OFF"
    except (TypeError, ValueError):
        return str(value)


def _headline_for_transition(before: dict[str, Any], after: dict[str, Any]) -> str:
    be = before.get("proxy_enable")
    ae = after.get("proxy_enable")
    bs = before.get("proxy_server")
    asrv = after.get("proxy_server")
    if be == 0 and ae == 1:
        return "Proxy turned ON — browser and app traffic may be redirected"
    if be == 1 and ae == 0:
        return "Proxy turned OFF — direct access restored (if nothing re-enables it)"
    if bs != asrv:
        return "Proxy server address changed"
    return "Proxy settings changed"


def _recommended_steps(record: dict[str, Any]) -> list[str]:
    before = record.get("before_snapshot") or {}
    after = record.get("after_snapshot") or {}
    ae = after.get("proxy_enable")
    server = after.get("proxy_server") or before.get("proxy_server")
    steps: list[str] = []
    proc = (record.get("attribution") or {}).get("process") or {}
    pname = proc.get("name")
    pid = proc.get("pid")

    if ae == 1:
        steps.append("Run scripts\\reset_proxy.bat as Administrator (clears ProxyEnable and removes ProxyServer).")
        if pname and pid is not None:
            steps.append(
                f"Stop the correlated process: {pname} (PID {pid}) — listener correlation is not registry-writer proof."
            )
        if server and "127.0.0.1" in str(server).lower():
            steps.append("Localhost proxy detected: close dev tools (Node, IDE, VPN) that set system proxy.")
        steps.append("Verify: python -m src proxy-status")
    elif ae == 0:
        steps.append("If browsing works, keep proxy-guard or monitor running to catch re-enable (0 -> 1).")
        if after.get("proxy_server"):
            steps.append("ProxyServer is still set in registry — run scripts\\reset_proxy.bat to delete it.")
    else:
        steps.append("Review before/after snapshots in reports\\proxy_guard_watch.jsonl.")

    steps.append("Human-readable tail: python -m src proxy-watch-report --tail 5")
    return steps


def format_proxy_guard_change(record: dict[str, Any]) -> str:
    """Format one schema v2 ``proxy_guard_change`` (or compatible) audit row."""

    event = str(record.get("event") or "proxy_guard_change")
    ts = record.get("timestamp") or record.get("timestamp_utc") or "unknown"
    before = record.get("before_snapshot") or {}
    after = record.get("after_snapshot") or {}
    attrib = record.get("attribution") or {}
    policy = record.get("policy_decision") or {}
    rollback = record.get("rollback_result") or {}
    proc = attrib.get("process") or {}

    lines = [
        "=" * 72,
        "PROXY GUARD — CHANGE EVENT",
        "=" * 72,
        f"Time (UTC):  {ts}",
        f"Event:       {event}",
        f"Summary:     {_headline_for_transition(before, after)}",
        "",
        "WININET (HKCU) -- before -> after",
        f"  ProxyEnable:  {_proxy_on_label(before.get('proxy_enable'))}  ->  {_proxy_on_label(after.get('proxy_enable'))}",
        f"  ProxyServer:  {before.get('proxy_server') or '(none)'}  ->  {after.get('proxy_server') or '(none)'}",
    ]
    pac_b = before.get("auto_config_url")
    pac_a = after.get("auto_config_url")
    if pac_b or pac_a:
        lines.append(f"  AutoConfigURL:  {pac_b or '(none)'}  ->  {pac_a or '(none)'}")

    lines.extend(
        [
            "",
            "PROCESS (heuristic — does not prove who wrote the registry)",
            f"  Mode:         {attrib.get('mode') or 'unknown'}",
            f"  Confidence:   {attrib.get('confidence') or 'unknown'}",
        ]
    )
    if proc:
        lines.extend(
            [
                f"  Name:         {proc.get('name') or 'unknown'}",
                f"  PID:          {proc.get('pid') if proc.get('pid') is not None else 'unknown'}",
                f"  Parent PID:   {proc.get('ppid') if proc.get('ppid') is not None else 'unknown'}",
                f"  Path:         {proc.get('exe') or '(unavailable)'}",
                f"  Command line: {proc.get('cmdline') or '(unavailable)'}",
            ]
        )
    else:
        lines.append("  (no process correlated)")

    lines.extend(
        [
            "",
            "POLICY",
            f"  Decision:     {policy.get('decision') or 'unknown'}",
            f"  Reason:       {policy.get('reason') or 'unknown'}",
        ]
    )
    if policy.get("matched_rule"):
        lines.append(f"  Matched rule: {policy.get('matched_rule')}")

    rb_status = rollback.get("status")
    if rb_status:
        lines.extend(["", "ROLLBACK", f"  Status:       {rb_status}", f"  Detail:       {rollback.get('detail') or ''}"])

    limitations = attrib.get("limitations") or []
    if limitations:
        lines.append("")
        lines.append("LIMITATIONS")
        for item in limitations:
            lines.append(f"  - {item}")

    lines.append("")
    lines.append("RECOMMENDED NEXT STEPS")
    for step in _recommended_steps(record):
        lines.append(f"  - {step}")

    lines.append("=" * 72)
    return "\n".join(lines)


def format_proxy_state_change_v1(record: dict[str, Any]) -> str:
    """Format legacy monitor_proxy.ps1 ``proxy_state_change`` rows (schema v1)."""

    ts = record.get("timestamp_utc") or record.get("timestamp") or "unknown"
    old_en = record.get("old_enable")
    new_en = record.get("new_enable")
    lines = [
        "=" * 72,
        "PROXY MONITOR — REGISTRY CHANGE",
        "=" * 72,
        f"Time (UTC):     {ts}",
        f"ProxyEnable:    {_proxy_on_label(old_en)}  ->  {_proxy_on_label(new_en)}",
        f"ProxyServer:    {record.get('old_server_masked') or '?'}  ->  {record.get('new_server_masked') or '?'}",
    ]
    procs = record.get("recent_processes")
    if procs:
        lines.append("")
        lines.append("Recent process names (snapshot at change time, not proof of writer):")
        for name in procs:
            lines.append(f"  - {name}")
    lines.append("=" * 72)
    return "\n".join(lines)


def format_watch_record(record: dict[str, Any]) -> str:
    """Dispatch formatter by schema_version / event type."""

    if record.get("event") == "proxy_state_change" or record.get("schema_version") == 1:
        return format_proxy_state_change_v1(record)
    return format_proxy_guard_change(record)


def format_watch_report(
    records: list[dict[str, Any]],
    *,
    path: Path | None = None,
    total_rows: int | None = None,
) -> str:
    """Format multiple watch rows for terminal output."""

    if not records:
        where = str(path) if path else "reports/proxy_guard_watch.jsonl"
        return f"No proxy watch events found in {where}."

    header = [
        "PROXY GUARD WATCH REPORT",
        "-" * 72,
    ]
    if path:
        header.append(f"Source: {path}")
    if total_rows is not None:
        header.append(f"Showing last {len(records)} of {total_rows} event(s)")
    else:
        header.append(f"Showing last {len(records)} event(s)")
    header.append("")

    blocks = ["\n".join(header)]
    for idx, rec in enumerate(records, start=1):
        blocks.append(f"[{idx}/{len(records)}]")
        blocks.append(format_watch_record(rec))
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"
