import pytest

from app.core.contracts import create_agent_response


def test_default_agent_response():
    response = create_agent_response(
        task_id="task-001",
        agent="analyst",
    )

    assert response == {
        "task_id": "task-001",
        "agent": "analyst",
        "status": "success",
        "findings": [],
        "metrics": {},
        "recommendations": [],
    }


def test_response_with_data():
    response = create_agent_response(
        task_id="task-002",
        agent="finance",
        status="partial",
        findings=[
            {
                "finding": "Revenue increased",
                "evidence": "Revenue rose by 12%",
            }
        ],
        metrics={"revenue_growth_pct": 12},
        recommendations=["Review expense trends"],
    )

    assert response["status"] == "partial"
    assert response["metrics"]["revenue_growth_pct"] == 12
    assert len(response["findings"]) == 1


def test_invalid_agent():
    with pytest.raises(ValueError):
        create_agent_response(
            task_id="task-003",
            agent="unknown",
        )


def test_invalid_status():
    with pytest.raises(ValueError):
        create_agent_response(
            task_id="task-004",
            agent="analyst",
            status="pending",
        )


def test_empty_task_id():
    with pytest.raises(ValueError):
        create_agent_response(
            task_id="",
            agent="analyst",
        )


def test_invalid_finding_structure():
    with pytest.raises(ValueError):
        create_agent_response(
            task_id="task-005",
            agent="analyst",
            findings=[{"finding": "Missing evidence"}],
        )


def test_failed_response_clears_results():
    response = create_agent_response(
        task_id="task-006",
        agent="marketing",
        status="failed",
        findings=[
            {
                "finding": "Some finding",
                "evidence": "Some evidence",
            }
        ],
        metrics={"ctr": 4.5},
        recommendations=["Some action"],
    )

    assert response["status"] == "failed"
    assert response["findings"] == []
    assert response["metrics"] == {}
    assert response["recommendations"] == []