"""Persistent named proxy snapshots (JSONL + optional default JSON) for last-known-good restores."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..core.time_utils import utc_now_iso
from .models import ProxySnapshot
from .parser import parse_proxy_server, summarize_proxy_risk

SCHEMA_VERSION = 1
SNAPSHOTS_FILENAME = "proxy_known_good_snapshots.jsonl"
DEFAULT_CONFIG_RELPATH = Path("config") / "last_known_good_proxy.json"


def snapshots_jsonl_path(repo_root: Path) -> Path:
    return repo_root / "logs" / SNAPSHOTS_FILENAME


def default_known_good_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_CONFIG_RELPATH


def summarize_snapshot_risk(snapshot: ProxySnapshot) -> str:
    """Return a short categorical label for list/diff output (no hostname)."""

    parsed = parse_proxy_server(snapshot.proxy_server)
    return summarize_proxy_risk(parsed, snapshot.proxy_enable == 1)


def append_named_snapshot(
    repo_root: Path,
    *,
    name: str,
    snapshot: ProxySnapshot,
    risk_summary: str | None = None,
) -> dict[str, Any]:
    """Append one record to ``logs/proxy_known_good_snapshots.jsonl``."""

    path = snapshots_jsonl_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    risk = risk_summary or summarize_snapshot_risk(snapshot)
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "name": name.strip(),
        "saved_at": utc_now_iso(),
        "risk_summary": risk,
        "snapshot": snapshot.to_jsonable(),
    }
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return row


def write_default_config(repo_root: Path, record: dict[str, Any]) -> Path:
    """Write ``config/last_known_good_proxy.json`` from a full row (name, saved_at, snapshot, ...)."""

    path = default_known_good_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": SCHEMA_VERSION,
        "name": record.get("name"),
        "saved_at": record.get("saved_at"),
        "risk_summary": record.get("risk_summary"),
        "snapshot": record.get("snapshot"),
    }
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def iter_named_records(repo_root: Path) -> Iterator[dict[str, Any]]:
    path = snapshots_jsonl_path(repo_root)
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("name") and isinstance(obj.get("snapshot"), dict):
                yield obj


def get_latest_named_record(repo_root: Path, name: str) -> dict[str, Any] | None:
    """Return the last JSONL row matching ``name`` (file order)."""

    want = name.strip()
    last: dict[str, Any] | None = None
    for rec in iter_named_records(repo_root):
        if str(rec.get("name")) == want:
            last = rec
    return last


def snapshot_from_record(rec: dict[str, Any] | None) -> ProxySnapshot | None:
    if rec is None:
        return None
    snap = rec.get("snapshot")
    if not isinstance(snap, dict):
        return None
    try:
        return ProxySnapshot.from_json_dict(snap)
    except (KeyError, TypeError, ValueError):
        return None


def load_default_record(repo_root: Path) -> dict[str, Any] | None:
    path = default_known_good_path(repo_root)
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(blob, dict):
        return None
    return blob


def list_snapshot_summaries(repo_root: Path) -> list[dict[str, Any]]:
    """One row per distinct name (latest win), plus optional default file flag."""

    by_name: dict[str, dict[str, Any]] = {}
    for rec in iter_named_records(repo_root):
        n = str(rec.get("name"))
        by_name[n] = rec
    default_rec = load_default_record(repo_root)
    default_name = str(default_rec["name"]) if default_rec and default_rec.get("name") else None
    out: list[dict[str, Any]] = []
    for nm in sorted(by_name.keys()):
        rec = by_name[nm]
        snap = snapshot_from_record(rec)
        out.append(
            {
                "name": nm,
                "saved_at": rec.get("saved_at"),
                "risk_summary": rec.get("risk_summary"),
                "has_default_file": default_name == nm,
            },
        )
    return out
