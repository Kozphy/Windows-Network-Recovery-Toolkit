"""Watcher, reports, and explainers for proxy writer attribution.

All live operations are read-only except append-only JSONL writes under ``logs/``. No
processes are killed, no certificates are deleted, and no network settings are changed.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evidence.registry_writer import collect_registry_writer_evidence, parse_procmon_csv

from .attribution import (
    ProxyAttributionEvent,
    build_proxy_attribution_event,
    candidate_listeners_from_attribution,
    proxy_tuple_from_signals,
    utc_now_iso,
)
from .certificate_checker import collect_certificate_indicators
from .persistence_checker import collect_persistence_indicators
from .port_process_attribution import attribute_proxy_port
from .proxy_signal_collector import collect_proxy_signals, parse_proxy_server


def default_writer_audit_path() -> Path:
    """Return the canonical append-only writer attribution audit path."""

    return Path(__file__).resolve().parent.parent / "logs" / "proxy_writer_audit.jsonl"


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as one UTF-8 line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_proxy_writer_event(event: ProxyAttributionEvent, *, audit_path: Path | None = None) -> Path:
    """Append a proxy writer attribution event and return the written path."""

    path = audit_path or default_writer_audit_path()
    append_jsonl(path, event.to_jsonable())
    return path


def _probe(
    name: str,
    argv: list[str],
    *,
    run: Callable[..., Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Run one bounded read-only connectivity probe."""

    try:
        proc = run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {"name": name, "ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}
    except OSError as exc:
        return {"name": name, "ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}

    return {
        "name": name,
        "ok": int(getattr(proc, "returncode", 1)) == 0,
        "returncode": int(getattr(proc, "returncode", 1)),
        "stdout": (getattr(proc, "stdout", "") or "")[:2000],
        "stderr": (getattr(proc, "stderr", "") or "")[:2000],
    }


def _proxy_url_from_signals(signals: dict[str, Any]) -> str | None:
    parsed = signals.get("parsed_proxy")
    if not isinstance(parsed, dict):
        parsed = parse_proxy_server(signals.get("proxy_server"))
    endpoints = parsed.get("endpoints") if isinstance(parsed, dict) else []
    if isinstance(endpoints, list):
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue
            host = endpoint.get("host")
            port = endpoint.get("port")
            if host and port:
                return f"http://{host}:{port}"
    server = str(signals.get("proxy_server") or "").strip()
    if server and "=" not in server and ":" in server:
        return f"http://{server}" if "://" not in server else server
    return None


def run_connectivity_checks(
    signals: dict[str, Any],
    *,
    run: Callable[..., Any] = subprocess.run,
    timeout_seconds: float = 8.0,
) -> dict[str, Any]:
    """Run safe DNS/TCP/HTTPS checks for before/after comparison.

    The probes are read-only and bounded. Failures are emitted as structured signals rather
    than exceptions.
    """

    checks: dict[str, Any] = {
        "dns": _probe(
            "dns",
            ["nslookup", "www.microsoft.com"],
            run=run,
            timeout_seconds=timeout_seconds,
        ),
        "tcp_443": _probe(
            "tcp_443",
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Test-NetConnection www.microsoft.com -Port 443 -InformationLevel Quiet",
            ],
            run=run,
            timeout_seconds=timeout_seconds,
        ),
        "https_direct": _probe(
            "https_direct",
            ["curl.exe", "-I", "--max-time", str(int(timeout_seconds)), "--noproxy", "*", "https://www.microsoft.com"],
            run=run,
            timeout_seconds=timeout_seconds + 2.0,
        ),
        "https_via_proxy": {
            "name": "https_via_proxy",
            "ok": None,
            "returncode": None,
            "stdout": "",
            "stderr": "skipped_no_enabled_proxy",
        },
    }
    proxy_url = _proxy_url_from_signals(signals)
    if int(signals.get("proxy_enable") or 0) == 1 and proxy_url:
        checks["https_via_proxy"] = _probe(
            "https_via_proxy",
            ["curl.exe", "-I", "--max-time", str(int(timeout_seconds)), "--proxy", proxy_url, "https://www.microsoft.com"],
            run=run,
            timeout_seconds=timeout_seconds + 2.0,
        )
        checks["https_via_proxy"]["proxy_url"] = proxy_url
    checks["proxy_enable"] = signals.get("proxy_enable")
    checks["proxy_server"] = signals.get("proxy_server")
    return checks


def compare_connectivity(before: dict[str, Any] | None, after: dict[str, Any]) -> dict[str, Any]:
    """Return a before/after connectivity envelope with regression detection."""

    regressions: list[str] = []
    if before:
        for key in ("dns", "tcp_443", "https_direct", "https_via_proxy"):
            b = before.get(key)
            a = after.get(key)
            if isinstance(b, dict) and isinstance(a, dict) and b.get("ok") is True and a.get("ok") is False:
                regressions.append(key)
    return {
        "before": before,
        "after": after,
        "regression_detected": bool(regressions),
        "regressed_checks": regressions,
    }


def capture_proxy_writer_event(
    *,
    proxy_before_signals: dict[str, Any],
    proxy_after_signals: dict[str, Any],
    connectivity_before: dict[str, Any] | None,
    since_seconds: int = 120,
    procmon_csv_path: str | Path | None = None,
    run: Callable[..., Any] = subprocess.run,
) -> ProxyAttributionEvent:
    """Capture listener, writer, persistence, certificate, and connectivity context."""

    parsed = proxy_after_signals.get("parsed_proxy") or parse_proxy_server(proxy_after_signals.get("proxy_server"))
    port = parsed.get("localhost_port") if isinstance(parsed, dict) else None
    listener_attr = attribute_proxy_port(port if isinstance(port, int) else None)
    candidate_listeners = candidate_listeners_from_attribution(listener_attr)
    writer_result = collect_registry_writer_evidence(
        since_seconds=since_seconds,
        procmon_csv_path=procmon_csv_path,
        run=run,
    )
    connectivity_after = run_connectivity_checks(proxy_after_signals, run=run)
    connectivity = compare_connectivity(connectivity_before, connectivity_after)
    return build_proxy_attribution_event(
        proxy_before=proxy_tuple_from_signals(proxy_before_signals),
        proxy_after=proxy_tuple_from_signals(proxy_after_signals),
        candidate_listeners=candidate_listeners,
        registry_writer_evidence=writer_result.get("evidence") or [],
        persistence_indicators=collect_persistence_indicators(),
        certificate_indicators=collect_certificate_indicators(),
        connectivity_before_after=connectivity,
        writer_limitations=list(writer_result.get("limitations") or []),
        parsed_proxy=parsed if isinstance(parsed, dict) else None,
    )


def watch_writer(
    *,
    interval_seconds: float,
    audit_path: Path | None = None,
    since_seconds: int = 120,
    procmon_csv_path: str | Path | None = None,
    max_events: int | None = None,
    once: bool = False,
    run: Callable[..., Any] = subprocess.run,
) -> int:
    """Poll WinINET proxy tuple and append attribution events when it changes."""

    path = audit_path or default_writer_audit_path()
    previous_signals = collect_proxy_signals()
    previous_tuple = proxy_tuple_from_signals(previous_signals)
    previous_connectivity = run_connectivity_checks(previous_signals, run=run)

    if once:
        observed = build_proxy_attribution_event(
            proxy_before=None,
            proxy_after=previous_tuple,
            candidate_listeners=[],
            registry_writer_evidence=[],
            persistence_indicators={},
            certificate_indicators={},
            connectivity_before_after={"after": previous_connectivity, "regression_detected": False},
            writer_limitations=["Initial snapshot only; no state change observed."],
            parsed_proxy=previous_signals.get("parsed_proxy") if isinstance(previous_signals.get("parsed_proxy"), dict) else None,
        )
        print(json.dumps(observed.to_jsonable(), indent=2, ensure_ascii=False))
        return 0

    emitted = 0
    while True:
        time.sleep(max(1.0, float(interval_seconds)))
        current_signals = collect_proxy_signals()
        current_tuple = proxy_tuple_from_signals(current_signals)
        if current_tuple != previous_tuple:
            event = capture_proxy_writer_event(
                proxy_before_signals=previous_signals,
                proxy_after_signals=current_signals,
                connectivity_before=previous_connectivity,
                since_seconds=since_seconds,
                procmon_csv_path=procmon_csv_path,
                run=run,
            )
            append_proxy_writer_event(event, audit_path=path)
            print(json.dumps(event.to_jsonable(), ensure_ascii=False))
            emitted += 1
            previous_signals = current_signals
            previous_tuple = current_tuple
            previous_connectivity = (event.connectivity_before_after.get("after") or {}) if event.connectivity_before_after else {}
            if max_events is not None and emitted >= max_events:
                return 0


def load_writer_audit_events(path: Path | None = None) -> list[dict[str, Any]]:
    """Load valid JSON rows from the writer attribution audit file."""

    audit_path = path or default_writer_audit_path()
    if not audit_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def build_writer_report(events: list[dict[str, Any]], *, audit_path: Path | None = None) -> dict[str, Any]:
    """Aggregate writer attribution audit events for JSON/Markdown reports."""

    by_level: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    for event in events:
        level = str(event.get("evidence_level") or event.get("event_type") or "UNKNOWN")
        by_level[level] = by_level.get(level, 0) + 1
        cls = str(event.get("classification") or "UNCLASSIFIED")
        by_classification[cls] = by_classification.get(cls, 0) + 1
    latest = events[-1] if events else None
    return {
        "generated_at": utc_now_iso(),
        "event_count": len(events),
        "counts_by_evidence_level": by_level,
        "counts_by_classification": by_classification,
        "latest_event": latest,
        "audit_path": str(audit_path or default_writer_audit_path()),
    }


def format_writer_report_markdown(report: dict[str, Any]) -> str:
    """Render a concise Markdown writer attribution report."""

    lines = [
        "# Proxy Writer Attribution Report",
        "",
        f"- generated_at: `{report.get('generated_at')}`",
        f"- event_count: `{report.get('event_count')}`",
        "",
        "## Evidence Levels",
    ]
    for key, value in sorted((report.get("counts_by_evidence_level") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.append("")
    lines.append("## Classifications")
    for key, value in sorted((report.get("counts_by_classification") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    latest = report.get("latest_event") or {}
    if latest:
        lines.extend(
            [
                "",
                "## Latest Event",
                f"- event_id: `{latest.get('event_id')}`",
                f"- evidence_level: `{latest.get('evidence_level')}`",
                f"- classification: `{latest.get('classification')}`",
                f"- confidence: `{latest.get('confidence')}`",
            ]
        )
    return "\n".join(lines)


def import_procmon_trace(path: str | Path, *, audit_path: Path | None = None) -> dict[str, Any]:
    """Parse a Procmon CSV and append an import audit row."""

    evidence = parse_procmon_csv(path)
    payload = {
        "event_type": "procmon_import",
        "timestamp": utc_now_iso(),
        "source_path": str(path),
        "evidence_count": len(evidence),
        "registry_writer_evidence": [item.to_jsonable() for item in evidence],
        "limitations": []
        if evidence
        else ["No Procmon RegSetValue rows matched WinINET proxy value filters."],
        "safety_boundary": {
            "read_only_import": True,
            "no_remediation_executed": True,
        },
    }
    append_jsonl(audit_path or default_writer_audit_path(), payload)
    return payload


def find_event(event_id: str, *, audit_path: Path | None = None) -> dict[str, Any] | None:
    """Find a writer attribution event by id."""

    for event in load_writer_audit_events(audit_path):
        if str(event.get("event_id") or "") == event_id:
            return event
    return None


def explain_event(event_id: str, *, audit_path: Path | None = None) -> str:
    """Return an audit-friendly explanation for one event id."""

    event = find_event(event_id, audit_path=audit_path)
    if event is None:
        return f"Event {event_id} was not found in the proxy writer audit log."
    lines = [
        f"event_id: {event.get('event_id')}",
        f"timestamp: {event.get('timestamp')}",
        f"evidence_level: {event.get('evidence_level')}",
        f"classification: {event.get('classification')}",
        f"confidence: {event.get('confidence')}",
        "",
        "changed_fields:",
    ]
    for field in event.get("changed_fields") or []:
        lines.append(f"- {field}")
    lines.extend(["", "interpretation:"])
    if event.get("evidence_level") == "WRITER_PROOF":
        lines.append("- Registry-write telemetry is present; this is writer proof at the source telemetry level.")
    elif event.get("candidate_listeners"):
        lines.append("- A listener/process was correlated to the configured proxy port, so it is a candidate_actor only.")
    else:
        lines.append("- The event is based on observed proxy state change without writer proof.")
    lines.append("- Netstat tells who is listening. Sysmon/Procmon tells who wrote the registry. These are different.")
    lines.extend(["", "limitations:"])
    for limitation in event.get("limitations") or []:
        lines.append(f"- {limitation}")
    lines.extend(["", "recommended_next_steps:"])
    for step in event.get("recommended_next_steps") or []:
        lines.append(f"- {step}")
    return "\n".join(lines)
