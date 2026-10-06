import pytest

from app.core import synthesis


def test_synthesis_success(monkeypatch):
    response = """
    {
        "executive_summary": "The company is profitable but should monitor expenses.",
        "key_insights": [
            "Revenue is growing.",
            "Expenses require monitoring."
        ],
        "risks": [
            "Expense growth could reduce margins."
        ],
        "recommended_actions": [
            "Review major expense categories."
        ]
    }
    """

    monkeypatch.setattr(
        synthesis,
        "get_completion",
        lambda **kwargs: response,
    )

    agent_responses = [
        {
            "task_id": "task-001-analyst",
            "agent": "analyst",
            "status": "success",
            "findings": [
                {
                    "finding": "Revenue is growing.",
                    "evidence": {"source": "financial_report"},
                }
            ],
            "metrics": {
                "total_profit": 4000,
            },
            "recommendations": [
                "Monitor expenses."
            ],
        }
    ]

    result = synthesis.synthesize_agent_responses(
        agent_responses
    )

    assert result["executive_summary"]
    assert len(result["key_insights"]) == 2
    assert len(result["risks"]) == 1
    assert len(result["recommended_actions"]) == 1


def test_synthesis_invalid_json(monkeypatch):
    monkeypatch.setattr(
        synthesis,
        "get_completion",
        lambda **kwargs: "not valid json",
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        synthesis.synthesize_agent_responses([])


def test_synthesis_missing_field(monkeypatch):
    response = """
    {
        "executive_summary": "Summary",
        "key_insights": [],
        "risks": []
    }
    """

    monkeypatch.setattr(
        synthesis,
        "get_completion",
        lambda **kwargs: response,
    )

    with pytest.raises(ValueError, match="recommended_actions"):
        synthesis.synthesize_agent_responses([])


def test_synthesis_wrong_list_type(monkeypatch):
    response = """
    {
        "executive_summary": "Summary",
        "key_insights": "not a list",
        "risks": [],
        "recommended_actions": []
    }
    """

    monkeypatch.setattr(
        synthesis,
        "get_completion",
        lambda **kwargs: response,
    )

    with pytest.raises(ValueError, match="key_insights"):
        synthesis.synthesize_agent_responses([])