"""Fuse registry-write telemetry with listener attribution (diagnostic evidence only)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from telemetry.models import EvidenceLevel, RegistryWriteEvent, RegistryWriterEvidence
from telemetry.sysmon_reader import is_relevant_proxy_registry_path

NO_TELEMETRY_LIMITATION = "No Sysmon/EventLog/ETW registry writer telemetry was supplied."
LISTENER_NOT_PROOF = (
    "Listener/process correlation does not prove registry writer identity without "
    "registry-write telemetry."
)
WRITER_NOT_MALICIOUS = (
    "REGISTRY_WRITER_OBSERVED identifies a process that appears to have written a proxy "
    "registry value; this does not prove malicious intent."
)
MATCH_NOT_INTENT = (
    "WRITER_AND_LISTENER_MATCH means the same process appears to have written the proxy key "
    "and owned the listener port; this still does not prove intent."
)
CONFLICT_NEUTRAL = (
    "Registry writer telemetry and listener owner disagree; attribution remains unresolved "
    "and neither process should be accused automatically."
)


def default_no_telemetry_evidence() -> RegistryWriterEvidence:
    """Baseline evidence payload when no telemetry input is supplied."""
    return RegistryWriterEvidence(
        evidence_level="NO_TELEMETRY",
        matched_events=[],
        candidate_writers=[],
        listener_match=None,
        limitations=[NO_TELEMETRY_LIMITATION, LISTENER_NOT_PROOF],
        recommended_next_steps=[
            "Enable Sysmon registry value set logging (Event ID 13) or import Event Log / Procmon traces.",
            "Re-run fusion with telemetry fixtures or live exports around the proxy change time.",
        ],
        confidence_rank="none",
    )


def _normalize_process_path(path: str | None) -> str:
    if not path:
        return ""
    return os.path.normcase(path.replace("/", "\\"))


def _writer_identity(event: RegistryWriteEvent) -> dict[str, Any]:
    return {
        "process_id": event.process_id,
        "process_name": event.process_name,
        "process_path": event.process_path,
        "process_guid": event.process_guid,
        "user": event.user,
    }


def _dedupe_writers(events: list[RegistryWriteEvent]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    writers: list[dict[str, Any]] = []
    for event in events:
        key = (
            event.process_id,
            _normalize_process_path(event.process_path),
            (event.process_name or "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        writers.append(_writer_identity(event))
    return writers


def _event_in_window(
    event: RegistryWriteEvent,
    *,
    start: datetime,
    end: datetime,
) -> bool:
    ts = event.timestamp_utc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return start <= ts <= end


def _listener_owner(listener_attribution: dict[str, Any] | None) -> dict[str, Any] | None:
    if not listener_attribution:
        return None
    pid = listener_attribution.get("pid") or listener_attribution.get("process_id")
    return {
        "process_id": pid,
        "process_name": listener_attribution.get("process_name"),
        "process_path": listener_attribution.get("process_path"),
        "port": listener_attribution.get("port"),
        "attribution_confidence": listener_attribution.get("attribution_confidence"),
    }


def _writer_matches_listener(writer: dict[str, Any], listener: dict[str, Any]) -> bool:
    listener_pid = listener.get("process_id")
    listener_path = _normalize_process_path(listener.get("process_path"))
    listener_name = str(listener.get("process_name") or "").lower()
    writer_pid = writer.get("process_id")
    writer_path = _normalize_process_path(writer.get("process_path"))
    writer_name = str(writer.get("process_name") or "").lower()
    if listener_pid is not None and writer_pid is not None and listener_pid == writer_pid:
        return True
    if listener_path and writer_path and listener_path == writer_path:
        return True
    if listener_name and writer_name and listener_name == writer_name:
        return True
    return False


def _writers_match_listener(
    writers: list[dict[str, Any]],
    listener: dict[str, Any] | None,
) -> bool:
    if not listener or not writers:
        return False
    return any(_writer_matches_listener(writer, listener) for writer in writers)


def _writers_conflict_listener(
    writers: list[dict[str, Any]],
    listener: dict[str, Any] | None,
) -> bool:
    if not listener or not writers:
        return False
    identifiable_writers = [
        writer
        for writer in writers
        if writer.get("process_id") is not None
        or writer.get("process_path")
        or writer.get("process_name")
    ]
    if not identifiable_writers:
        return False
    listener_identifiable = (
        listener.get("process_id") is not None
        or listener.get("process_path")
        or listener.get("process_name")
    )
    if not listener_identifiable:
        return False
    matches = [_writer_matches_listener(writer, listener) for writer in identifiable_writers]
    if any(matches) and not all(matches):
        return True
    return not any(matches)


def _writers_missing_identity(events: list[RegistryWriteEvent]) -> bool:
    if not events:
        return False
    return all(
        event.process_id is None and not event.process_path and not event.process_name
        for event in events
    )


def fuse_registry_writer_evidence(
    *,
    proxy_change_time: datetime,
    telemetry_events: list[RegistryWriteEvent],
    listener_attribution: dict[str, Any] | None = None,
    window_before_seconds: int = 120,
    window_after_seconds: int = 30,
) -> RegistryWriterEvidence:
    """Fuse telemetry rows with optional listener attribution into evidence summary."""
    if proxy_change_time.tzinfo is None:
        proxy_change_time = proxy_change_time.replace(tzinfo=timezone.utc)

    if not telemetry_events:
        return default_no_telemetry_evidence()

    start = proxy_change_time - timedelta(seconds=window_before_seconds)
    end = proxy_change_time + timedelta(seconds=window_after_seconds)
    windowed = [
        event for event in telemetry_events if _event_in_window(event, start=start, end=end)
    ]
    relevant = [event for event in windowed if is_relevant_proxy_registry_path(event.registry_path)]

    if not relevant:
        return RegistryWriterEvidence(
            evidence_level="NO_RELEVANT_REGISTRY_WRITES",
            matched_events=[],
            candidate_writers=[],
            listener_match=_listener_owner(listener_attribution),
            limitations=[
                "Telemetry rows were supplied but none matched proxy registry paths in the time window.",
                LISTENER_NOT_PROOF,
            ],
            recommended_next_steps=[
                "Verify Sysmon/EventLog collection includes HKCU Internet Settings proxy values.",
                "Widen the fusion window or align proxy_change_time with the registry drift timestamp.",
            ],
            confidence_rank="none",
        )

    writers = _dedupe_writers(relevant)
    listener = _listener_owner(listener_attribution)
    limitations = [WRITER_NOT_MALICIOUS, LISTENER_NOT_PROOF]
    for event in relevant:
        limitations.extend(event.parse_warnings)

    if _writers_missing_identity(relevant):
        return RegistryWriterEvidence(
            evidence_level="INCONCLUSIVE",
            matched_events=relevant,
            candidate_writers=writers,
            listener_match=listener,
            limitations=limitations
            + ["Matched registry writes lack sufficient process identity fields."],
            recommended_next_steps=[
                "Collect richer telemetry (Image/ProcessId/CommandLine) from Sysmon Event ID 13.",
                "Import Procmon or Security 4657 rows with process metadata.",
            ],
            confidence_rank="low",
        )

    evidence_level: EvidenceLevel = "REGISTRY_WRITER_OBSERVED"
    confidence_rank = "medium"
    listener_match: dict[str, Any] | None = None
    recommended = [
        "Preserve telemetry exports and correlate with proxy drift timeline.",
        "Review candidate writer signing, parent process, and recent package changes.",
    ]

    if (
        listener
        and _writers_match_listener(writers, listener)
        and not _writers_conflict_listener(writers, listener)
    ):
        evidence_level = "WRITER_AND_LISTENER_MATCH"
        confidence_rank = "high"
        listener_match = {
            "matched": True,
            "listener": listener,
            "writers": writers,
        }
        limitations.append(MATCH_NOT_INTENT)
    elif listener and _writers_conflict_listener(writers, listener):
        evidence_level = "CONFLICTING_EVIDENCE"
        confidence_rank = "medium"
        listener_match = {
            "matched": False,
            "listener": listener,
            "writers": writers,
        }
        limitations.append(CONFLICT_NEUTRAL)
        recommended.append(
            "Treat listener owner and registry writer as separate candidates until stronger proof is collected."
        )

    return RegistryWriterEvidence(
        evidence_level=evidence_level,
        matched_events=relevant,
        candidate_writers=writers,
        listener_match=listener_match,
        limitations=limitations,
        recommended_next_steps=recommended,
        confidence_rank=confidence_rank,
    )


def build_report_registry_writer_section(
    *,
    attribution: dict[str, Any] | None,
    telemetry_events: list[RegistryWriteEvent] | None,
    proxy_change_time: datetime | None = None,
) -> dict[str, Any]:
    """Build registry_writer_evidence dict for proxy_guard report payloads."""
    if not telemetry_events:
        return default_no_telemetry_evidence().to_dict()

    change_time = proxy_change_time or datetime.now(timezone.utc)
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=change_time,
        telemetry_events=telemetry_events,
        listener_attribution=attribution,
    )
    return evidence.to_dict()
