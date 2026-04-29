import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).with_name("toolkit.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        conn.commit()


def ensure_user_org_project(user_id: str, email: str, project_name: str = "Default Project") -> dict[str, str]:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id, email) VALUES (?, ?)",
            (user_id, email),
        )
        row = conn.execute(
            "SELECT id FROM organizations WHERE owner_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            org_id = row["id"]
        else:
            org_id = f"org_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO organizations (id, name, owner_id) VALUES (?, ?, ?)",
                (org_id, "My Organization", user_id),
            )
            conn.execute(
                "INSERT OR IGNORE INTO subscriptions (org_id, plan, status) VALUES (?, 'free', 'active')",
                (org_id,),
            )

        prow = conn.execute(
            "SELECT id FROM projects WHERE org_id = ? ORDER BY id LIMIT 1",
            (org_id,),
        ).fetchone()
        if prow:
            project_id = prow["id"]
        else:
            project_id = f"proj_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO projects (id, org_id, name) VALUES (?, ?, ?)",
                (project_id, org_id, project_name),
            )
        conn.commit()
    return {"org_id": org_id, "project_id": project_id}


def get_project_for_user(user_id: str, project_id: Optional[str]) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        if project_id:
            row = conn.execute(
                """
                SELECT p.id AS project_id, p.org_id
                FROM projects p
                JOIN organizations o ON o.id = p.org_id
                WHERE p.id = ? AND o.owner_id = ?
                """,
                (project_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT p.id AS project_id, p.org_id
                FROM projects p
                JOIN organizations o ON o.id = p.org_id
                WHERE o.owner_id = ?
                ORDER BY p.id
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
    return dict(row) if row else None


def insert_diagnosis(project_id: str, input_data: dict[str, Any], result: dict[str, Any]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO diagnosis_logs (project_id, input_data, result) VALUES (?, ?, ?)",
            (project_id, json.dumps(input_data), json.dumps(result)),
        )
        conn.commit()
        return int(cur.lastrowid)


def insert_metric(project_id: str, time_wait: int, established: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO connection_metrics (project_id, time_wait, established) VALUES (?, ?, ?)",
            (project_id, time_wait, established),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_recent_metrics(project_id: str, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at AS timestamp, time_wait, established
            FROM connection_metrics
            WHERE project_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_history(org_id: str, project_id: Optional[str] = None, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
    with get_connection() as conn:
        if project_id:
            diag_rows = conn.execute(
                """
                SELECT d.id, d.created_at AS timestamp, d.input_data, d.result
                FROM diagnosis_logs d
                JOIN projects p ON p.id = d.project_id
                WHERE p.org_id = ? AND d.project_id = ?
                ORDER BY d.id DESC
                LIMIT ?
                """,
                (org_id, project_id, limit),
            ).fetchall()
            metric_rows = conn.execute(
                """
                SELECT m.id, m.created_at AS timestamp, m.time_wait, m.established
                FROM connection_metrics m
                JOIN projects p ON p.id = m.project_id
                WHERE p.org_id = ? AND m.project_id = ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (org_id, project_id, limit),
            ).fetchall()
        else:
            diag_rows = conn.execute(
                """
                SELECT d.id, d.created_at AS timestamp, d.input_data, d.result
                FROM diagnosis_logs d
                JOIN projects p ON p.id = d.project_id
                WHERE p.org_id = ?
                ORDER BY d.id DESC
                LIMIT ?
                """,
                (org_id, limit),
            ).fetchall()
            metric_rows = conn.execute(
                """
                SELECT m.id, m.created_at AS timestamp, m.time_wait, m.established
                FROM connection_metrics m
                JOIN projects p ON p.id = m.project_id
                WHERE p.org_id = ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (org_id, limit),
            ).fetchall()

    diagnosis_logs: list[dict[str, Any]] = []
    for row in diag_rows:
        item = dict(row)
        item["input_data"] = json.loads(item["input_data"])
        item["result"] = json.loads(item["result"])
        diagnosis_logs.append(item)
    return {
        "diagnosis_logs": diagnosis_logs,
        "connection_metrics": [dict(row) for row in metric_rows],
    }


def get_subscription(org_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM subscriptions WHERE org_id = ? LIMIT 1",
            (org_id,),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO subscriptions (org_id, plan, status) VALUES (?, 'free', 'active')",
                (org_id,),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM subscriptions WHERE org_id = ? LIMIT 1",
                (org_id,),
            ).fetchone()
    return dict(row)


def update_subscription(
    org_id: str,
    plan: str,
    status: str,
    stripe_customer_id: Optional[str],
    stripe_subscription_id: Optional[str],
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (org_id, plan, status, stripe_customer_id, stripe_subscription_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(org_id) DO UPDATE SET
                plan=excluded.plan,
                status=excluded.status,
                stripe_customer_id=excluded.stripe_customer_id,
                stripe_subscription_id=excluded.stripe_subscription_id
            """,
            (org_id, plan, status, stripe_customer_id, stripe_subscription_id),
        )
        conn.commit()


def month_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.utcnow()
    return f"{d.year:04d}-{d.month:02d}"


def get_usage(org_id: str, month: Optional[str] = None) -> dict[str, Any]:
    m = month or month_key()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usage WHERE org_id = ? AND month = ?",
            (org_id, m),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO usage (org_id, month, diagnosis_count) VALUES (?, ?, 0)",
                (org_id, m),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM usage WHERE org_id = ? AND month = ?",
                (org_id, m),
            ).fetchone()
    return dict(row)


def increment_usage(org_id: str, month: Optional[str] = None) -> int:
    m = month or month_key()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO usage (org_id, month, diagnosis_count)
            VALUES (?, ?, 1)
            ON CONFLICT(org_id, month) DO UPDATE SET
                diagnosis_count = diagnosis_count + 1
            """,
            (org_id, m),
        )
        conn.commit()
        row = conn.execute(
            "SELECT diagnosis_count FROM usage WHERE org_id = ? AND month = ?",
            (org_id, m),
        ).fetchone()
    return int(row["diagnosis_count"])
