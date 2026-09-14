from pathlib import Path

import pytest

from analyst import analyze_revenue, analyze_revenue_as_agent
from backend.schemas.agent import AgentResponse


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "revenue.csv"


def test_analyze_revenue_returns_latest_product_changes():
    result = analyze_revenue(str(DATA_PATH))

    assert result["month"] == "March"
    assert result["previous_month"] == "February"
    assert isinstance(result["products"], list)
    assert len(result["products"]) == 3

    product_c = next(
        product for product in result["products"] if product["product"] == "Product C"
    )

    assert product_c["previous_revenue"] == 108000
    assert product_c["latest_revenue"] == 62000
    assert product_c["change"] == pytest.approx(-0.43)


def test_analyze_revenue_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        analyze_revenue(str(DATA_PATH.with_name("missing.csv")))


def test_analyze_revenue_as_agent_returns_agent_response():
    response = analyze_revenue_as_agent("task_001", str(DATA_PATH))

    assert isinstance(response, AgentResponse)
    assert response.agent == "analyst"
    assert response.status == "completed"
    assert response.task_id == "task_001"
    assert response.findings
    assert response.metrics
    assert response.recommendations


def test_analyze_revenue_as_agent_represents_product_c_decline():
    response = analyze_revenue_as_agent("task_001", str(DATA_PATH))

    product_c = response.metrics["products"]["Product C"]

    assert response.metrics["previous_month"] == "February"
    assert response.metrics["latest_month"] == "March"
    assert product_c["previous_revenue"] == 108000
    assert product_c["latest_revenue"] == 62000
    assert product_c["change"] == pytest.approx(-0.43)
    assert any("Product C" in finding.finding for finding in response.findings)
    assert any("Product C" in recommendation for recommendation in response.recommendations)
