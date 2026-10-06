"""Commander/CEO orchestration agent for AI Company OS."""

import json
import re

from app.core.agent import run_analyst_task
from app.core.contracts import create_agent_response
from app.core.hr_operations_agent import run_hr_operations_task
from app.core.marketing_agent import run_marketing_task
from app.core.synthesis import synthesize_agent_responses
from app.database.memory import save_agent_response
from app.llm.nebius_client import get_completion


SYSTEM_PROMPT = """
You are the Commander/CEO agent inside AI Company OS.

You may ONLY select these agents:
- analyst
- marketing
- hr

Never select any other agent, including data_engineer or finance.

Return ONLY valid JSON:
{
  "executive_summary": "Brief description.",
  "required_agents": ["analyst"],
  "investigation_questions": ["Question 1"]
}

Never invent business data.
"""


AVAILABLE_AGENTS = {
    "analyst": run_analyst_task,
    "marketing": run_marketing_task,
    "hr": run_hr_operations_task,
}


# ---------------------------------------------------------------------------
# Synthesis context bounds.
#
# The synthesis call uses a fixed output budget (max_tokens=4000) that must not
# change. Large datasets (for example a 400k-row train.csv) can otherwise inflate
# the prompt with duplicated raw breakdowns, so Nemotron spends its whole output
# budget before emitting any content and returns finish_reason="length" with an
# empty message. The deterministic analysis stays complete; only the text sent to
# the LLM is bounded and de-duplicated.
# ---------------------------------------------------------------------------
SYNTHESIS_EVIDENCE_CHAR_LIMIT = 14000
SYNTHESIS_PROMPT_CHAR_BUDGET = 26000

# Top-N slices kept in the synthesis evidence digest. These are display-only
# caps: the full deterministic analysis is still stored in the agent metrics.
_EVIDENCE_PRODUCTS = 8
_EVIDENCE_REGIONS = 8
_EVIDENCE_CHANNELS = 5
_EVIDENCE_MONTHS = 12
_EVIDENCE_DECLINING = 8
_EVIDENCE_INSIGHTS = 8
_EVIDENCE_LIMITATIONS = 8
_EVIDENCE_DEPARTMENTS = 10


def _take(items, count):
    if not isinstance(items, list):
        return items
    return items[:count]


def _compact_reasoning_for_prompt(reasoning):
    """Drop the raw sales-pattern arrays that duplicate the evidence digest.

    The computed strongest/weakest/trend values are kept; the full region,
    product and monthly lists are not needed by the LLM and are the main source
    of duplicated context for large datasets.
    """

    if not isinstance(reasoning, dict):
        return reasoning

    compact = dict(reasoning)
    pattern = reasoning.get("sales_pattern")

    if isinstance(pattern, dict):
        compact["sales_pattern"] = {
            "strongest_region": pattern.get("strongest_region"),
            "weakest_region": pattern.get("weakest_region"),
            "strongest_product": pattern.get("strongest_product"),
            "weakest_product": pattern.get("weakest_product"),
            "weakest_declining_region": pattern.get("weakest_declining_region"),
            "strongest_month": pattern.get("strongest_month"),
            "weakest_month": pattern.get("weakest_month"),
            "trend_change_pct": pattern.get("trend_change_pct"),
        }

    return compact


def _compact_evidence_for_prompt(evidence_by_dataset):
    """Build a small, decision-relevant evidence digest for the synthesis prompt.

    Keeps the KPIs, the top product/region slices, monthly trend, workforce
    fields and limitations. Large cross-tab arrays that the reasoning pack never
    uses (product_region, product_channel, sellers, payments, reviews) are
    omitted from the prompt while remaining intact in the stored evidence.
    """

    digest = {}

    for filename, payload in (evidence_by_dataset or {}).items():
        payload = payload or {}
        domain = payload.get("domain")
        data = payload.get("evidence", {}) or {}

        if domain == "workforce":
            digest[filename] = {
                "domain": domain,
                "dataset": data.get("dataset") or "workforce",
                "headcount": data.get("headcount"),
                "attrition": data.get("attrition"),
                "overtime": data.get("overtime"),
                "departments": _take(data.get("departments"), _EVIDENCE_DEPARTMENTS),
                "department_metrics": _take(
                    data.get("department_metrics"), _EVIDENCE_DEPARTMENTS
                ),
                "available_fields": data.get("available_fields"),
                "limitations": _take(
                    data.get("limitations"), _EVIDENCE_LIMITATIONS
                ),
            }
            continue

        declining = data.get("declining")
        compact_declining = None
        if isinstance(declining, dict):
            compact_declining = {
                "products": _take(
                    declining.get("products"), _EVIDENCE_DECLINING
                ),
                "regions": _take(declining.get("regions"), _EVIDENCE_DECLINING),
            }
        elif isinstance(declining, list):
            compact_declining = _take(declining, _EVIDENCE_DECLINING)

        monthly = data.get("monthly") or []
        if isinstance(monthly, list):
            monthly = monthly[-_EVIDENCE_MONTHS:]

        digest[filename] = {
            "domain": domain,
            "dataset": data.get("dataset"),
            "metrics": data.get("metrics"),
            "top_products": _take(data.get("products"), _EVIDENCE_PRODUCTS),
            "top_regions": _take(data.get("regions"), _EVIDENCE_REGIONS),
            "channels": _take(data.get("channels"), _EVIDENCE_CHANNELS),
            "monthly": monthly,
            "declining": compact_declining,
            "insights": _take(data.get("insights"), _EVIDENCE_INSIGHTS),
            "limitations": _take(
                data.get("limitations"), _EVIDENCE_LIMITATIONS
            ),
        }

    return digest


def _bounded_json(value, limit):
    """Serialize compactly and hard-cap the result as a last-resort safeguard."""

    text = json.dumps(value, separators=(",", ":"), default=str)

    if len(text) <= limit:
        return text

    return json.dumps(
        {
            "truncated": True,
            "note": (
                "Additional evidence was omitted to stay within the synthesis "
                "context budget. The deterministic reasoning pack above is "
                "authoritative."
            ),
            "evidence_head": text[:limit],
        },
        separators=(",", ":"),
        default=str,
    )


def _parse_commander_plan(raw_response):
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        (raw_response or "").strip(),
        flags=re.I,
    ).strip()

    try:
        plan = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Commander returned invalid JSON: {error}."
        ) from error

    if not isinstance(plan, dict):
        raise ValueError("Commander response must be a JSON object.")

    for key in (
        "executive_summary",
        "required_agents",
        "investigation_questions",
    ):
        if key not in plan:
            raise ValueError(
                f"Commander response is missing: {key}"
            )

    if (
        not isinstance(plan["required_agents"], list)
        or not isinstance(plan["investigation_questions"], list)
    ):
        raise ValueError(
            "Commander returned an invalid investigation plan."
        )

    for agent in plan["required_agents"]:
        if agent not in AVAILABLE_AGENTS:
            raise ValueError(
                f"Commander selected unknown agent: {agent}"
            )

    return plan


def create_investigation_plan(query):
    raw = get_completion(
        prompt=f"User request:\n{query}\n\nCreate the investigation plan.",
        system_prompt=SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=2000,
    )

    return _parse_commander_plan(raw)


def _split_questions(query):
    """Split a multi-question user request while preserving question order."""
    lines = [
        line.strip()
        for line in query.splitlines()
        if line.strip()
    ]
    return lines


def _build_fallback_synthesis(agent_responses):
    """Build deterministic synthesis when NVIDIA synthesis is unavailable."""

    key_insights = []
    recommended_actions = []

    for response in agent_responses:
        for finding in response.get("findings", []):
            if isinstance(finding, dict):
                value = finding.get("finding")
                if isinstance(value, str) and value.strip():
                    key_insights.append(value.strip())

        for recommendation in response.get("recommendations", []):
            if (
                isinstance(recommendation, str)
                and recommendation.strip()
            ):
                recommended_actions.append(
                    recommendation.strip()
                )

    return {
        "executive_summary": (
            "Specialist-agent analysis was completed successfully."
        ),
        "key_insights": key_insights or [
            "Specialist-agent analysis was completed."
        ],
        "risks": [
            "NVIDIA synthesis output was unavailable or did not "
            "match the expected schema."
        ],
        "recommended_actions": recommended_actions,
    }


def _sanitize_investigation_text(text):
    """Remove empty placeholder question slots a model may add.

    The pipeline must never render placeholder questions such as
    "QUESTION 6 / No question was provided" when fewer questions exist.
    """

    if not text:
        return text

    cleaned = re.sub(
        r"QUESTION\s+\d+\s*[:\-]?\s*\n\s*No question was provided[^\n]*\n?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"QUESTION\s+\d+\s*[:\-]?\s*No question was provided[^\n]*\n?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned.strip()


def _build_company_prompt(company, combined, reasoning, questions):
    """Build a dynamic, multi-dataset, evidence-classified prompt."""

    count = len(questions)

    scope = (
        "the single question provided"
        if count <= 1
        else f"EACH OF THE {count} QUESTIONS"
    )

    question_lines = chr(10).join(
        f"{index + 1}. {question}"
        for index, question in enumerate(questions)
    )

    reasoning_context = _compact_reasoning_for_prompt(reasoning)
    evidence_context = _bounded_json(
        _compact_evidence_for_prompt(combined.get("evidence", {})),
        SYNTHESIS_EVIDENCE_CHAR_LIMIT,
    )

    return f"""
You are the final business intelligence analyst for {company}.

Answer {scope}, separately and in order.
Use ONLY the verified evidence below for every claim.
Never calculate metrics from raw rows when deterministic evidence exists.

EVIDENCE CLASSIFICATION (mandatory):
Classify every statement as one of:
1. VERIFIED FACT — directly measured in a connected dataset.
2. CALCULATED RESULT — a deterministic comparison/derivation from verified
   facts (rankings, per-period changes), not a future scenario.
3. CALCULATED SCENARIO — arithmetic extrapolation on verified facts, with
   assumptions stated (only when the user asks for one).
4. INFERENCE — a reasoned risk/implication, never stated as fact.
5. LIMITATION / UNKNOWN — what the data cannot determine.
6. RECOMMENDATION — evidence-grounded next action (human approval required).

REASONING RULES:
- Never convert an INFERENCE or a CALCULATED RESULT into a VERIFIED FACT.
- Do NOT introduce any growth, forecast, what-if, or required-orders scenario
  unless the user explicitly asks for a growth target, forecast, what-if
  analysis, required orders, or a future sales target. For descriptive
  questions, present only VERIFIED FACTS and CALCULATED RESULTS.
- Never claim the workforce cannot support growth. The datasets do not measure
  employee productivity or workload capacity, so the conclusion must remain an
  appropriately uncertain risk assessment.
- Never describe attrition as an annual or per-year forecast. The HR dataset has
  no time dimension. State recorded counts/rates only
  (e.g. "records 237 employees with attrition, 16.12% of the workforce").
- Treat overtime as a risk indicator only ("are recorded as working overtime"),
  never as proof of insufficient capacity.
- Present any growth projection as a CALCULATED SCENARIO and state the
  assumption (average order value remains approximately constant). Never state
  the company necessarily needs that exact order count.
- For sales-pattern questions, explicitly address the strongest region, the
  weakest region, the strongest product, the weakest/underperforming product
  pattern, and the strongest/weakest monthly (time) pattern using only the
  deterministic evidence. Do not claim declines unless the deterministic
  evidence names the products/regions/periods.
- Only state a decline or underperformance when the CALCULATED RESULTS or
  DATASET EVIDENCE identify the specific product, region, or period.
- Do not recommend hiring into a department merely because it is the largest.
- Recommendations must directly address the user's question. Do not return
  "Monitor expenses" when no expense dataset is connected or when the question
  is not about expenses.
- If a dataset lacks required fields, state exactly what is missing.
- Answer EXACTLY {count} question(s). Never add empty or placeholder questions
  such as "No question was provided".

DETERMINISTIC REASONING PACK (authoritative — do not contradict):
{json.dumps(reasoning_context, separators=(",", ":"), default=str)}

AUTHORITATIVE EXECUTIVE SUMMARY DRAFT:
{reasoning.get("executive_summary_draft", "")}

Your executive summary must preserve this draft's facts, uncertainty and labels.

CONNECTED DATASETS:
{json.dumps(combined.get("datasets_used", []), separators=(",", ":"), default=str)}

DATASET EVIDENCE (decision-relevant digest; full analysis retained internally):
{evidence_context}

USER QUESTIONS:
{question_lines}

End with an EXECUTIVE SUMMARY that answers, in order: what is verified, what
scenario was calculated, what risks are indicated, what cannot be determined,
and what management should do next.
"""


def _run_company_investigation(task_id, query):
    from app.core.company_context import (
        get_company_dataset_analysis,
        get_active_company,
        build_company_dataset_evidence,
    )
    from app.core.evidence_reasoning import (
        build_reasoning_pack,
        key_insight_strings,
        recommendation_strings,
    )

    ctx = get_active_company()
    combined = build_company_dataset_evidence(query)

    if not ctx["datasets"] or combined is None:
        return create_agent_response(
            task_id=task_id,
            agent="commander",
            status="success",
            findings=[
                {
                    "finding": (
                        "No usable uploaded company dataset "
                        "is available yet."
                    ),
                    "evidence": {
                        "source": "company_workspace"
                    },
                }
            ],
            metrics={
                "company_analysis": None,
                "required_agents": [],
                "investigation_questions": _split_questions(query),
                "nvidia_synthesis": {
                    "executive_summary": (
                        "Upload a usable sales or business dataset "
                        "before asking data-driven company questions."
                    ),
                    "key_insights": [],
                    "risks": [
                        "No verified company dataset is available."
                    ],
                    "recommended_actions": [
                        "Upload and connect a company dataset."
                    ],
                },
            },
            recommendations=[
                "Upload and connect a company dataset."
            ],
        )

    primary = get_company_dataset_analysis()
    questions = _split_questions(query)

    # Deterministic, labelled evidence taxonomy (facts / scenario / inference /
    # limitation / recommendation). This is authoritative for the LLM.
    reasoning = build_reasoning_pack(query, combined)

    prompt = _build_company_prompt(
        ctx["profile"].get("name") or "the company",
        combined,
        reasoning,
        questions,
    )

    raw = get_completion(
        prompt=prompt,
        system_prompt=(
            "You are a strict evidence-grounded company intelligence "
            "analyst working across multiple connected datasets. "
            "Never fabricate numbers or missing data. Preserve the evidence "
            "classification and uncertainty provided to you."
        ),
        temperature=0.1,
        max_tokens=4000,
    )

    raw = _sanitize_investigation_text(raw)

    datasets_used = combined.get("datasets_used", [])
    source_datasets = combined.get("source_datasets", [])

    required_agents = ["analyst"]
    if any(item.get("domain") == "workforce" for item in datasets_used):
        required_agents.append("hr")
    if any(item.get("domain") == "financial" for item in datasets_used):
        required_agents.append("finance")

    # Question-aware insights and evidence-grounded actions.
    key_insights = key_insight_strings(reasoning) or combined.get("insights") or (
        (primary or {}).get("insights", [])
    )
    risks = [
        item.get("statement")
        for item in reasoning.get("limitations", [])
        if item.get("statement")
    ] or combined.get("limitations") or (primary or {}).get("limitations", [])
    actions = recommendation_strings(reasoning)

    synthesis = {
        "executive_summary": raw or reasoning.get("executive_summary_draft", ""),
        "verified_summary": reasoning.get("executive_summary_draft", ""),
        "key_insights": key_insights,
        "risks": risks,
        "recommended_actions": actions,
        "question_count": len(questions),
        "questions": questions,
        "evidence_labels": [
            "VERIFIED FACT",
            "CALCULATED RESULT",
            "CALCULATED SCENARIO",
            "INFERENCE",
            "LIMITATION",
            "RECOMMENDATION",
        ],
        "reasoning": reasoning,
    }

    finding_evidence = {
        "datasets": source_datasets,
        "source_datasets": source_datasets,
        "dataset": (primary or {}).get("dataset"),
        "dataset_evidence": combined,
        "reasoning": reasoning,
    }

    agent_responses = [
        {
            "task_id": f"{task_id}-analyst",
            "agent": "analyst",
            "status": "success",
            "findings": [
                {
                    "finding": raw,
                    "evidence": finding_evidence,
                }
            ],
            "metrics": (primary or {}).get("metrics", {}),
            "recommendations": [],
        }
    ]

    workforce_files = [
        item["filename"]
        for item in datasets_used
        if item.get("domain") == "workforce"
    ]

    if workforce_files:
        agent_responses.append(
            {
                "task_id": f"{task_id}-hr",
                "agent": "hr",
                "status": "success",
                "findings": [
                    {
                        "finding": (
                            "Workforce evidence analyzed from the connected "
                            "HR dataset(s): " + ", ".join(workforce_files)
                        ),
                        "evidence": finding_evidence,
                    }
                ],
                "metrics": {
                    "workforce": {
                        filename: payload["evidence"]
                        for filename, payload in combined["evidence"].items()
                        if payload.get("domain") == "workforce"
                    }
                },
                "recommendations": [],
            }
        )

    return create_agent_response(
        task_id=task_id,
        agent="commander",
        status="success",
        findings=[
            {
                "finding": raw,
                "evidence": finding_evidence,
            }
        ],
        metrics={
            "company_analysis": primary,
            "required_agents": required_agents,
            "investigation_questions": questions,
            "agent_responses": agent_responses,
            "nvidia_synthesis": synthesis,
            "datasets_used": datasets_used,
            "dataset_evidence": combined,
            "reasoning": reasoning,
        },
        recommendations=actions or ["Monitor expenses."],
    )


def run_commander_task(task_id, query):
    from app.core.company_context import get_active_company

    if get_active_company().get("active"):
        return _run_company_investigation(task_id, query)

    plan = create_investigation_plan(query)
    agent_responses = []

    for agent_name in plan["required_agents"]:
        if agent_name == "analyst":
            response = run_analyst_task(
                task_id=f"{task_id}-analyst",
                query=query,
            )
        elif agent_name == "marketing":
            response = run_marketing_task(
                task_id=f"{task_id}-marketing"
            )
        elif agent_name == "hr":
            response = run_hr_operations_task(
                task_id=f"{task_id}-hr"
            )
        else:
            raise ValueError(
                f"Unsupported Commander agent: {agent_name}"
            )

        save_agent_response(response)
        agent_responses.append(response)

    try:
        synthesis = synthesize_agent_responses(
            agent_responses,
            completion_fn=get_completion,
        )
    except ValueError:
        synthesis = _build_fallback_synthesis(agent_responses)

    findings = [
        {
            "finding": plan["executive_summary"],
            "evidence": {"source": "commander_plan"},
        },
        {
            "finding": synthesis["executive_summary"],
            "evidence": {"source": "nvidia_final_synthesis"},
        },
    ]

    metrics = {
        "required_agents": plan["required_agents"],
        "investigation_questions": plan["investigation_questions"],
        "agent_responses": agent_responses,
        "nvidia_synthesis": synthesis,
    }

    recommendations = list(
        synthesis["recommended_actions"]
    )

    for response in agent_responses:
        recommendations.extend(
            response.get("recommendations", [])
        )

    return create_agent_response(
        task_id=task_id,
        agent="commander",
        status="success",
        findings=findings,
        metrics=metrics,
        recommendations=recommendations,
    )


