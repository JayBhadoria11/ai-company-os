import pytest

from app.core import agent


@pytest.fixture
def mock_analysis(monkeypatch):
    sample_result = {
        "query": "Analyze business performance",
        "financial_report": {
            "total_revenue": 150000,
            "total_expenses": 90000,
            "net_profit": 60000,
        },
        "insights": {
            "executive_summary": "Business is profitable.",
            "key_findings": [
                "Revenue exceeded expenses.",
                "Net profit was positive.",
            ],
            "risks": [
                "Expenses should be monitored.",
            ],
            "recommended_actions": [
                "Review monthly expenses.",
                "Monitor revenue trends.",
            ],
        },
        "model": "NVIDIA Nemotron via Nebius",
    }

    monkeypatch.setattr(
        agent,
        "run_business_analysis",
        lambda query: sample_result,
    )

    return sample_result


def test_analyst_returns_shared_contract(mock_analysis):
    response = agent.run_analyst_task(
        task_id="analyst-001",
        query="Analyze business performance",
    )

    assert response["task_id"] == "analyst-001"
    assert response["agent"] == "analyst"
    assert response["status"] == "success"

    assert isinstance(response["findings"], list)
    assert isinstance(response["metrics"], dict)
    assert isinstance(response["recommendations"], list)


def test_analyst_preserves_financial_metrics(mock_analysis):
    response = agent.run_analyst_task(
        task_id="analyst-002",
        query="Analyze business performance",
    )

    assert response["metrics"] == mock_analysis["financial_report"]


def test_analyst_maps_summary_and_findings(mock_analysis):
    response = agent.run_analyst_task(
        task_id="analyst-003",
        query="Analyze business performance",
    )

    findings = response["findings"]

    assert findings[0]["finding"] == "Business is profitable."
    assert findings[1]["finding"] == "Revenue exceeded expenses."

    for item in findings:
        assert "finding" in item
        assert "evidence" in item


def test_analyst_maps_risks(mock_analysis):
    response = agent.run_analyst_task(
        task_id="analyst-004",
        query="Analyze business performance",
    )

    risk_findings = [
        item["finding"]
        for item in response["findings"]
        if item["finding"].startswith("Risk:")
    ]

    assert "Risk: Expenses should be monitored." in risk_findings


def test_analyst_maps_recommendations(mock_analysis):
    response = agent.run_analyst_task(
        task_id="analyst-005",
        query="Analyze business performance",
    )

    assert response["recommendations"] == [
        "Review monthly expenses.",
        "Monitor revenue trends.",
    ]


def test_analyst_propagates_analysis_failure(monkeypatch):
    def failing_analysis(query):
        raise RuntimeError("Analysis failed")

    monkeypatch.setattr(
        agent,
        "run_business_analysis",
        failing_analysis,
    )

    with pytest.raises(RuntimeError, match="Analysis failed"):
        agent.run_analyst_task(
            task_id="analyst-006",
            query="Analyze business performance",
        )