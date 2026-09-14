from pathlib import Path

import pytest

from backend.agents.commander.commander import Commander
from backend.schemas.agent import AgentResponse, Finding


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "revenue.csv"
EXPENSES_PATH = Path(__file__).resolve().parents[3] / "data" / "expenses.csv"


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


def test_execute_analyst_task_returns_agent_response():
    commander = Commander()
    task = {
        "task_id": "task_001",
        "agent": "analyst",
        "objective": "Analyze revenue and identify major changes.",
    }

    response = commander.execute_analyst_task(task, str(DATA_PATH))

    assert isinstance(response, AgentResponse)
    assert response.agent == "analyst"
    assert response.task_id == "task_001"


def test_execute_analyst_task_requires_analyst_task():
    commander = Commander()
    task = {
        "task_id": "task_002",
        "agent": "finance",
        "objective": "Review financial impact.",
    }

    with pytest.raises(ValueError, match="analyst"):
        commander.execute_analyst_task(task, str(DATA_PATH))


def test_execute_analyst_task_requires_task_id():
    commander = Commander()

    with pytest.raises(ValueError, match="task_id"):
        commander.execute_analyst_task({"agent": "analyst"}, str(DATA_PATH))


def test_run_with_file_path_executes_analyst():
    commander = Commander()

    result = commander.run("Find out why revenue dropped.", file_path=str(DATA_PATH))

    assert result["objective"] == "Find out why revenue dropped."
    assert [task["agent"] for task in result["plan"]] == [
        "analyst",
        "finance",
        "marketing",
    ]
    assert "analyst" in result["results"]
    assert result["results"]["analyst"]["responses"][0]["status"] == "completed"


def test_run_with_file_path_contains_product_c_decline():
    commander = Commander()

    result = commander.run("Find out why revenue dropped.", file_path=str(DATA_PATH))
    analyst_result = result["results"]["analyst"]
    product_c = analyst_result["metrics"]["products"]["Product C"]

    assert product_c["previous_revenue"] == 108000
    assert product_c["latest_revenue"] == 62000
    assert product_c["change"] == pytest.approx(-0.43)
    assert any("Product C" in finding["finding"] for finding in analyst_result["findings"])


def test_execute_finance_task_returns_agent_response():
    commander = Commander()
    task = {
        "task_id": "task_002",
        "agent": "finance",
        "objective": "Review financial impact and cash flow risks.",
    }

    response = commander.execute_finance_task(task, str(EXPENSES_PATH))

    assert isinstance(response, AgentResponse)
    assert response.agent == "finance"
    assert response.task_id == "task_002"
    assert response.findings
    assert response.metrics


def test_execute_finance_task_requires_finance_task():
    commander = Commander()
    task = {
        "task_id": "task_001",
        "agent": "analyst",
        "objective": "Analyze revenue and identify major changes.",
    }

    with pytest.raises(ValueError, match="finance"):
        commander.execute_finance_task(task, str(EXPENSES_PATH))


def test_execute_finance_task_requires_task_id():
    commander = Commander()

    with pytest.raises(ValueError, match="task_id"):
        commander.execute_finance_task({"agent": "finance"}, str(EXPENSES_PATH))


def test_run_with_finance_file_path_executes_finance():
    commander = Commander()

    result = commander.run(
        "Find out why profitability changed.",
        finance_file_path=str(EXPENSES_PATH),
    )

    assert "finance" in result["results"]
    assert "analyst" not in result["results"]
    assert result["results"]["finance"]["responses"][0]["status"] == "completed"


def test_run_with_finance_file_path_identifies_marketing_expense_increase():
    commander = Commander()

    result = commander.run(
        "Find out why profitability changed.",
        finance_file_path=str(EXPENSES_PATH),
    )
    finance_result = result["results"]["finance"]

    assert (
        finance_result["metrics"]["largest_category_increase"]["category"]
        == "Marketing"
    )
    assert (
        finance_result["metrics"]["largest_category_increase"]["amount_change"]
        == 15000
    )
    assert any("Marketing" in finding["finding"] for finding in finance_result["findings"])


def test_run_with_revenue_and_finance_file_paths_executes_both_agents():
    commander = Commander()

    result = commander.run(
        "Find out why revenue dropped and profitability changed.",
        file_path=str(DATA_PATH),
        finance_file_path=str(EXPENSES_PATH),
    )

    assert set(result["results"]) == {"analyst", "finance"}
    assert result["results"]["analyst"]["responses"][0]["agent"] == "analyst"
    assert result["results"]["finance"]["responses"][0]["agent"] == "finance"
    assert (
        result["results"]["finance"]["metrics"]["largest_category_increase"][
            "category"
        ]
        == "Marketing"
    )
