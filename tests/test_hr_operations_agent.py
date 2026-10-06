import pytest

from app.core import hr_operations_agent


def test_hr_operations_agent_success(monkeypatch):
    monkeypatch.setattr(
        hr_operations_agent,
        "get_completion",
        lambda **kwargs: """
        {
            "executive_summary": "Workforce utilization is high.",
            "key_findings": [
                "Two employees are overloaded."
            ],
            "risks": [
                "Workload imbalance may delay tasks."
            ],
            "recommended_actions": [
                "Reassign pending tasks."
            ]
        }
        """,
    )

    result = hr_operations_agent.run_hr_operations_task("hr-agent-001")

    assert result["task_id"] == "hr-agent-001"
    assert result["agent"] == "hr"
    assert result["status"] == "success"

    assert isinstance(result["findings"], list)
    assert isinstance(result["metrics"], dict)
    assert isinstance(result["recommendations"], list)

    assert len(result["findings"]) > 0
    assert len(result["recommendations"]) > 0


def test_hr_operations_agent_invalid_json(monkeypatch):
    monkeypatch.setattr(
        hr_operations_agent,
        "get_completion",
        lambda **kwargs: "not valid json",
    )

    result = hr_operations_agent.run_hr_operations_task("hr-agent-002")

    assert result["task_id"] == "hr-agent-002"
    assert result["agent"] == "hr"
    assert result["status"] == "partial"

    assert result["metrics"]
    assert result["findings"]
    assert result["recommendations"] == []


def test_hr_operations_agent_nvidia_failure(monkeypatch):
    def fail_completion(**kwargs):
        raise RuntimeError("Nemotron unavailable")

    monkeypatch.setattr(
        hr_operations_agent,
        "get_completion",
        fail_completion,
    )

    result = hr_operations_agent.run_hr_operations_task("hr-agent-003")

    assert result["status"] == "partial"
    assert result["agent"] == "hr"
    assert result["metrics"]
    assert result["findings"]


def test_hr_operations_agent_calculation_failure(monkeypatch):
    def fail_metrics():
        raise RuntimeError("HR data unavailable")

    monkeypatch.setattr(
        hr_operations_agent,
        "calculate_hr_operations_metrics",
        fail_metrics,
    )

    result = hr_operations_agent.run_hr_operations_task("hr-agent-004")

    assert result["task_id"] == "hr-agent-004"
    assert result["agent"] == "hr"
    assert result["status"] == "failed"

    assert result["findings"] == []
    assert result["metrics"] == {}
    assert result["recommendations"] == []


def test_hr_operations_agent_response_schema(monkeypatch):
    monkeypatch.setattr(
        hr_operations_agent,
        "get_completion",
        lambda **kwargs: """
        {
            "executive_summary": "Workforce analysis completed.",
            "key_findings": [],
            "risks": [],
            "recommended_actions": []
        }
        """,
    )

    result = hr_operations_agent.run_hr_operations_task("hr-agent-005")

    assert set(result.keys()) == {
        "task_id",
        "agent",
        "status",
        "findings",
        "metrics",
        "recommendations",
    }

    for finding in result["findings"]:
        assert "finding" in finding
        assert "evidence" in finding