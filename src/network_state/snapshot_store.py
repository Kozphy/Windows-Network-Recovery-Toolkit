"""Named network/proxy snapshots — append-only JSONL + default profile pointer."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..core.time_utils import utc_now_iso
from ..proxy_guard.known_good_store import summarize_snapshot_risk
from ..proxy_guard.models import ProxySnapshot

from .paths import default_profile_json, snapshots_jsonl

SCHEMA_VERSION = 1


def append_snapshot(repo_root: Path, *, name: str, snapshot: ProxySnapshot, risk_summary: str | None = None) -> dict[str, Any]:
    path = snapshots_jsonl(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    risk = risk_summary or summarize_snapshot_risk(snapshot)
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "name": name.strip(),
        "saved_at": utc_now_iso(),
        "risk_summary": risk,
        "snapshot": snapshot.to_jsonable(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def iter_records(repo_root: Path) -> Iterator[dict[str, Any]]:
    path = snapshots_jsonl(repo_root)
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


def get_latest_named(repo_root: Path, name: str) -> dict[str, Any] | None:
    want = name.strip()
    last: dict[str, Any] | None = None
    for rec in iter_records(repo_root):
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
    path = default_profile_json(repo_root)
    if not path.is_file():
        return None
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return blob if isinstance(blob, dict) else None


def write_default_profile(repo_root: Path, *, name: str) -> Path:
    """Point default JSON at latest row for ``name``."""

    rec = get_latest_named(repo_root, name)
    if rec is None:
        raise ValueError(f"Unknown profile name: {name}")
    path = default_profile_json(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": SCHEMA_VERSION,
        "name": rec.get("name"),
        "saved_at": rec.get("saved_at"),
        "risk_summary": rec.get("risk_summary"),
        "snapshot": rec.get("snapshot"),
    }
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def list_profile_summaries(repo_root: Path) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for rec in iter_records(repo_root):
        by_name[str(rec["name"])] = rec
    default_rec = load_default_record(repo_root)
    default_name = str(default_rec["name"]) if default_rec and default_rec.get("name") else None
    return [
        {
            "name": nm,
            "saved_at": rec.get("saved_at"),
            "risk_summary": rec.get("risk_summary"),
            "is_default": default_name == nm,
        }
        for nm, rec in sorted(by_name.items(), key=lambda x: x[0])
    ]


def resolve_named_snapshot(repo_root: Path, name: str) -> ProxySnapshot | None:
    return snapshot_from_record(get_latest_named(repo_root, name))
