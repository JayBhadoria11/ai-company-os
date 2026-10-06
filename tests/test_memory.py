import uuid

import pytest

from app.database.memory import (
    initialize_memory,
    save_agent_response,
    get_task_memory,
)


def unique_task_id():
    return f"memory-test-{uuid.uuid4()}"


def test_initialize_memory():
    initialize_memory()


def test_save_and_get_agent_response():
    task_id = unique_task_id()

    response = {
        "task_id": task_id,
        "agent": "analyst",
        "status": "success",
        "findings": [
            {
                "finding": "Revenue increased.",
                "evidence": {
                    "source": "financial_report"
                },
            }
        ],
        "metrics": {
            "revenue_growth_pct": 23.5
        },
        "recommendations": [
            "Monitor revenue growth."
        ],
    }

    save_agent_response(response)

    memory = get_task_memory(task_id)

    assert len(memory) == 1
    assert memory[0]["task_id"] == task_id
    assert memory[0]["agent"] == "analyst"
    assert memory[0]["status"] == "success"
    assert memory[0]["findings"] == response["findings"]
    assert memory[0]["metrics"] == response["metrics"]
    assert memory[0]["recommendations"] == response["recommendations"]


def test_memory_supports_multiple_agents():
    task_id = unique_task_id()

    responses = [
        {
            "task_id": task_id,
            "agent": "analyst",
            "status": "success",
            "findings": [],
            "metrics": {"profit": 4000},
            "recommendations": [],
        },
        {
            "task_id": task_id,
            "agent": "marketing",
            "status": "success",
            "findings": [],
            "metrics": {"ctr": 5.0},
            "recommendations": [],
        },
    ]

    for response in responses:
        save_agent_response(response)

    memory = get_task_memory(task_id)

    assert len(memory) == 2
    assert memory[0]["agent"] == "analyst"
    assert memory[1]["agent"] == "marketing"


def test_missing_response_field():
    response = {
        "task_id": unique_task_id(),
        "agent": "analyst",
        "status": "success",
        "findings": [],
        "metrics": {},
    }

    with pytest.raises(ValueError, match="recommendations"):
        save_agent_response(response)