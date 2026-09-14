import pytest

from backend.agents.commander.commander import Commander
from backend.schemas.agent import AgentResponse, Finding


def make_response(
    task_id: str,
    agent: str,
    findings: list[Finding] | None = None,
    metrics: dict | None = None,
    recommendations: list[str] | None = None,
) -> AgentResponse:
    return AgentResponse(
        task_id=task_id,
        agent=agent,
        status="complete",
        findings=findings or [],
        metrics=metrics or {},
        recommendations=recommendations or [],
    )


def test_create_plan_creates_core_agent_tasks():
    commander = Commander()

    plan = commander.create_plan(
        "Find out why revenue dropped and create a recovery plan."
    )

    assert [task["agent"] for task in plan] == ["analyst", "finance", "marketing"]
    assert [task["task_id"] for task in plan] == ["task_001", "task_002", "task_003"]
    assert all(task["objective"] for task in plan)


def test_create_plan_rejects_empty_objective():
    commander = Commander()

    with pytest.raises(ValueError, match="objective"):
        commander.create_plan("   ")


def test_collect_results_groups_multiple_agent_responses():
    commander = Commander()
    analyst_response = make_response("task_001", "analyst")
    finance_response = make_response("task_002", "finance")

    results = commander.collect_results([analyst_response, finance_response])

    assert set(results) == {"analyst", "finance"}
    assert results["analyst"]["responses"][0]["task_id"] == "task_001"
    assert results["finance"]["responses"][0]["task_id"] == "task_002"


def test_collect_results_preserves_findings_metrics_and_recommendations():
    commander = Commander()
    response = make_response(
        task_id="task_001",
        agent="analyst",
        findings=[
            Finding(
                finding="Product C revenue declined sharply.",
                evidence="March revenue fell from 108000 to 62000.",
            )
        ],
        metrics={"product_c_change": -0.43},
        recommendations=["Investigate Product C churn and pipeline quality."],
    )

    results = commander.collect_results([response])

    assert results["analyst"]["findings"] == [
        {
            "finding": "Product C revenue declined sharply.",
            "evidence": "March revenue fell from 108000 to 62000.",
        }
    ]
    assert results["analyst"]["metrics"] == {"product_c_change": -0.43}
    assert results["analyst"]["recommendations"] == [
        "Investigate Product C churn and pipeline quality."
    ]


def test_run_returns_objective_plan_and_results():
    commander = Commander()
    objective = "Diagnose revenue performance."
    response = make_response(
        task_id="task_001",
        agent="analyst",
        findings=[Finding(finding="Revenue dropped.", evidence="CSV analysis.")],
    )

    result = commander.run(objective, [response])

    assert result["objective"] == objective
    assert [task["agent"] for task in result["plan"]] == [
        "analyst",
        "finance",
        "marketing",
    ]
    assert result["results"]["analyst"]["findings"] == [
        {"finding": "Revenue dropped.", "evidence": "CSV analysis."}
    ]


def test_collect_results_rejects_invalid_result_type():
    commander = Commander()

    with pytest.raises(TypeError, match="AgentResponse"):
        commander.collect_results([{"agent": "analyst"}])
