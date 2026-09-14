from typing import Any

from pydantic import BaseModel


class Finding(BaseModel):
    finding: str
    evidence: str


class AgentResponse(BaseModel):
    task_id: str
    agent: str
    status: str
    findings: list[Finding]
    metrics: dict[str, Any]
    recommendations: list[str]