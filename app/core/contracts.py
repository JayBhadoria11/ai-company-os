"""Shared response contract for all AI Company OS agents."""

from typing import Any


AGENT_NAMES = {
    "commander",
    "analyst",
    "finance",
    "marketing",
    "hr",
    "action",
}

AGENT_STATUSES = {
    "success",
    "partial",
    "failed",
}


def create_agent_response(
    task_id: str,
    agent: str,
    status: str = "success",
    findings: list | None = None,
    metrics: dict | None = None,
    recommendations: list | None = None,
) -> dict:
    """Create a standardized response shared by all agents."""

    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string.")

    if agent not in AGENT_NAMES:
        raise ValueError(f"Unknown agent: {agent}")

    if status not in AGENT_STATUSES:
        raise ValueError(f"Invalid agent status: {status}")

    findings = [] if findings is None else findings
    metrics = {} if metrics is None else metrics
    recommendations = [] if recommendations is None else recommendations

    if not isinstance(findings, list):
        raise TypeError("findings must be a list.")

    if not isinstance(metrics, dict):
        raise TypeError("metrics must be a dictionary.")

    if not isinstance(recommendations, list):
        raise TypeError("recommendations must be a list.")

    for finding in findings:
        if not isinstance(finding, dict):
            raise TypeError("Each finding must be a dictionary.")

        if "finding" not in finding or "evidence" not in finding:
            raise ValueError(
                "Each finding must contain 'finding' and 'evidence'."
            )

    if status == "failed":
        findings = []
        metrics = {}
        recommendations = []

    return {
        "task_id": task_id,
        "agent": agent,
        "status": status,
        "findings": findings,
        "metrics": metrics,
        "recommendations": recommendations,
    }