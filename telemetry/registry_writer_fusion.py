"""Fuse registry-write telemetry with listener attribution (diagnostic evidence only)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from telemetry.models import (
    EvidenceLevel,
    ListenerObservation,
    ProcessIdentity,
    RegistryWriteEvent,
    RegistryWriterEvidence,
)
from telemetry.sysmon_parser import is_relevant_proxy_registry_path

NO_WRITER_LIMITATION = "No registry writer telemetry was supplied for fusion."
LISTENER_NOT_PROOF = (
    "Listener/process correlation is candidate evidence only; it does not prove registry writer identity."
)
WRITER_NOT_MALICIOUS = (
    "REGISTRY_WRITER_OBSERVED identifies a process that appears to have written a proxy "
    "registry value; this does not prove malicious intent."
)
MATCH_NOT_INTENT = (
    "WRITER_AND_LISTENER_MATCH means the same process appears to have written the proxy key "
    "and owned the listener port; this still does not prove intent."
)
MISMATCH_NEUTRAL = (
    "Registry writer telemetry and listener owner disagree; attribution remains unresolved."
)


def default_no_telemetry_evidence(
    listener: ListenerObservation | None = None,
) -> RegistryWriterEvidence:
    """Baseline when no writer telemetry is available."""
    if listener is not None:
        return RegistryWriterEvidence(
            evidence_level="LISTENER_OBSERVED",
            listener_observation=listener.to_dict(),
            limitations=[LISTENER_NOT_PROOF, NO_WRITER_LIMITATION],
            recommended_next_steps=[
                "Import Sysmon Event ID 13 or Security 4657 rows around the proxy change time.",
                "Do not treat listener ownership as registry-writer proof.",
            ],
            confidence_rank="low",
        )
    return RegistryWriterEvidence(
        evidence_level="NO_WRITER_EVIDENCE",
        limitations=[NO_WRITER_LIMITATION, LISTENER_NOT_PROOF],
        recommended_next_steps=[
            "Enable Sysmon registry value set logging (Event ID 13) or import Event Log traces.",
            "Optionally supply listener attribution for LISTENER_OBSERVED candidate evidence.",
        ],
        confidence_rank="none",
    )


def _normalize_process_path(path: str | None) -> str:
    if not path:
        return ""
    return os.path.normcase(path.replace("/", "\\"))


def _writer_dict(identity: ProcessIdentity) -> dict[str, Any]:
    return identity.to_dict()


def _dedupe_writers(events: list[RegistryWriteEvent]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    writers: list[dict[str, Any]] = []
    for event in events:
        identity = event.writer
        key = (
            identity.process_id,
            _normalize_process_path(identity.process_path),
            (identity.process_name or "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        writers.append(_writer_dict(identity))
    return writers


def _event_in_window(event: RegistryWriteEvent, *, start: datetime, end: datetime) -> bool:
    ts = event.timestamp_utc
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return start <= ts <= end


def _identity_matches(a: ProcessIdentity, b: ProcessIdentity) -> bool:
    if a.process_id is not None and b.process_id is not None and a.process_id == b.process_id:
        return True
    ap = _normalize_process_path(a.process_path)
    bp = _normalize_process_path(b.process_path)
    if ap and bp and ap == bp:
        return True
    an = (a.process_name or "").lower()
    bn = (b.process_name or "").lower()
    return bool(an and bn and an == bn)


def _writers_match_listener(
    writers: list[dict[str, Any]], listener: ListenerObservation
) -> bool:
    listener_identity = ProcessIdentity.from_dict(listener.to_dict())
    for writer in writers:
        if _identity_matches(ProcessIdentity.from_dict(writer), listener_identity):
            return True
    return False


def _writers_mismatch_listener(
    writers: list[dict[str, Any]], listener: ListenerObservation
) -> bool:
    identifiable = [
        w
        for w in writers
        if w.get("process_id") is not None or w.get("process_path") or w.get("process_name")
    ]
    if not identifiable:
        return False
    listener_identity = ProcessIdentity.from_dict(listener.to_dict())
    if (
        listener_identity.process_id is None
        and not listener_identity.process_path
        and not listener_identity.process_name
    ):
        return False
    return not _writers_match_listener(identifiable, listener)


def _writers_missing_identity(events: list[RegistryWriteEvent]) -> bool:
    return bool(events) and all(
        e.process_id is None and not e.process_path and not e.process_name for e in events
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

    listener = ListenerObservation.from_attribution_dict(listener_attribution)

    if not telemetry_events:
        return default_no_telemetry_evidence(listener)

    start = proxy_change_time - timedelta(seconds=window_before_seconds)
    end = proxy_change_time + timedelta(seconds=window_after_seconds)
    windowed = [e for e in telemetry_events if _event_in_window(e, start=start, end=end)]
    relevant = [e for e in windowed if is_relevant_proxy_registry_path(e.registry_path)]

    if not relevant:
        base = default_no_telemetry_evidence(listener)
        base.limitations.append(
            "Telemetry rows were supplied but none matched proxy registry paths in the time window."
        )
        return base

    writers = _dedupe_writers(relevant)
    limitations = [WRITER_NOT_MALICIOUS, LISTENER_NOT_PROOF]
    for event in relevant:
        limitations.extend(event.parse_warnings)

    if _writers_missing_identity(relevant):
        return RegistryWriterEvidence(
            evidence_level="INCONCLUSIVE",
            matched_events=relevant,
            candidate_writers=writers,
            listener_observation=listener.to_dict() if listener else None,
            limitations=limitations + ["Matched registry writes lack sufficient process identity."],
            recommended_next_steps=[
                "Collect richer Sysmon Event ID 13 fields (Image, ProcessId, CommandLine).",
            ],
            confidence_rank="low",
        )

    evidence_level: EvidenceLevel = "REGISTRY_WRITER_OBSERVED"
    confidence_rank = "medium"
    listener_match: dict[str, Any] | None = None
    recommended = [
        "Preserve telemetry exports and correlate with proxy drift timeline.",
        "Review candidate writer signing and parent process context.",
    ]

    if listener:
        if _writers_match_listener(writers, listener) and not _writers_mismatch_listener(
            writers, listener
        ):
            evidence_level = "WRITER_AND_LISTENER_MATCH"
            confidence_rank = "high"
            listener_match = {
                "matched": True,
                "listener": listener.to_dict(),
                "writers": writers,
            }
            limitations.append(MATCH_NOT_INTENT)
        elif _writers_mismatch_listener(writers, listener):
            evidence_level = "WRITER_LISTENER_MISMATCH"
            confidence_rank = "medium"
            listener_match = {
                "matched": False,
                "listener": listener.to_dict(),
                "writers": writers,
            }
            limitations.append(MISMATCH_NEUTRAL)
            recommended.append(
                "Treat listener owner and registry writer as separate candidates until stronger proof."
            )

    return RegistryWriterEvidence(
        evidence_level=evidence_level,
        matched_events=relevant,
        candidate_writers=writers,
        listener_match=listener_match,
        listener_observation=listener.to_dict() if listener else None,
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
    listener = ListenerObservation.from_attribution_dict(attribution)
    if not telemetry_events:
        return default_no_telemetry_evidence(listener).to_dict()

    change_time = proxy_change_time or datetime.now(timezone.utc)
    evidence = fuse_registry_writer_evidence(
        proxy_change_time=change_time,
        telemetry_events=telemetry_events,
        listener_attribution=attribution,
    )
    return evidence.to_dict()
