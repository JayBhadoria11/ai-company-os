import pytest

from app.core import commander


def test_create_investigation_plan(monkeypatch):
    response = """
    {
        "executive_summary": "Financial performance should be investigated.",
        "required_agents": ["analyst"],
        "investigation_questions": [
            "Is the company profitable?"
        ]
    }
    """

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: response,
    )

    result = commander.create_investigation_plan(
        "Analyze company profitability"
    )

    assert result["required_agents"] == ["analyst"]
    assert result["investigation_questions"]


def test_commander_invalid_json(monkeypatch):
    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: "not valid json",
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        commander.create_investigation_plan(
            "Analyze the company"
        )


def test_commander_unknown_agent(monkeypatch):
    response = """
    {
        "executive_summary": "Investigation required.",
        "required_agents": ["unknown"],
        "investigation_questions": []
    }
    """

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: response,
    )

    with pytest.raises(ValueError, match="unknown agent"):
        commander.create_investigation_plan(
            "Analyze the company"
        )


def test_commander_orchestration(monkeypatch):
    response = """
    {
        "executive_summary": "Analyze financial performance.",
        "required_agents": ["analyst"],
        "investigation_questions": [
            "What is the current financial performance?"
        ]
    }
    """

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: response,
    )

    monkeypatch.setattr(
        commander,
        "run_analyst_task",
        lambda task_id, query: {
            "task_id": task_id,
            "agent": "analyst",
            "status": "success",
            "findings": [
                {
                    "finding": "Business is profitable.",
                    "evidence": {"source": "financial_report"},
                }
            ],
            "metrics": {
                "profit": 4000,
            },
            "recommendations": [
                "Monitor expenses."
            ],
        },
    )

    result = commander.run_commander_task(
        "commander-001",
        "Analyze company profitability",
    )

    assert result["task_id"] == "commander-001"
    assert result["agent"] == "commander"
    assert result["status"] == "success"

    assert result["metrics"]["required_agents"] == ["analyst"]
    assert len(result["metrics"]["agent_responses"]) == 1
    assert result["metrics"]["agent_responses"][0]["agent"] == "analyst"

    assert "Monitor expenses." in result["recommendations"]


def test_commander_response_schema(monkeypatch):
    response = """
    {
        "executive_summary": "Workforce analysis required.",
        "required_agents": ["hr"],
        "investigation_questions": [
            "Are employees overloaded?"
        ]
    }
    """

    monkeypatch.setattr(
        commander,
        "get_completion",
        lambda **kwargs: response,
    )

    monkeypatch.setattr(
        commander,
        "run_hr_operations_task",
        lambda task_id: {
            "task_id": task_id,
            "agent": "hr",
            "status": "success",
            "findings": [],
            "metrics": {},
            "recommendations": [
                "Review workload distribution."
            ],
        },
    )

    result = commander.run_commander_task(
        "commander-002",
        "Analyze workforce workload",
    )

    assert set(result.keys()) == {
        "task_id",
        "agent",
        "status",
        "findings",
        "metrics",
        "recommendations",
    }