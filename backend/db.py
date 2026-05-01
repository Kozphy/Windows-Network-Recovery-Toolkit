"""SQLite helpers for embedded telemetry tables and connection handling.

This module supplies `get_connection`, `init_db` (DDL from ``schema.sql``), and
focused read/write routines for the ``diagnosis_records`` shape used by some
callers. It does not implement HTTP auth or Stripe logic; those live in
``backend.main`` and sibling modules.

System placement:
    ``backend.main`` (when wired) → these helpers → ``backend/toolkit.db``.

Key invariants:
    - Database file path: ``backend/toolkit.db`` beside this module.
    - ``_utc_now_iso`` stamps use UTC with explicit offset in ISO-8601 text.
    - Connections set ``row_factory = sqlite3.Row`` for dict-like access.

Engineering Notes:
    ``init_db`` executes ``schema.sql``, which defines SaaS-oriented tables (for example
    ``diagnosis_logs``) that differ from the legacy ``diagnosis_records`` table targeted
    by `insert_diagnosis` in this file. Operators must provide DDL that matches whichever
    insert helpers they call, or ``sqlite3.OperationalError`` will surface at runtime.

Failure modes:
    Corrupt JSON in ``recent_processes`` breaks `get_diagnosis_history`; missing table
    mismatches break inserts during startup tests.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("toolkit.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format.

    Returns:
        str: UTC timestamp including timezone offset.
    """
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row mapping behavior.

    Returns:
        sqlite3.Connection: Open connection configured with `sqlite3.Row`.

    Raises:
        sqlite3.Error: If database path cannot be opened.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema from the local SQL schema file.

    Side effects:
        - Reads schema SQL file from disk.
        - Executes DDL against SQLite database file.

    Idempotency:
        Expected idempotency depends on schema SQL using safe
        `CREATE TABLE IF NOT EXISTS` patterns.

    Raises:
        OSError: On schema file read failures.
        sqlite3.Error: On DDL execution failures.
    """
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        conn.commit()


def insert_diagnosis(record: dict[str, Any]) -> int:
    """Persist one diagnosis record and return inserted row id.

    Schema expectations:
        Required keys include `device_id`, status fields, root-cause metadata,
        and recommendation/risk values.

    Side effects:
        Writes one row to `diagnosis_records` table.

    Idempotency:
        Not idempotent; repeated identical calls create additional rows.

    Audit Notes:
        - What can go wrong: missing required keys or malformed record values.
        - Detection: raised `KeyError`/`sqlite3.Error`.
        - Recovery: validate input payload before insertion and retry safely.

    Args:
        record: Normalized diagnosis record payload.

    Returns:
        int: SQLite autoincrement row id.

    Raises:
        KeyError: If required payload keys are missing.
        sqlite3.Error: If insert fails.
        TypeError: If values are not JSON/SQLite serializable.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO diagnosis_records (
                timestamp,
                device_id,
                dns_status,
                tcp_443_status,
                https_status,
                winhttp_proxy,
                user_proxy_enabled,
                user_proxy_server,
                recent_processes,
                root_cause,
                confidence,
                recommended_fix,
                risk_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("timestamp") or _utc_now_iso(),
                record["device_id"],
                record["dns_status"],
                record["tcp_443_status"],
                record["https_status"],
                record["winhttp_proxy"],
                1 if record["user_proxy_enabled"] else 0,
                record["user_proxy_server"],
                json.dumps(record.get("recent_processes", [])),
                record["root_cause"],
                record["confidence"],
                record["recommended_fix"],
                record["risk_level"],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def _deserialize_row(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a database row into API-friendly Python types.

    Args:
        row: SQLite row fetched from `diagnosis_records`.

    Returns:
        dict[str, Any]: Mapping with boolean/user proxy normalization and
        decoded recent process list.

    Raises:
        json.JSONDecodeError: If stored recent_processes JSON is corrupted.
    """
    item = dict(row)
    item["user_proxy_enabled"] = bool(item["user_proxy_enabled"])
    item["recent_processes"] = json.loads(item["recent_processes"]) if item["recent_processes"] else []
    return item


def get_latest_diagnosis() -> dict[str, Any] | None:
    """Fetch the newest diagnosis record, if available.

    Returns:
        dict[str, Any] | None: Latest diagnosis row or `None` when table empty.

    Raises:
        sqlite3.Error: If query execution fails.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return _deserialize_row(row)


def get_diagnosis_history(limit: int = 100) -> list[dict[str, Any]]:
    """Fetch diagnosis history in reverse chronological order.

    Args:
        limit: Requested row count; internally clamped to [1, 1000].

    Returns:
        list[dict[str, Any]]: Deserialized diagnosis rows ordered newest first.

    Raises:
        sqlite3.Error: If query fails.
        json.JSONDecodeError: If stored JSON payloads are malformed.
    """
    safe_limit = max(1, min(limit, 1000))
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [_deserialize_row(row) for row in rows]
