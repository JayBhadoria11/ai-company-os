"""Shared memory/context storage for AI Company OS."""

import json

from app.database.db import get_connection, initialize_database


def initialize_memory():
    """Create the shared agent memory table if it does not exist."""

    initialize_database()

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                findings TEXT NOT NULL,
                metrics TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_agent_response(response):
    """Save a standardized AgentResponse into shared memory."""

    required_keys = {
        "task_id",
        "agent",
        "status",
        "findings",
        "metrics",
        "recommendations",
    }

    missing_keys = required_keys - response.keys()

    if missing_keys:
        raise ValueError(
            f"Agent response is missing: {sorted(missing_keys)}"
        )

    initialize_memory()

    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO agent_memory (
                task_id,
                agent,
                status,
                findings,
                metrics,
                recommendations,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                response["task_id"],
                response["agent"],
                response["status"],
                json.dumps(response["findings"], default=str),
                json.dumps(response["metrics"], default=str),
                json.dumps(response["recommendations"], default=str),
                timestamp,
            ),
        )

        return cursor.lastrowid


def get_task_memory(task_id):
    """Return all agent responses stored for a task."""

    initialize_memory()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM agent_memory
            WHERE task_id = ?
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

    memory = []

    for row in rows:
        item = dict(row)

        for key in [
            "findings",
            "metrics",
            "recommendations",
        ]:
            item[key] = json.loads(item[key])

        memory.append(item)

    return memory