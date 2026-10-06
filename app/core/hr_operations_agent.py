"""HR and Operations Agent for AI Company OS."""

import json
import re

from app.core.company_context import company_context_text
from app.core.contracts import create_agent_response
from app.llm.nebius_client import get_completion
from app.tools.hr_operations import calculate_hr_operations_metrics


SYSTEM_PROMPT = """
You are the HR and Operations Agent inside AI Company OS.

Analyze only the verified metrics provided to you.

Return ONLY valid JSON:
{
  "executive_summary": "Brief summary.",
  "key_findings": ["Finding 1"],
  "risks": ["Risk 1"],
  "recommended_actions": ["Recommendation 1"]
}

Never invent metrics.
"""


def analyze_hr_operations():
    """Analyze workforce and operations using NVIDIA Nemotron."""

    metrics = calculate_hr_operations_metrics()

    prompt = f"""
Company workspace context (authoritative when present):
{company_context_text()}

Analyze these verified HR and operations metrics:

{json.dumps(metrics, indent=2, allow_nan=False)}

Return the required JSON analysis.
"""

    raw_response = get_completion(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=3000,
    )

    if not raw_response or not raw_response.strip():
        raise ValueError(
            "Nemotron returned an empty HR/Ops analysis."
        )

    cleaned_response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw_response.strip(),
        flags=re.I,
    ).strip()

    try:
        insights = json.loads(cleaned_response)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Nemotron returned invalid HR/Ops JSON: {error}"
        ) from error

    if not isinstance(insights, dict):
        raise ValueError(
            "Nemotron HR/Ops response must be a JSON object."
        )

    return {
        "metrics": metrics,
        "insights": insights,
        "model": "NVIDIA Nemotron via Nebius",
    }


def run_hr_operations_task(task_id):
    """Run HR/Ops while distinguishing data failures from LLM failures."""

    # Metrics failure = complete agent failure.
    try:
        metrics = calculate_hr_operations_metrics()
    except Exception:
        return create_agent_response(
            task_id=task_id,
            agent="hr",
            status="failed",
            findings=[],
            metrics={},
            recommendations=[],
        )

    # LLM / JSON failure = partial success because verified metrics exist.
    try:
        prompt = f"""
Company workspace context (authoritative when present):
{company_context_text()}

Analyze these verified HR and operations metrics:

{json.dumps(metrics, indent=2, allow_nan=False)}

Return the required JSON analysis.
"""

        raw_response = get_completion(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=3000,
        )

        if not raw_response or not raw_response.strip():
            raise ValueError(
                "Nemotron returned an empty HR/Ops analysis."
            )

        cleaned_response = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            raw_response.strip(),
            flags=re.I,
        ).strip()

        insights = json.loads(cleaned_response)

        if not isinstance(insights, dict):
            raise ValueError(
                "Nemotron HR/Ops response must be a JSON object."
            )

    except Exception as error:
        return create_agent_response(
            task_id=task_id,
            agent="hr",
            status="partial",
            findings=[
                {
                    "finding": (
                        "HR/Ops metrics were calculated, but "
                        "NVIDIA analysis was unavailable."
                    ),
                    "evidence": {
                        "error": str(error),
                    },
                }
            ],
            metrics={
                "workforce": metrics,
            },
            recommendations=[],
        )

    return create_agent_response(
        task_id=task_id,
        agent="hr",
        status="success",
        findings=[
            {
                "finding": insights.get(
                    "executive_summary",
                    "HR and operations analysis completed.",
                ),
                "evidence": {
                    "workforce": metrics,
                },
            }
        ],
        metrics={
            "workforce": metrics,
            "nvidia_analysis": insights,
        },
        recommendations=insights.get(
            "recommended_actions",
            [],
        ),
    )
