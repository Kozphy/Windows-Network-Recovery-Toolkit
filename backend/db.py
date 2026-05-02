"""SQLite persistence for SaaS diagnosis, metering, subscriptions, and projects.

Defines `get_connection`, `init_db` (DDL from ``schema.sql``), and helpers consumed
by ``backend.main``: multi-tenant users/orgs/projects, ``diagnosis_logs``,
``connection_metrics``, subscriptions, and usage counters.

Failure modes:
    ``init_db`` may raise ``sqlite3.Error`` when schema SQL cannot execute.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).with_name("toolkit.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
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


def month_key(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m")


def ensure_user_org_project(user_id: str, email: str) -> None:
    """Ensure a user row exists and owns one org with a default project and subscription."""
    with get_connection() as conn:
        existing = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if existing is None:
            conn.execute("INSERT INTO users (id, email) VALUES (?, ?)", (user_id, email))
        elif existing["email"] != email:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))

        org = conn.execute(
            "SELECT id FROM organizations WHERE owner_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if org is None:
            org_id = str(uuid.uuid4())
            proj_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO organizations (id, name, owner_id) VALUES (?, ?, ?)",
                (org_id, f"Org-{org_id[:8]}", user_id),
            )
            conn.execute(
                "INSERT INTO projects (id, org_id, name) VALUES (?, ?, ?)",
                (proj_id, org_id, "Default Project"),
            )
            conn.execute(
                "INSERT INTO subscriptions (org_id, plan, status) VALUES (?, ?, ?)",
                (org_id, "free", "active"),
            )
        conn.commit()


def get_project_for_user(user_id: str, requested_project_id: Optional[str]) -> Optional[dict[str, Any]]:
    """Return `{project_id, org_id, name}` for owner, optionally scoped by project id."""
    with get_connection() as conn:
        if requested_project_id:
            row = conn.execute(
                """
                SELECT p.id AS project_id, p.org_id, p.name
                FROM projects p
                INNER JOIN organizations o ON o.id = p.org_id
                WHERE o.owner_id = ? AND p.id = ?
                """,
                (user_id, requested_project_id),
            ).fetchone()
            return dict(row) if row else None

        row = conn.execute(
            """
            SELECT p.id AS project_id, p.org_id, p.name
            FROM projects p
            INNER JOIN organizations o ON o.id = p.org_id
            WHERE o.owner_id = ?
            ORDER BY p.name
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def get_subscription(org_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT org_id, plan, status, stripe_customer_id, stripe_subscription_id
            FROM subscriptions WHERE org_id = ?
            """,
            (org_id,),
        ).fetchone()
    if not row:
        return {"plan": "free", "status": "active", "org_id": org_id}
    return dict(row)


def update_subscription(
    org_id: str,
    plan: str,
    status: str,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (org_id, plan, status, stripe_customer_id, stripe_subscription_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                plan = excluded.plan,
                status = excluded.status,
                stripe_customer_id = COALESCE(
                    excluded.stripe_customer_id, subscriptions.stripe_customer_id),
                stripe_subscription_id = COALESCE(
                    excluded.stripe_subscription_id, subscriptions.stripe_subscription_id)
            """,
            (org_id, plan, status, stripe_customer_id, stripe_subscription_id),
        )
        conn.commit()


def get_usage(org_id: str, month: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT org_id, month, diagnosis_count FROM usage WHERE org_id = ? AND month = ?",
            (org_id, month),
        ).fetchone()
    if row:
        return {"org_id": row["org_id"], "month": row["month"], "diagnosis_count": int(row["diagnosis_count"])}
    return {"org_id": org_id, "month": month, "diagnosis_count": 0}


def try_increment_usage_with_limit(org_id: str, limit: int, month: str) -> Optional[int]:
    """Return new diagnosis_count after increment, or None when plan limit is reached."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT diagnosis_count FROM usage WHERE org_id = ? AND month = ?",
            (org_id, month),
        ).fetchone()
        current = int(row["diagnosis_count"]) if row else 0
        if limit != -1 and current >= limit:
            conn.rollback()
            return None
        conn.execute(
            """
            INSERT INTO usage (org_id, month, diagnosis_count)
            VALUES (?, ?, 1)
            ON CONFLICT(org_id, month) DO UPDATE SET
                diagnosis_count = diagnosis_count + 1
            """,
            (org_id, month),
        )
        row2 = conn.execute(
            "SELECT diagnosis_count FROM usage WHERE org_id = ? AND month = ?",
            (org_id, month),
        ).fetchone()
        conn.commit()
        return int(row2["diagnosis_count"]) if row2 else None


def insert_diagnosis(*, project_id: str, input_data: dict[str, Any], result: dict[str, Any]) -> int:
    created = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO diagnosis_logs (project_id, input_data, result, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, json.dumps(input_data), json.dumps(result), created),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_metric(*, project_id: str, time_wait: int, established: int) -> int:
    created = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO connection_metrics (project_id, time_wait, established, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, time_wait, established, created),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_recent_metrics(project_id: str, limit: int) -> list[dict[str, Any]]:
    safe = max(1, min(limit, 100))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT time_wait, established, created_at
            FROM connection_metrics
            WHERE project_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (project_id, safe),
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["timestamp"] = item.pop("created_at")
        out.append(item)
    return out


def get_history(
    org_id: str,
    project_id: Optional[str],
    limit: int,
) -> dict[str, Any]:
    safe = max(1, min(limit, 500))

    diag_sql = """
        SELECT dl.id, dl.project_id, dl.input_data, dl.result, dl.created_at
        FROM diagnosis_logs dl
        INNER JOIN projects p ON p.id = dl.project_id
        WHERE p.org_id = ?
    """
    met_sql = """
        SELECT cm.id, cm.project_id, cm.time_wait, cm.established, cm.created_at
        FROM connection_metrics cm
        INNER JOIN projects p ON p.id = cm.project_id
        WHERE p.org_id = ?
    """
    diag_params: list[Any] = [org_id]
    met_params: list[Any] = [org_id]
    if project_id:
        diag_sql += " AND dl.project_id = ?"
        met_sql += " AND cm.project_id = ?"
        diag_params.append(project_id)
        met_params.append(project_id)

    diag_sql += " ORDER BY dl.id DESC LIMIT ?"
    met_sql += " ORDER BY cm.id DESC LIMIT ?"
    diag_params.append(safe)
    met_params.append(safe)

    with get_connection() as conn:
        drows = conn.execute(diag_sql, diag_params).fetchall()
        mrows = conn.execute(met_sql, met_params).fetchall()

    diagnoses: list[dict[str, Any]] = []
    for r in drows:
        diagnoses.append(
            {
                "id": r["id"],
                "project_id": r["project_id"],
                "input": json.loads(r["input_data"]),
                "result": json.loads(r["result"]),
                "created_at": r["created_at"],
            }
        )
    metrics_out: list[dict[str, Any]] = []
    for r in mrows:
        metrics_out.append(
            {
                "id": r["id"],
                "project_id": r["project_id"],
                "time_wait": r["time_wait"],
                "established": r["established"],
                "timestamp": r["created_at"],
            }
        )

    return {"diagnoses": diagnoses, "metrics": metrics_out}
