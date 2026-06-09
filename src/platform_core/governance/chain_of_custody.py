"""Hash-chained audit chain of custody."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


HASH_CHAIN_EXCLUDED_FIELDS = frozenset({"previous_hash", "current_hash", "signature_status"})


def audit_hash_body(record: dict[str, Any]) -> dict[str, Any]:
    """Fields participating in the hash — must match ``append_audit`` pre-hash body."""
    return {k: v for k, v in record.items() if k not in HASH_CHAIN_EXCLUDED_FIELDS}


def chain_hash(previous_hash: str, record_body: dict[str, Any]) -> str:
    payload = previous_hash + "|" + _canonical_json(record_body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain(records: list[dict[str, Any]]) -> tuple[bool, str]:
    prev = "genesis"
    for idx, rec in enumerate(records):
        body = audit_hash_body(rec)
        expected = chain_hash(prev, body)
        current = str(rec.get("current_hash", ""))
        if current != expected:
            return False, f"chain break at index {idx}"
        prev = current
    return True, "ok"
