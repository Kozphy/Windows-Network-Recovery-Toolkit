"""Analytics pipeline evidence schema — normalized events with raw snapshots preserved.

Module responsibility:
    Define ``EvidenceEvent`` and normalizers that convert proxy CLI/audit rows into a stable
    analytics shape while preserving ``raw_snapshot`` for replay.

System placement:
    Upstream of ``incident_classifier`` and ``analytics_pipeline``. Tiers T0–T5 label claim
    strength — they do not upgrade proof automatically.

Key invariants:
    * ``event_id`` is deterministic from timestamp, type, and stable fields.
    * ``timestamp_utc`` expected as ISO-8601 UTC string.
    * ``STANDARD_LIMITATIONS`` appended to normalized events where applicable.

Data handling:
    Missing optional fields become empty dicts or false — normalizers do not invent probe results.
    Duplicate event_ids deduplicated in ``analytics_pipeline._dedupe_events``.
"""

from __future__ import annotations

import hashlib
import json
import socket
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class EvidenceTier(StrEnum):
    T0_OBSERVATION = "T0_OBSERVATION"
    T1_STATE_EVIDENCE = "T1_STATE_EVIDENCE"
    T2_RUNTIME_EVIDENCE = "T2_RUNTIME_EVIDENCE"
    T3_PATH_EVIDENCE = "T3_PATH_EVIDENCE"
    T4_WRITER_PROOF = "T4_WRITER_PROOF"
    T5_GOVERNANCE_PROOF = "T5_GOVERNANCE_PROOF"


STANDARD_LIMITATIONS = [
    "Listener ownership is correlation, not registry writer proof.",
    "Registry writer attribution requires Sysmon, Procmon, ETW, or EventLog evidence.",
    "Successful proxy probe does not prove the proxy is safe or intended.",
    "Risk classification is a triage signal, not a malware verdict.",
]


@dataclass
class EvidenceEvent:
    """Normalized evidence row for analytics pipeline and export.

    Attributes:
        event_id: Deterministic hash id (see ``make_event_id``).
        timestamp_utc: Observation time in UTC ISO-8601.
        endpoint_id: Host identifier; defaults via ``default_endpoint_id`` in normalizers.
        evidence_type: proxy_state, listener_state, probe_result, proxy_change, etc.
        source_command: CLI command that produced the observation.
        raw_snapshot: Unmodified source dict for replay.
        normalized_fields: Fields used by classifier and charts.
        evidence_tier: T0–T5 claim strength label.
        evidence_summary: One-line human summary.
        limitations: Per-event governance caveats.
    """

    event_id: str
    timestamp_utc: str
    endpoint_id: str | None
    evidence_type: str
    source_command: str
    raw_snapshot: dict[str, Any]
    normalized_fields: dict[str, Any]
    evidence_tier: str
    evidence_summary: str
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_event_id(timestamp_utc: str, evidence_type: str, stable_fields: dict[str, Any]) -> str:
    """Deterministic event id from stable fields (sorted JSON hash)."""
    payload = json.dumps(
        {"timestamp_utc": timestamp_utc, "evidence_type": evidence_type, "stable": stable_fields},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def default_endpoint_id() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "local-endpoint"


def normalize_proxy_state(raw: dict[str, Any], *, source_command: str = "proxy-status") -> EvidenceEvent:
    ts = str(raw.get("timestamp_utc") or raw.get("timestamp") or "")
    endpoint_id = raw.get("endpoint_id") or default_endpoint_id()
    enabled = bool(raw.get("wininet_proxy_enabled") or raw.get("proxy_enable"))
    server = str(raw.get("wininet_proxy_server") or raw.get("proxy_server") or "")
    winhttp_direct = raw.get("winhttp_direct_access")
    normalized = {
        "wininet_proxy_enabled": enabled,
        "wininet_proxy_server": server,
        "wininet_auto_config_url": str(raw.get("wininet_auto_config_url") or raw.get("auto_config_url") or ""),
        "winhttp_direct_access": winhttp_direct,
        "localhost_port": raw.get("localhost_port"),
        "wininet_winhttp_mismatch": bool(enabled and winhttp_direct),
    }
    stable = {"server": server, "enabled": enabled, "winhttp_direct": winhttp_direct}
    return EvidenceEvent(
        event_id=make_event_id(ts, "proxy_state", stable),
        timestamp_utc=ts,
        endpoint_id=str(endpoint_id) if endpoint_id else None,
        evidence_type="proxy_state",
        source_command=source_command,
        raw_snapshot=dict(raw),
        normalized_fields=normalized,
        evidence_tier=EvidenceTier.T1_STATE_EVIDENCE.value,
        evidence_summary=f"WinINET proxy_enable={int(enabled)} proxy_server={server or '(none)'}",
        limitations=list(STANDARD_LIMITATIONS),
    )


def normalize_listener_state(raw: dict[str, Any], *, source_command: str = "proxy-owner") -> EvidenceEvent:
    ts = str(raw.get("timestamp_utc") or raw.get("timestamp") or "")
    endpoint_id = raw.get("endpoint_id") or default_endpoint_id()
    proc = raw.get("process") if isinstance(raw.get("process"), dict) else {}
    port = raw.get("localhost_port")
    normalized = {
        "listener_found": bool(raw.get("listener_found")),
        "localhost_port": port,
        "listener_pid": proc.get("pid"),
        "listener_name": proc.get("name"),
        "listener_path": proc.get("exe_path"),
        "listener_command_line": proc.get("cmdline"),
    }
    stable = {"port": port, "pid": proc.get("pid"), "name": proc.get("name")}
    tier = EvidenceTier.T2_RUNTIME_EVIDENCE.value
    if raw.get("writer_proof") or raw.get("sysmon_event_id") == 13:
        tier = EvidenceTier.T4_WRITER_PROOF.value
    summary = (
        f"listener_found={normalized['listener_found']} port={port} process={proc.get('name') or 'unknown'}"
    )
    return EvidenceEvent(
        event_id=make_event_id(ts, "listener_state", stable),
        timestamp_utc=ts,
        endpoint_id=str(endpoint_id) if endpoint_id else None,
        evidence_type="listener_state",
        source_command=source_command,
        raw_snapshot=dict(raw),
        normalized_fields=normalized,
        evidence_tier=tier,
        evidence_summary=summary,
        limitations=list(STANDARD_LIMITATIONS),
    )


def normalize_probe_result(raw: dict[str, Any], *, source_command: str = "proxy-health") -> EvidenceEvent:
    ts = str(raw.get("timestamp_utc") or raw.get("timestamp") or "")
    endpoint_id = raw.get("endpoint_id") or default_endpoint_id()
    health = raw.get("health") if isinstance(raw.get("health"), dict) else raw
    normalized = {
        "proxy_status": health.get("proxy_status"),
        "tcp_listening": health.get("tcp_listening"),
        "tcp_connect_ok": health.get("tcp_connect_ok"),
        "direct_probe_ok": health.get("direct_probe_ok"),
        "proxy_probe_ok": health.get("proxy_probe_ok") or health.get("external_probe_ok"),
        "proxy_https_connect_ok": health.get("proxy_https_connect_ok"),
        "failure_reason": health.get("failure_reason"),
    }
    stable = {
        "proxy_status": normalized["proxy_status"],
        "direct": normalized["direct_probe_ok"],
        "proxy": normalized["proxy_probe_ok"],
    }
    return EvidenceEvent(
        event_id=make_event_id(ts, "probe_result", stable),
        timestamp_utc=ts,
        endpoint_id=str(endpoint_id) if endpoint_id else None,
        evidence_type="probe_result",
        source_command=source_command,
        raw_snapshot=dict(raw),
        normalized_fields=normalized,
        evidence_tier=EvidenceTier.T3_PATH_EVIDENCE.value,
        evidence_summary=f"proxy_status={normalized.get('proxy_status')} direct={normalized.get('direct_probe_ok')} proxy={normalized.get('proxy_probe_ok')}",
        limitations=list(STANDARD_LIMITATIONS),
    )


def normalize_proxy_change_event(raw: dict[str, Any], *, source_command: str = "proxy-watch") -> EvidenceEvent:
    ts = str(raw.get("timestamp_utc") or raw.get("timestamp") or "")
    endpoint_id = raw.get("endpoint_id") or default_endpoint_id()
    old_state = raw.get("old_state") or raw.get("before") or {}
    new_state = raw.get("new_state") or raw.get("after") or {}
    normalized = {
        "old_proxy_server": old_state.get("wininet_proxy_server"),
        "new_proxy_server": new_state.get("wininet_proxy_server"),
        "old_proxy_enabled": old_state.get("wininet_proxy_enabled"),
        "new_proxy_enabled": new_state.get("wininet_proxy_enabled"),
        "localhost_port": new_state.get("localhost_port"),
        "reverter_suspected": bool(raw.get("reverter_suspected")),
        "reverter_status": (raw.get("reverter_diagnosis") or {}).get("status"),
    }
    stable = {
        "old": normalized["old_proxy_server"],
        "new": normalized["new_proxy_server"],
        "enabled": normalized["new_proxy_enabled"],
    }
    return EvidenceEvent(
        event_id=make_event_id(ts, "proxy_change", stable),
        timestamp_utc=ts,
        endpoint_id=str(endpoint_id) if endpoint_id else None,
        evidence_type="proxy_change",
        source_command=source_command,
        raw_snapshot=dict(raw),
        normalized_fields=normalized,
        evidence_tier=EvidenceTier.T1_STATE_EVIDENCE.value,
        evidence_summary=(
            f"ProxyServer {normalized['old_proxy_server']} -> {normalized['new_proxy_server']}"
        ),
        limitations=list(STANDARD_LIMITATIONS),
    )


def events_to_json(events: list[EvidenceEvent]) -> list[dict[str, Any]]:
    return [e.to_dict() for e in events]


def events_from_dicts(rows: list[dict[str, Any]]) -> list[EvidenceEvent]:
    out: list[EvidenceEvent] = []
    for row in rows:
        out.append(EvidenceEvent(**{k: v for k, v in row.items() if k in EvidenceEvent.__dataclass_fields__}))
    return out
