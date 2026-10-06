"""Marketing Agent for AI Company OS."""

import json
import re

from app.core.company_context import company_context_text
from app.core.contracts import create_agent_response
from app.llm.nebius_client import get_completion
from app.tools.marketing import calculate_marketing_metrics


SYSTEM_PROMPT = """
You are the Marketing Agent inside AI Company OS.

Analyze the supplied verified marketing campaign metrics.

Return ONLY valid JSON using exactly this structure:

{
    "executive_summary": "A concise summary of campaign performance.",
    "key_findings": [
        "Finding 1",
        "Finding 2"
    ],
    "risks": [
        "Risk 1"
    ],
    "recommended_actions": [
        "Action 1",
        "Action 2"
    ]
}

STRICT RULES:
1. Use only the supplied campaign data.
2. Never invent numbers or business facts.
3. Python-calculated metrics are authoritative.
4. Do not treat null metrics as zero.
5. Distinguish observed facts from possible explanations.
6. Recommendations must be practical and evidence-based.
7. Do not claim any action was executed.
8. Return valid JSON only.
9. Do not use Markdown fences.
10. Keep the response concise.
"""


def analyze_marketing_campaigns():
    """Analyze campaign metrics using NVIDIA Nemotron."""

    metrics = calculate_marketing_metrics()

    prompt = f"""
Company workspace context (authoritative when present):
{company_context_text()}

Analyze these verified marketing campaign metrics:

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
        raise ValueError("Nemotron returned an empty marketing analysis.")

    cleaned_response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw_response.strip(),
        flags=re.IGNORECASE,
    ).strip()

    try:
        insights = json.loads(cleaned_response)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Nemotron returned invalid JSON: {error}"
        ) from error

    if not isinstance(insights, dict):
        raise ValueError("Nemotron response must be a JSON object.")

    required_keys = [
        "executive_summary",
        "key_findings",
        "risks",
        "recommended_actions",
    ]

    for key in required_keys:
        if key not in insights:
            raise ValueError(
                f"Nemotron response is missing: {key}"
            )

    if not isinstance(insights["executive_summary"], str):
        raise ValueError(
            "executive_summary must be a string."
        )

    for key in ["key_findings", "risks", "recommended_actions"]:
        if not isinstance(insights[key], list):
            raise ValueError(f"{key} must be a list.")

        if not all(isinstance(item, str) for item in insights[key]):
            raise ValueError(
                f"Every item in {key} must be a string."
            )

    return {
        "metrics": metrics,
        "insights": insights,
        "model": "NVIDIA Nemotron via Nebius",
    }


def run_marketing_task(task_id):
    """Run Marketing and return the shared AgentResponse contract."""

    try:
        result = analyze_marketing_campaigns()

        insights = result["insights"]

        findings = [
            {
                "finding": insights["executive_summary"],
                "evidence": {
                    "source": "marketing_metrics",
                },
            }
        ]

        findings.extend(
            {
                "finding": item,
                "evidence": {
                    "source": "marketing_metrics",
                },
            }
            for item in insights["key_findings"]
        )

        findings.extend(
            {
                "finding": f"Risk: {item}",
                "evidence": {
                    "source": "marketing_metrics",
                },
            }
            for item in insights["risks"]
        )

        return create_agent_response(
            task_id=task_id,
            agent="marketing",
            status="success",
            findings=findings,
            metrics={
                "campaigns": result["metrics"],
                "model": result["model"],
            },
            recommendations=insights["recommended_actions"],
        )

    except Exception:
        try:
            metrics = calculate_marketing_metrics()

            return create_agent_response(
                task_id=task_id,
                agent="marketing",
                status="partial",
                findings=[
                    {
                        "finding": (
                            "Campaign metrics were calculated, "
                            "but AI interpretation was unavailable."
                        ),
                        "evidence": {
                            "source": "python_calculations",
                        },
                    }
                ],
                metrics={
                    "campaigns": metrics,
                },
                recommendations=[],
            )

        except Exception:
            return create_agent_response(
                task_id=task_id,
                agent="marketing",
                status="failed",
            )
