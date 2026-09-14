from collections import defaultdict
from typing import Any

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

    def run(self, objective: str, results: list[AgentResponse]) -> dict[str, Any]:
        self._validate_objective(objective)

        plan = self.create_plan(objective)
        collected_results = self.collect_results(results)

        return {
            "objective": objective,
            "plan": plan,
            "results": collected_results,
        }

    @staticmethod
    def _validate_objective(objective: str) -> None:
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("objective must be a non-empty string.")
