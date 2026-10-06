import json
import re

from app.llm.nebius_client import get_completion
from app.tools.financial_aggregator import generate_financial_report
from app.core.contracts import create_agent_response
from app.core.company_context import company_context_text, get_active_company


SYSTEM_PROMPT = """
You are the business intelligence analyst inside AI Company OS.

Analyze the supplied financial report and return ONLY valid JSON.

Use exactly this structure:

{
  "executive_summary": "A concise summary of business performance.",
  "key_findings": [
    "Finding 1",
    "Finding 2",
    "Finding 3",
    "Finding 4"
  ],
  "risks": [
    "Risk 1",
    "Risk 2",
    "Risk 3"
  ],
  "recommended_actions": [
    "Action 1",
    "Action 2",
    "Action 3"
  ]
}

STRICT RULES:
1. Use only supplied financial data.
2. Never invent numbers or business facts.
3. Python calculations are authoritative.
4. January-to-June revenue growth is endpoint_growth_pct.
5. Never confuse endpoint growth with revenue_trend.change_pct.
6. Do not claim seasonality from six months of data.
7. Do not claim cash reserves or cash flow are known.
8. Distinguish observed facts from possible explanations.
9. Recommendations must be practical and evidence-based.
10. Do not claim any action was executed.
11. Return valid JSON only.
12. Do not use Markdown fences.
13. Keep the response concise.
"""


def run_business_analysis(query):
    financial_report = generate_financial_report()

    if not financial_report:
        raise ValueError(
            "No company dataset is available. Upload a company dataset in "
            "Company Workshop before requesting a financial analysis."
        )

    summary = financial_report["summary"]
    verified_metrics = json.dumps(summary, indent=2, default=str)

    prompt = f"""
Company workspace context:
{company_context_text()}

Analysis request:
{query}

Verified financial data:
{json.dumps(financial_report, indent=2, default=str)}

Analyze the report using the required JSON structure.
"""

    raw_response = get_completion(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=6000,
    )

    if not raw_response or not raw_response.strip():
        raise ValueError("Nemotron returned an empty analysis.")

    cleaned_response = raw_response.strip()

    cleaned_response = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        cleaned_response,
        flags=re.IGNORECASE,
    ).strip()

    try:
        insights = json.loads(cleaned_response)

        if isinstance(insights, str):
            insights = json.loads(insights)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Nemotron returned invalid JSON: {error}. "
            f"Response: {cleaned_response[:500]}"
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
            raise ValueError(f"Nemotron response is missing: {key}")

    if not isinstance(insights["executive_summary"], str):
        raise ValueError(
            "Nemotron field 'executive_summary' must be a string."
        )

    for key in ["key_findings", "risks", "recommended_actions"]:
        if not isinstance(insights[key], list):
            raise ValueError(f"Nemotron field '{key}' must be a list.")

        if not all(isinstance(item, str) for item in insights[key]):
            raise ValueError(
                f"Every item in Nemotron field '{key}' must be a string."
            )

    return {
        "query": query,
        "financial_report": financial_report,
        "insights": insights,
        "model": "NVIDIA Nemotron via Nebius",
    }
    
def run_analyst_task(task_id, query):
    """Run Analyst and return the shared AgentResponse contract."""

    result = run_business_analysis(query)

    insights = result["insights"]

    findings = [
        {
            "finding": insights["executive_summary"],
            "evidence": {
                "source": "financial_report",
            },
        }
    ]

    findings.extend(
        {
            "finding": item,
            "evidence": {
                "source": "financial_report",
            },
        }
        for item in insights["key_findings"]
    )

    findings.extend(
        {
            "finding": f"Risk: {item}",
            "evidence": {
                "source": "financial_report",
            },
        }
        for item in insights["risks"]
    )

    return create_agent_response(
        task_id=task_id,
        agent="analyst",
        status="success",
        findings=findings,
        metrics=result["financial_report"],
        recommendations=insights["recommended_actions"],
    )
