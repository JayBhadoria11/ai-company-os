"""Approval-gated action execution engine for AI Company OS."""

from app.core.approval import get_approval
from app.database.db import get_connection, initialize_database

ACTION_STATUSES = {
    "pending_approval",
    "executed",
    "rejected",
}


def initialize_actions():
    initialize_database()
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def request_action(task_id, action):
    """Create one logical pending action; don't duplicate an existing lifecycle."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string.")
    if not action or not isinstance(action, str):
        raise ValueError("action must be a non-empty string.")

    initialize_actions()

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT *
            FROM action_history
            WHERE task_id = ? AND action = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (task_id, action),
        ).fetchone()

        if existing is not None and existing["status"] in {"pending_approval", "executed"}:
            return existing["id"]

        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        cursor = connection.execute(
            """
            INSERT INTO action_history (
                task_id, action, status, result, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                task_id,
                action,
                "pending_approval",
                "Action recorded and awaiting human approval.",
                timestamp,
            ),
        )
        return cursor.lastrowid


def execute_action(task_id, action):
    """Transition the existing action from pending to executed."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string.")
    if not action or not isinstance(action, str):
        raise ValueError("action must be a non-empty string.")

    approval = get_approval(task_id)
    if approval is None:
        raise ValueError("No approval request exists for this task.")
    if approval["status"] == "pending":
        raise ValueError("Action cannot execute because approval is still pending.")
    if approval["status"] == "rejected":
        raise ValueError("Action cannot execute because the request was rejected.")
    if approval["status"] != "approved":
        raise ValueError("Action cannot execute because approval is invalid.")

    initialize_actions()

    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    result = f"SIMULATED EXECUTION: {action}"

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT *
            FROM action_history
            WHERE task_id = ? AND action = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (task_id, action),
        ).fetchone()

        if existing is not None:
            if existing["status"] == "executed":
                return {
                    "action_id": existing["id"],
                    "task_id": task_id,
                    "action": action,
                    "status": "executed",
                    "result": existing["result"],
                }

            if existing["status"] == "rejected":
                raise ValueError("This action was rejected and cannot execute.")

            connection.execute(
                """
                UPDATE action_history
                SET status = ?, result = ?, created_at = ?
                WHERE id = ?
                """,
                ("executed", result, timestamp, existing["id"]),
            )
            action_id = existing["id"]
        else:
            cursor = connection.execute(
                """
                INSERT INTO action_history (
                    task_id, action, status, result, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, action, "executed", result, timestamp),
            )
            action_id = cursor.lastrowid

    return {
        "action_id": action_id,
        "task_id": task_id,
        "action": action,
        "status": "executed",
        "result": result,
    }


def get_task_actions(task_id):
    """Return one current lifecycle record per logical action."""
    initialize_actions()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM action_history
            WHERE task_id = ?
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

    latest = {}
    for row in rows:
        latest[row["action"]] = dict(row)

    return list(latest.values())
