from pathlib import Path

import pytest

from backend.schemas.agent import AgentResponse
from finance import analyze_finances, analyze_finances_as_agent


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "expenses.csv"


def test_analyze_finances_returns_basic_expense_analysis():
    result = analyze_finances(str(DATA_PATH))

    assert result["month"] == "March"
    assert result["previous_month"] == "February"
    assert isinstance(result["categories"], list)
    assert len(result["categories"]) == 3


def test_analyze_finances_calculates_total_expenses():
    result = analyze_finances(str(DATA_PATH))

    assert result["previous_total_expenses"] == 207000
    assert result["latest_total_expenses"] == 225000


def test_analyze_finances_calculates_expense_change():
    result = analyze_finances(str(DATA_PATH))

    assert result["expense_change"] == 18000
    assert result["expense_change_percent"] == pytest.approx(0.09)


def test_analyze_finances_calculates_category_changes():
    result = analyze_finances(str(DATA_PATH))
    categories = {
        category["category"]: category for category in result["categories"]
    }

    assert categories["Salaries"]["amount_change"] == 0
    assert categories["Salaries"]["change"] == pytest.approx(0.0)
    assert categories["Marketing"]["previous_amount"] == 55000
    assert categories["Marketing"]["latest_amount"] == 70000
    assert categories["Marketing"]["amount_change"] == 15000
    assert categories["Marketing"]["change"] == pytest.approx(0.27)
    assert categories["Infrastructure"]["amount_change"] == 3000


def test_analyze_finances_identifies_largest_category_increase():
    result = analyze_finances(str(DATA_PATH))

    assert result["largest_category_increase"]["category"] == "Marketing"
    assert result["largest_category_increase"]["amount_change"] == 15000


def test_analyze_finances_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        analyze_finances(str(DATA_PATH.with_name("missing.csv")))


def test_analyze_finances_rejects_missing_required_columns(tmp_path):
    invalid_file = tmp_path / "expenses.csv"
    invalid_file.write_text("month,category\nMarch,Marketing\n")

    with pytest.raises(ValueError, match="amount"):
        analyze_finances(str(invalid_file))


def test_analyze_finances_rejects_empty_data(tmp_path):
    empty_file = tmp_path / "expenses.csv"
    empty_file.write_text("month,category,amount\n")

    with pytest.raises(ValueError, match="does not contain any rows"):
        analyze_finances(str(empty_file))


def test_analyze_finances_as_agent_returns_agent_response():
    response = analyze_finances_as_agent("task_002", str(DATA_PATH))

    assert isinstance(response, AgentResponse)
    assert response.agent == "finance"
    assert response.status == "completed"
    assert response.task_id == "task_002"
    assert response.findings
    assert response.metrics
    assert response.recommendations


def test_analyze_finances_as_agent_preserves_finance_metrics():
    response = analyze_finances_as_agent("task_002", str(DATA_PATH))

    assert response.metrics["previous_total_expenses"] == 207000
    assert response.metrics["latest_total_expenses"] == 225000
    assert response.metrics["expense_change"] == 18000
    assert response.metrics["categories"]["Marketing"]["amount_change"] == 15000
    assert response.metrics["largest_category_increase"]["category"] == "Marketing"
