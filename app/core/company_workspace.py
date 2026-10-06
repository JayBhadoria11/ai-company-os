"""Company Workspace persistence and dataset inspection for AI Company OS.

This module is the single source of truth for the company profile, the active
company dataset(s), and the derived company workspace state. All other modules
(Intelligence, Agents, Financials, Approvals, Command Center) consume the
workspace through :mod:`app.core.company_context`.
"""

import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.database.db import get_connection

WORKSPACE_DIR = Path(__file__).resolve().parents[1] / "data" / "company_workspace"
UPLOAD_DIR = WORKSPACE_DIR / "datasets"
PROFILE_PATH = WORKSPACE_DIR / "company_profile.json"

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_DATASET_BYTES = 100 * 1024 * 1024  # 100 MB

DEFAULT_COMPANY_PROFILE = {
    "name": "",
    "industry": "",
    "description": "",
    "website": "",
    "headquarters": "",
    "stage": "",
    "team_size": "",
    "founded_year": "",
    "currency": "USD",
    "reporting_period": "Monthly",
    "primary_kpi": "Revenue",
    "revenue_target": "",
    "growth_target": "",
}

PROFILE_FIELDS = tuple(DEFAULT_COMPANY_PROFILE.keys())


def initialize_workspace():
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_dataset_table(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS company_datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            metadata TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def load_company_profile():
    """Return the persisted company profile merged over the defaults."""
    initialize_workspace()
    profile = DEFAULT_COMPANY_PROFILE.copy()

    if not PROFILE_PATH.exists():
        return profile

    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return profile

    if isinstance(data, dict):
        for key, value in data.items():
            if key == "updated_at":
                profile[key] = value
            elif key in DEFAULT_COMPANY_PROFILE:
                profile[key] = "" if value is None else value

    return profile


def save_company_profile(profile):
    """Persist the company profile, merging provided fields over the defaults."""
    initialize_workspace()
    current = load_company_profile()

    if isinstance(profile, dict):
        for key, value in profile.items():
            if key in DEFAULT_COMPANY_PROFILE:
                current[key] = "" if value is None else value

    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROFILE_PATH.write_text(
        json.dumps(current, indent=2, default=str),
        encoding="utf-8",
    )
    return current


def _safe_name(name):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name or "")).strip("._")
    return cleaned or "dataset.csv"


def _json_safe(value):
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (ValueError, TypeError):
            return str(value)
    if pd.isna(value):
        return None
    return value


def inspect_dataframe(df):
    numeric = df.select_dtypes(include="number")
    missing = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    numeric_columns = [str(c) for c in numeric.columns]
    date_candidates = [
        str(c)
        for c in df.columns
        if any(token in str(c).lower() for token in ["date", "month", "time", "year"])
    ]

    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "numeric_columns": numeric_columns,
        "categorical_columns": [
            str(c)
            for c in df.select_dtypes(include=["object", "category"]).columns
        ],
        "date_candidates": date_candidates,
        "missing_values": missing,
        "duplicate_rows": duplicate_rows,
        "memory_mb": round(float(df.memory_usage(deep=True).sum()) / 1024 / 1024, 3),
    }


def _read_dataset(path, nrows=None):
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, nrows=nrows)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, nrows=nrows)
    raise ValueError("Only CSV and Excel datasets are supported.")


def save_dataset_bytes(filename, data, replace=True):
    """Persist an uploaded dataset and return its inspected metadata.

    When ``replace`` is true, any previously stored dataset with the same
    filename is replaced so re-uploading a file updates it in place instead of
    creating a duplicate.
    """
    initialize_workspace()

    safe_filename = _safe_name(filename)
    suffix = Path(safe_filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only CSV and Excel datasets are supported.")

    if not data:
        raise ValueError("The uploaded dataset is empty.")

    if len(data) > MAX_DATASET_BYTES:
        raise ValueError("The uploaded dataset is larger than the 100 MB limit.")

    # Parse in memory before touching the persisted file so a bad upload cannot
    # destroy a previously working dataset.
    try:
        if suffix == ".csv":
            frame = pd.read_csv(io.BytesIO(data))
        else:
            frame = pd.read_excel(io.BytesIO(data))
    except Exception as error:
        raise ValueError(f"Could not parse the uploaded dataset: {error}") from error

    if frame.empty or len(frame.columns) == 0:
        raise ValueError("The uploaded dataset does not contain any rows.")

    destination = UPLOAD_DIR / safe_filename
    saved_at = datetime.now(timezone.utc).isoformat()

    info = inspect_dataframe(frame)
    info.update(
        {
            "filename": safe_filename,
            "path": str(destination),
            "saved_at": saved_at,
            "size_bytes": len(data),
        }
    )

    with get_connection() as connection:
        _ensure_dataset_table(connection)

        if replace:
            existing = connection.execute(
                "SELECT id, path FROM company_datasets WHERE filename = ?",
                (safe_filename,),
            ).fetchall()
            for row in existing:
                old_path = row["path"]
                if old_path and Path(old_path) != destination:
                    Path(old_path).unlink(missing_ok=True)
            connection.execute(
                "DELETE FROM company_datasets WHERE filename = ?",
                (safe_filename,),
            )

        destination.write_bytes(data)
        connection.execute(
            "INSERT INTO company_datasets (filename, path, metadata, created_at) "
            "VALUES (?, ?, ?, ?)",
            (
                safe_filename,
                str(destination),
                json.dumps(info, default=str),
                saved_at,
            ),
        )

    return info


def save_dataset(uploaded_file):
    """Persist a Streamlit-style uploaded file object."""
    filename = getattr(uploaded_file, "name", None) or "dataset.csv"
    data = uploaded_file.getvalue()
    return save_dataset_bytes(filename, data)


def list_datasets():
    initialize_workspace()

    with get_connection() as connection:
        _ensure_dataset_table(connection)
        rows = connection.execute(
            "SELECT id, filename, path, metadata, created_at "
            "FROM company_datasets ORDER BY id DESC"
        ).fetchall()

    result = []
    for row in rows:
        try:
            metadata = json.loads(row["metadata"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        result.append(
            {
                "id": row["id"],
                "filename": row["filename"],
                "path": row["path"],
                "created_at": row["created_at"],
                "metadata": metadata,
            }
        )

    return result


def get_active_dataset():
    """Return the most recently uploaded dataset, if any."""
    datasets = list_datasets()
    return datasets[0] if datasets else None


def load_dataset_preview(dataset, limit=8):
    """Return a small, JSON-safe preview of a stored dataset."""
    if not dataset or not dataset.get("path"):
        return None

    path = Path(dataset["path"])
    if not path.exists():
        return None

    try:
        frame = _read_dataset(path, nrows=limit)
    except Exception:
        return None

    rows = []
    for record in frame.to_dict(orient="records"):
        rows.append({key: _json_safe(value) for key, value in record.items()})

    metadata = dataset.get("metadata", {})
    columns = metadata.get("column_names") or [str(c) for c in frame.columns]

    return {
        "filename": dataset.get("filename"),
        "columns": list(columns),
        "rows": rows,
        "preview_rows": len(rows),
        "total_rows": metadata.get("rows"),
    }


def delete_dataset(dataset_id=None):
    """Delete one dataset (by id) or every company dataset."""
    initialize_workspace()

    with get_connection() as connection:
        _ensure_dataset_table(connection)

        if dataset_id is None:
            rows = connection.execute(
                "SELECT id, path FROM company_datasets"
            ).fetchall()
            connection.execute("DELETE FROM company_datasets")
        else:
            rows = connection.execute(
                "SELECT id, path FROM company_datasets WHERE id = ?",
                (dataset_id,),
            ).fetchall()
            connection.execute(
                "DELETE FROM company_datasets WHERE id = ?",
                (dataset_id,),
            )

    for row in rows:
        if row["path"]:
            Path(row["path"]).unlink(missing_ok=True)

    return len(rows)


def clear_workspace():
    """Remove the profile, every dataset file, and dataset metadata."""
    initialize_workspace()

    for file in UPLOAD_DIR.iterdir():
        if file.is_file():
            file.unlink()

    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()

    with get_connection() as connection:
        connection.execute("DROP TABLE IF EXISTS company_datasets")
