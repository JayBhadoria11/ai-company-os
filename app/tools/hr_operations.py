"""Deterministic HR and Operations analytics."""

from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "employees.csv"


REQUIRED_COLUMNS = {
    "employee_id",
    "department",
    "role",
    "capacity_hours",
    "assigned_hours",
    "completed_tasks",
    "pending_tasks",
}


def calculate_hr_operations_metrics():
    """Calculate workload, capacity, staffing, and bottleneck metrics."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Employee data file not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    if df.empty:
        raise ValueError("Employee data is empty.")

    missing_columns = REQUIRED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    numeric_columns = [
        "capacity_hours",
        "assigned_hours",
        "completed_tasks",
        "pending_tasks",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    total_capacity = float(df["capacity_hours"].sum())
    total_assigned = float(df["assigned_hours"].sum())
    total_completed = int(df["completed_tasks"].sum())
    total_pending = int(df["pending_tasks"].sum())

    utilization_rate = (
        total_assigned / total_capacity
        if total_capacity > 0
        else None
    )

    df["utilization_rate"] = (
        df["assigned_hours"] / df["capacity_hours"]
    )

    overloaded = df[df["assigned_hours"] > df["capacity_hours"]]
    underutilized = df[df["utilization_rate"] < 0.75]

    department_metrics = {}

    for department, group in df.groupby("department"):
        capacity = float(group["capacity_hours"].sum())
        assigned = float(group["assigned_hours"].sum())

        department_metrics[department] = {
            "capacity_hours": capacity,
            "assigned_hours": assigned,
            "utilization_rate": (
                assigned / capacity
                if capacity > 0
                else None
            ),
            "pending_tasks": int(group["pending_tasks"].sum()),
        }

    return {
        "summary": {
            "employee_count": int(len(df)),
            "total_capacity_hours": total_capacity,
            "total_assigned_hours": total_assigned,
            "total_completed_tasks": total_completed,
            "total_pending_tasks": total_pending,
            "overall_utilization_rate": utilization_rate,
        },
        "overloaded_employees": overloaded[
            [
                "employee_id",
                "department",
                "role",
                "capacity_hours",
                "assigned_hours",
                "utilization_rate",
                "pending_tasks",
            ]
        ].to_dict(orient="records"),
        "underutilized_employees": underutilized[
            [
                "employee_id",
                "department",
                "role",
                "capacity_hours",
                "assigned_hours",
                "utilization_rate",
            ]
        ].to_dict(orient="records"),
        "department_metrics": department_metrics,
    }