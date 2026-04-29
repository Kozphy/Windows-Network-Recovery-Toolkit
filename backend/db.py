import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).with_name("toolkit.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        conn.commit()


def insert_diagnosis(record: dict[str, Any]) -> int:
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
    item = dict(row)
    item["user_proxy_enabled"] = bool(item["user_proxy_enabled"])
    item["recent_processes"] = json.loads(item["recent_processes"]) if item["recent_processes"] else []
    return item


def get_latest_diagnosis() -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    return _deserialize_row(row)


def get_diagnosis_history(limit: int = 100) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 1000))
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM diagnosis_records ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [_deserialize_row(row) for row in rows]
