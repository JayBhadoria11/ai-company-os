from collections import defaultdict
from typing import Any

from backend.agents.analyst.analyst import analyze_revenue_as_agent
from backend.agents.finance.finance import analyze_finances_as_agent
from backend.schemas.agent import AgentResponse


class Commander:
    agent_objectives = {
        "analyst": "Analyze business data and identify major changes.",
        "finance": "Review financial impact and cash flow risks.",
        "marketing": "Investigate demand, funnel, and campaign performance.",
    }

    def create_plan(self, objective: str) -> list[dict[str, str]]:
        self._validate_objective(objective)

        return [
            {
                "task_id": f"task_{index:03d}",
                "agent": agent,
                "objective": task_objective,
            }
            for index, (agent, task_objective) in enumerate(
                self.agent_objectives.items(), start=1
            )
        ]

    def collect_results(self, results: list[AgentResponse]) -> dict[str, Any]:
        if not isinstance(results, list):
            raise TypeError("results must be a list of AgentResponse objects.")

        collected: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "responses": [],
                "findings": [],
                "metrics": {},
                "recommendations": [],
            }
        )

        for result in results:
            if not isinstance(result, AgentResponse):
                raise TypeError("Each result must be an AgentResponse object.")

            agent_results = collected[result.agent]
            agent_results["responses"].append(result.model_dump())
            agent_results["findings"].extend(
                finding.model_dump() for finding in result.findings
            )
            agent_results["metrics"].update(result.metrics)
            agent_results["recommendations"].extend(result.recommendations)

        return dict(collected)

    def execute_analyst_task(
        self, task: dict[str, str], file_path: str
    ) -> AgentResponse:
        if not isinstance(task, dict):
            raise TypeError("task must be a dictionary.")

        if task.get("agent") != "analyst":
            raise ValueError("execute_analyst_task requires an analyst task.")

        task_id = task.get("task_id")
        if not task_id:
            raise ValueError("Analyst task must contain a task_id.")

        return analyze_revenue_as_agent(task_id=task_id, file_path=file_path)

    def execute_finance_task(
        self, task: dict[str, str], file_path: str
    ) -> AgentResponse:
        if not isinstance(task, dict):
            raise TypeError("task must be a dictionary.")

        if task.get("agent") != "finance":
            raise ValueError("execute_finance_task requires a finance task.")

        task_id = task.get("task_id")
        if not task_id:
            raise ValueError("Finance task must contain a task_id.")

        return analyze_finances_as_agent(task_id=task_id, file_path=file_path)

    def run(
        self,
        objective: str,
        results: list[AgentResponse] | None = None,
        file_path: str | None = None,
        finance_file_path: str | None = None,
    ) -> dict[str, Any]:
        self._validate_objective(objective)

        plan = self.create_plan(objective)
        if results is None:
            agent_results = []
        elif not isinstance(results, list):
            raise TypeError("results must be a list of AgentResponse objects.")
        else:
            agent_results = list(results)

        if file_path is not None:
            analyst_task = next(task for task in plan if task["agent"] == "analyst")
            agent_results.append(self.execute_analyst_task(analyst_task, file_path))

        if finance_file_path is not None:
            finance_task = next(task for task in plan if task["agent"] == "finance")
            agent_results.append(
                self.execute_finance_task(finance_task, finance_file_path)
            )

        collected_results = self.collect_results(agent_results)

        return {
            "objective": objective,
            "plan": plan,
            "results": collected_results,
        }

    @staticmethod
    def _validate_objective(objective: str) -> None:
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("objective must be a non-empty string.")
