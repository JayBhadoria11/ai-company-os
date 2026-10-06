"""NVIDIA final synthesis layer for AI Company OS."""

import json
import re

from app.llm.nebius_client import get_completion


SYSTEM_PROMPT = """
You are the final NVIDIA intelligence layer inside AI Company OS.

Your job is to synthesize findings from multiple business-analysis agents
into one executive-level plain-text conclusion.

You must:
- use only the provided agent findings and metrics
- identify the most important business insights
- explain important relationships or risks
- provide practical recommendations
- never invent missing data

Return ONLY valid JSON using exactly this structure:

{
  "executive_summary": "Overall business conclusion.",
  "key_insights": ["Important insight 1"],
  "risks": ["Important risk 1"],
  "recommended_actions": ["Recommended action 1"]
}
"""


def _parse_synthesis_response(raw_response):
    """Parse and validate NVIDIA synthesis output."""

    if not raw_response or not raw_response.strip():
        raise ValueError("NVIDIA synthesis returned an empty response.")

    cleaned_response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        raw_response.strip(),
        flags=re.IGNORECASE,
    ).strip()

    try:
        result = json.loads(cleaned_response)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"NVIDIA synthesis returned invalid JSON: {error}."
        ) from error

    if not isinstance(result, dict):
        raise ValueError(
            "NVIDIA synthesis response must be a JSON object."
        )

    required_keys = [
        "executive_summary",
        "key_insights",
        "risks",
        "recommended_actions",
    ]

    for key in required_keys:
        if key not in result:
            raise ValueError(
                f"NVIDIA synthesis response is missing: {key}"
            )

    if not isinstance(result["executive_summary"], str):
        raise ValueError(
            "NVIDIA synthesis executive_summary must be a string."
        )

    for key in ["key_insights", "risks", "recommended_actions"]:
        if not isinstance(result[key], list):
            raise ValueError(
                f"NVIDIA synthesis {key} must be a list."
            )

        if not all(isinstance(item, str) for item in result[key]):
            raise ValueError(
                f"Every item in {key} must be a string."
            )

    return result


def synthesize_agent_responses(agent_responses, completion_fn=None):
    """Ask NVIDIA to synthesize specialist-agent results."""

    if not isinstance(agent_responses, list):
        raise TypeError("agent_responses must be a list.")

    prompt = f"""
Specialist agent results:

{json.dumps(agent_responses, indent=2, default=str)}

Create the final executive synthesis using the required JSON structure.
"""

    completion = completion_fn or get_completion

    raw_response = completion(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=8000,
    )

    return _parse_synthesis_response(raw_response)
