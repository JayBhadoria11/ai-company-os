"""SQLite database for AI Company OS analysis history."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "analysis_history.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                query_text TEXT NOT NULL DEFAULT '',
                tools_used TEXT,
                metrics_calculated TEXT,
                insights TEXT,
                user_approval INTEGER DEFAULT 0,
                model TEXT,
                task_id TEXT,
                result TEXT,
                synthesis TEXT,
                created_at TEXT
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(analysis_history)"
            ).fetchall()
        }

        required_columns = {
            "timestamp": "TEXT",
            "query_text": "TEXT NOT NULL DEFAULT ''",
            "tools_used": "TEXT",
            "metrics_calculated": "TEXT",
            "insights": "TEXT",
            "user_approval": "INTEGER DEFAULT 0",
            "model": "TEXT",
            "task_id": "TEXT",
            "result": "TEXT",
            "synthesis": "TEXT",
            "created_at": "TEXT",
            "context_type": "TEXT DEFAULT 'general'",
        }

        for column_name, column_type in required_columns.items():
            if column_name not in columns:
                connection.execute(
                    f"ALTER TABLE analysis_history ADD COLUMN "
                    f"{column_name} {column_type}"
                )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS intelligence_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                task_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )


def log_analysis(
    query_text,
    metrics_calculated=None,
    insights=None,
    model=None,
    tools_used=None,
    user_approval=0,
    result=None,
    synthesis=None,
    task_id=None,
    context_type="general",
):
    initialize_database()
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO analysis_history (
                timestamp, query_text, tools_used, metrics_calculated,
                insights, user_approval, model, task_id, result,
                synthesis, created_at, context_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                query_text,
                json.dumps(tools_used or [], default=str),
                json.dumps(metrics_calculated or {}, default=str),
                json.dumps(insights or {}, default=str),
                user_approval,
                model,
                task_id,
                json.dumps(result or {}, default=str),
                json.dumps(synthesis or {}, default=str),
                timestamp,
                context_type,
            ),
        )
        return cursor.lastrowid


def _decode(value, fallback=None):
    try:
        return json.loads(value or "{}")
    except (json.JSONDecodeError, TypeError):
        return {} if fallback is None else fallback


def get_recent_analyses(limit=20):
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM analysis_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    analyses = []
    for row in rows:
        item = dict(row)
        for key in ["tools_used", "metrics_calculated", "insights", "result", "synthesis"]:
            item[key] = _decode(item[key])
        analyses.append(item)
    return analyses


def get_latest_investigation():
    analyses = get_recent_analyses(limit=1)
    if not analyses:
        return None

    analysis = analyses[0]
    return {
        "query": analysis.get("query_text", ""),
        "task_id": analysis.get("task_id"),
        "result": analysis.get("result") or {},
        "synthesis": analysis.get("synthesis") or {},
        "timestamp": analysis.get("timestamp"),
    }


def clear_analysis_history():
    initialize_database()
    with get_connection() as connection:
        connection.execute("DELETE FROM analysis_history")


def clear_action_history():
    from app.core.action_engine import initialize_actions
    initialize_actions()
    with get_connection() as connection:
        connection.execute("DELETE FROM action_history")


def clear_approval_history():
    from app.core.approval import initialize_approvals
    initialize_approvals()
    with get_connection() as connection:
        connection.execute("DELETE FROM approval_requests")


def save_intelligence_question(question, task_id=None, status="pending"):
    """Persist an Intelligence question so it survives refreshes/restarts.

    Duplicates are intentionally allowed: each row represents a separate
    investigation event with its own id and timestamp.
    """
    initialize_database()

    clean = str(question or "").strip()
    if not clean:
        raise ValueError("question must be a non-empty string.")

    timestamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO intelligence_questions (question, task_id, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (clean, task_id, status, timestamp),
        )
        return cursor.lastrowid


def update_intelligence_question_status(question_id, status):
    """Update the investigation status for a persisted question."""
    if question_id is None:
        return

    initialize_database()
    with get_connection() as connection:
        connection.execute(
            "UPDATE intelligence_questions SET status = ? WHERE id = ?",
            (status, question_id),
        )


def get_intelligence_questions(limit=50):
    """Return persisted Intelligence questions, newest first."""
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, question, task_id, status, created_at
            FROM intelligence_questions
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 200)),),
        ).fetchall()

    return [dict(row) for row in rows]


def clear_intelligence_questions():
    """Remove all persisted Intelligence/Past Questions."""
    initialize_database()
    with get_connection() as connection:
        connection.execute("DELETE FROM intelligence_questions")


def delete_intelligence_question(question_id):
    """Delete a single persisted Intelligence question.

    Returns True when a row was removed, False when the id did not exist.
    """
    initialize_database()
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM intelligence_questions WHERE id = ?",
            (question_id,),
        )
        return cursor.rowcount > 0


def clear_company_workspace_state():
    """Clear company profile, datasets, and all derived company OS state."""
    from app.core.company_workspace import clear_workspace
    clear_workspace()
    initialize_database()
    with get_connection() as connection:
        connection.execute("DELETE FROM analysis_history WHERE context_type = 'company'")
    try:
        clear_action_history()
        clear_approval_history()
    except Exception:
        pass
    try:
        clear_intelligence_questions()
    except Exception:
        pass


def clear_all_os_state():
    """Factory reset the OS state, including company workspace and derived state."""
    clear_analysis_history()
    clear_action_history()
    clear_approval_history()
    clear_intelligence_questions()
    from app.core.company_workspace import clear_workspace
    clear_workspace()
