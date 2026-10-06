"""Human approval system for AI Company OS."""

from app.database.db import get_connection, initialize_database

APPROVAL_STATES = {"pending", "approved", "rejected"}


def initialize_approvals():
    initialize_database()
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def create_approval_request(task_id, summary):
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string.")
    if not summary or not isinstance(summary, str):
        raise ValueError("summary must be a non-empty string.")

    initialize_approvals()
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id FROM approval_requests WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        if existing:
            connection.execute(
                """
                UPDATE approval_requests
                SET summary = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (summary, timestamp, task_id),
            )
            return existing["id"]

        cursor = connection.execute(
            """
            INSERT INTO approval_requests (
                task_id, status, summary, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, "pending", summary, timestamp, timestamp),
        )
        return cursor.lastrowid


def get_approval(task_id):
    initialize_approvals()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM approval_requests WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def update_approval(task_id, status):
    if status not in {"approved", "rejected"}:
        raise ValueError("Approval status must be 'approved' or 'rejected'.")

    initialize_approvals()
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE approval_requests
            SET status = ?, updated_at = ?
            WHERE task_id = ? AND status = 'pending'
            """,
            (status, timestamp, task_id),
        )
        if cursor.rowcount == 0:
            raise ValueError(
                "Approval request does not exist or is no longer pending."
            )

    return get_approval(task_id)
