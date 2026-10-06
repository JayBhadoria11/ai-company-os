import pandas as pd
import pytest

from app.tools import hr_operations


@pytest.fixture
def sample_employee_data():
    return pd.DataFrame(
        {
            "employee_id": ["E001", "E002", "E003"],
            "department": ["Engineering", "Operations", "HR"],
            "role": ["Developer", "Manager", "HR Specialist"],
            "capacity_hours": [40, 40, 40],
            "assigned_hours": [36, 44, 28],
            "completed_tasks": [8, 6, 12],
            "pending_tasks": [2, 6, 1],
        }
    )


def test_hr_operations_metrics_calculation(
    monkeypatch, tmp_path, sample_employee_data
):
    file_path = tmp_path / "employees.csv"
    sample_employee_data.to_csv(file_path, index=False)

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    result = hr_operations.calculate_hr_operations_metrics()

    assert result["summary"]["employee_count"] == 3
    assert result["summary"]["total_capacity_hours"] == 120
    assert result["summary"]["total_assigned_hours"] == 108
    assert result["summary"]["total_completed_tasks"] == 26
    assert result["summary"]["total_pending_tasks"] == 9

    assert result["summary"]["overall_utilization_rate"] == pytest.approx(0.9)

    overloaded_ids = [
        employee["employee_id"]
        for employee in result["overloaded_employees"]
    ]
    assert overloaded_ids == ["E002"]

    underutilized_ids = [
        employee["employee_id"]
        for employee in result["underutilized_employees"]
    ]
    assert underutilized_ids == ["E003"]


def test_department_metrics(monkeypatch, tmp_path, sample_employee_data):
    file_path = tmp_path / "employees.csv"
    sample_employee_data.to_csv(file_path, index=False)

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    result = hr_operations.calculate_hr_operations_metrics()

    engineering = result["department_metrics"]["Engineering"]
    operations = result["department_metrics"]["Operations"]

    assert engineering["capacity_hours"] == 40
    assert engineering["assigned_hours"] == 36
    assert engineering["utilization_rate"] == pytest.approx(0.9)

    assert operations["assigned_hours"] == 44
    assert operations["utilization_rate"] == pytest.approx(1.1)
    assert operations["pending_tasks"] == 6


def test_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        hr_operations,
        "DATA_PATH",
        tmp_path / "missing.csv",
    )

    with pytest.raises(FileNotFoundError):
        hr_operations.calculate_hr_operations_metrics()


def test_empty_csv(monkeypatch, tmp_path):
    file_path = tmp_path / "employees.csv"
    file_path.write_text(
        "employee_id,department,role,capacity_hours,assigned_hours,"
        "completed_tasks,pending_tasks\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    with pytest.raises(ValueError, match="empty"):
        hr_operations.calculate_hr_operations_metrics()


def test_missing_columns(monkeypatch, tmp_path):
    file_path = tmp_path / "employees.csv"

    pd.DataFrame(
        {
            "employee_id": ["E001"],
            "department": ["Engineering"],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    with pytest.raises(ValueError, match="Missing required columns"):
        hr_operations.calculate_hr_operations_metrics()


def test_invalid_numeric_data(monkeypatch, tmp_path):
    file_path = tmp_path / "employees.csv"

    pd.DataFrame(
        {
            "employee_id": ["E001"],
            "department": ["Engineering"],
            "role": ["Developer"],
            "capacity_hours": ["invalid"],
            "assigned_hours": [30],
            "completed_tasks": [5],
            "pending_tasks": [2],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    with pytest.raises(ValueError):
        hr_operations.calculate_hr_operations_metrics()


def test_zero_total_capacity(monkeypatch, tmp_path):
    file_path = tmp_path / "employees.csv"

    pd.DataFrame(
        {
            "employee_id": ["E001"],
            "department": ["Engineering"],
            "role": ["Developer"],
            "capacity_hours": [0],
            "assigned_hours": [0],
            "completed_tasks": [0],
            "pending_tasks": [0],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(hr_operations, "DATA_PATH", file_path)

    result = hr_operations.calculate_hr_operations_metrics()

    assert result["summary"]["overall_utilization_rate"] is None
    assert result["department_metrics"]["Engineering"]["utilization_rate"] is None
