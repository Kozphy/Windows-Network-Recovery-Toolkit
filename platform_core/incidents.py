"""Deterministic incident clustering over local FailureEvent rows (fleet-style demo)."""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

ClusterSeverity = Literal["low", "medium", "high"]


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _severity_rank(s: str | None) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(str(s or "low").lower(), 1)


def _rank_to_label(r: int) -> ClusterSeverity:
    if r >= 3:
        return "high"
    if r == 2:
        return "medium"
    return "low"


class IncidentCluster(BaseModel):
    """Correlated failure events within a category/pattern/time window."""

    cluster_id: str = Field(description="Stable UUID for this cluster row.")
    category: str
    pattern_key: str = Field(description="category + fingerprint of signals / recommended action.")
    event_ids: list[str]
    endpoint_ids: list[str]
    first_seen_at: str
    last_seen_at: str
    cluster_severity: ClusterSeverity
    affected_endpoint_count: int = Field(ge=0)
    event_count: int = Field(ge=0)


def _pattern_fingerprint(ev: dict[str, Any]) -> str:
    cat = str(ev.get("category") or "unknown")
    action = str(ev.get("recommended_action_key") or "")
    summary_hint = str(ev.get("summary") or "")[:48]
    raw = f"{cat}|{action}|{summary_hint}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def _make_cluster(bucket: list[tuple[dict[str, Any], datetime, datetime]]) -> IncidentCluster:
    evs = [b[0] for b in bucket]
    first_t = min(b[1] for b in bucket)
    last_t = max(b[2] for b in bucket)
    cat = str(evs[0].get("category") or "unknown")
    fp = _pattern_fingerprint(evs[0])
    pattern_display = f"{cat}:{fp}"
    eids = sorted({str(e.get("event_id")) for e in evs if e.get("event_id")})
    eps = sorted({str(e.get("endpoint_id") or "") for e in evs if e.get("endpoint_id")})
    ranks = [_severity_rank(e.get("severity")) for e in evs]
    mx = max(ranks) if ranks else 1
    if len(eps) >= 2 and mx < 3:
        mx = min(3, mx + 1)
    sev = _rank_to_label(mx)
    cid = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "|".join(eids + [first_t.isoformat(), last_t.isoformat()]),
        )
    )
    return IncidentCluster(
        cluster_id=cid,
        category=cat,
        pattern_key=pattern_display,
        event_ids=eids,
        endpoint_ids=eps,
        first_seen_at=first_t.replace(tzinfo=timezone.utc).isoformat(),
        last_seen_at=last_t.replace(tzinfo=timezone.utc).isoformat(),
        cluster_severity=sev,
        affected_endpoint_count=len(eps),
        event_count=len(evs),
    )


def cluster_failure_events(
    events: list[dict[str, Any]],
    *,
    window_seconds: int = 3600,
) -> list[IncidentCluster]:
    """Group events by category + signal fingerprint; split when inter-arrival gap exceeds window.

    **Input assumptions:** dicts shaped like ``FailureEvent.model_dump()`` with ``event_id``,
    ``endpoint_id``, optional ISO ``first_seen_at`` / ``last_seen_at``.

    **Output guarantees:** deterministic given sorted inputs; pure (no I/O).

    **Idempotency:** Running twice on the same list returns identical clusters.
    """
    groups: dict[str, list[tuple[dict[str, Any], datetime, datetime]]] = defaultdict(list)

    for ev in events:
        eid = str(ev.get("event_id") or "")
        if not eid:
            continue
        fs = _parse_iso(ev.get("first_seen_at")) or _parse_iso(ev.get("last_seen_at"))
        ls = _parse_iso(ev.get("last_seen_at")) or fs
        if fs is None or ls is None:
            now = datetime.now(timezone.utc)
            fs = ls = now
        cat = str(ev.get("category") or "unknown")
        fp = _pattern_fingerprint(ev)
        gkey = f"{cat}|{fp}"
        groups[gkey].append((ev, fs, ls))

    out: list[IncidentCluster] = []
    for gkey in sorted(groups.keys()):
        rows = sorted(groups[gkey], key=lambda x: (x[2], str(x[0].get("event_id"))))
        bucket: list[tuple[dict[str, Any], datetime, datetime]] = []
        for row in rows:
            ev, fs, ls = row
            if not bucket:
                bucket.append(row)
                continue
            prev_ls = max(b[2] for b in bucket)
            if (ls - prev_ls).total_seconds() > window_seconds:
                out.append(_make_cluster(bucket))
                bucket = [row]
            else:
                bucket.append(row)
        if bucket:
            out.append(_make_cluster(bucket))

    out.sort(key=lambda c: (c.last_seen_at, c.cluster_id))
    return out
