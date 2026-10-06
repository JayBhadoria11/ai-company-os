import json

from app.core import marketing_agent


VALID_RESPONSE = {
    "executive_summary": "Campaign C has the highest conversion rate.",
    "key_findings": [
        "Campaign C has a 12.5% conversion rate.",
        "Campaign A has a 5% CTR.",
    ],
    "risks": [
        "Campaign D has no clicks.",
    ],
    "recommended_actions": [
        "Investigate Campaign D.",
        "Review Campaign C's strategy.",
    ],
}


def test_marketing_agent_success(monkeypatch):
    monkeypatch.setattr(
        marketing_agent,
        "calculate_marketing_metrics",
        lambda: [
            {
                "campaign": "A",
                "ctr_pct": 5.0,
                "conversion_rate_pct": 10.0,
                "cost_per_conversion": 50.0,
            }
        ],
    )

    monkeypatch.setattr(
        marketing_agent,
        "get_completion",
        lambda **kwargs: json.dumps(VALID_RESPONSE),
    )

    result = marketing_agent.run_marketing_task("task-001")

    assert result["task_id"] == "task-001"
    assert result["agent"] == "marketing"
    assert result["status"] == "success"
    assert len(result["findings"]) == 4
    assert len(result["recommendations"]) == 2
    assert "campaigns" in result["metrics"]


def test_marketing_agent_model_failure(monkeypatch):
    monkeypatch.setattr(
        marketing_agent,
        "calculate_marketing_metrics",
        lambda: [
            {
                "campaign": "A",
                "ctr_pct": 5.0,
                "conversion_rate_pct": 10.0,
                "cost_per_conversion": 50.0,
            }
        ],
    )

    def raise_error(**kwargs):
        raise RuntimeError("Model unavailable")

    monkeypatch.setattr(
        marketing_agent,
        "get_completion",
        raise_error,
    )

    result = marketing_agent.run_marketing_task("task-002")

    assert result["status"] == "partial"
    assert result["agent"] == "marketing"
    assert result["metrics"]["campaigns"][0]["campaign"] == "A"
    assert result["recommendations"] == []


def test_marketing_agent_invalid_json(monkeypatch):
    monkeypatch.setattr(
        marketing_agent,
        "calculate_marketing_metrics",
        lambda: [],
    )

    monkeypatch.setattr(
        marketing_agent,
        "get_completion",
        lambda **kwargs: "This is not JSON",
    )

    result = marketing_agent.run_marketing_task("task-003")

    assert result["status"] == "partial"
    assert result["agent"] == "marketing"


def test_marketing_agent_invalid_data(monkeypatch):
    def raise_error():
        raise FileNotFoundError("Marketing data unavailable")

    monkeypatch.setattr(
        marketing_agent,
        "calculate_marketing_metrics",
        raise_error,
    )

    result = marketing_agent.run_marketing_task("task-004")

    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["metrics"] == {}
    assert result["recommendations"] == []