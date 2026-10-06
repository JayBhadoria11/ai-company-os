"""Evidence classification and reasoning cleanup for the Intelligence layer.

This module converts the deterministic per-dataset evidence gathered by
``company_context.build_company_dataset_evidence`` into a labelled reasoning
pack that separates:

1. VERIFIED FACT
2. CALCULATED SCENARIO / ASSUMPTION
3. INFERENCE
4. LIMITATION / UNKNOWN
5. RECOMMENDATION

It also produces question-aware key insights and a deterministic executive
summary draft. Nothing here is fabricated: every statement is built from
metrics that the deterministic analyzers actually produced, and gaps are
reported as limitations.
"""

import re


SALES_DOMAINS = {"sales", "financial", "generic"}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "unavailable"


def _compact_money(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unavailable"

    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:,.0f}"


def _number(value):
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Query parsing
# ---------------------------------------------------------------------------

_GROWTH_PATTERNS = [
    r"increase\s+(?:our\s+)?(?:sales|revenue)\s+by\s+(\d+(?:\.\d+)?)\s*%",
    r"grow\s+(?:sales|revenue)?\s*by\s+(\d+(?:\.\d+)?)\s*%",
    r"(\d+(?:\.\d+)?)\s*%\s+(?:increase|growth)",
    r"(\d+(?:\.\d+)?)\s*%\s+(?:in|of)\s+(?:sales|revenue)",
]


def parse_growth_pct(query):
    """Return the requested growth percentage if the question specifies one."""

    text = str(query or "")

    for pattern in _GROWTH_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except (TypeError, ValueError):
                continue

    return None


# ---------------------------------------------------------------------------
# Evidence extraction
# ---------------------------------------------------------------------------

def _find_sales_evidence(evidence):
    for filename, payload in (evidence or {}).items():
        if payload.get("domain") not in SALES_DOMAINS:
            continue

        data = payload.get("evidence", {}) or {}
        metrics = data.get("metrics", {}) or {}

        if metrics.get("net_sales") is not None:
            return filename, data, metrics

    return None, {}, {}


def _find_workforce_evidence(evidence):
    items = []

    for filename, payload in (evidence or {}).items():
        if payload.get("domain") != "workforce":
            continue
        items.append((filename, payload.get("evidence", {}) or {}))

    return items


def _sales_department(workforce):
    for department in workforce.get("departments", []) or []:
        if "sales" in str(department.get("name", "")).lower():
            return department
    return None


_SCENARIO_TOKENS = [
    "what if", "what-if", "scenario", "forecast", "projected", "projection",
    "required orders", "future sales", "sales target", "revenue target",
    "growth target", "increase sales", "increase revenue",
]


def asks_for_scenario(query):
    """True only when the user explicitly asks for a scenario/forecast."""

    lower = str(query or "").lower()
    return any(token in lower for token in _SCENARIO_TOKENS)


def _sales_intent(query):
    """Detect which sales dimensions a question asks about."""

    lower = str(query or "").lower()

    return {
        "regions": any(
            token in lower
            for token in ["region", "regional", "geograph", "territor"]
        ),
        "products": any(
            token in lower
            for token in ["product", "item", "sku", "category", "segment"]
        ),
        "time": any(
            token in lower
            for token in [
                "time", "month", "monthly", "period", "trend", "season",
                "temporal",
            ]
        ),
        "weak": any(
            token in lower
            for token in [
                "weak", "underperform", "under-perform", "declin", "worst",
                "low", "poor", "lag", "bottom",
            ]
        ),
        "strong": any(
            token in lower
            for token in [
                "strong", "best", "top", "highest", "growth", "perform",
            ]
        ),
        "patterns": any(
            token in lower for token in ["pattern", "strongest", "weakest"]
        ),
    }


def _build_sales_pattern(sales_data):
    """Extract strongest/weakest region, product and time patterns."""

    regions = [
        region for region in (sales_data.get("regions") or [])
        if region.get("name") is not None
    ]
    products = [
        product for product in (sales_data.get("products") or [])
        if product.get("name") is not None
    ]
    monthly = [
        month for month in (sales_data.get("monthly") or [])
        if month.get("sales") is not None
    ]
    declining = sales_data.get("declining") or {}

    strongest_region = regions[0] if regions else None
    weakest_region = regions[-1] if len(regions) >= 2 else None

    strongest_product = products[0] if products else None

    weakest_product = None
    declining_products = declining.get("products") or []

    if declining_products:
        weakest_product = min(
            declining_products,
            key=lambda item: (
                item.get("change_pct")
                if item.get("change_pct") is not None
                else 0
            ),
        )
    elif len(products) >= 2:
        weakest_product = products[-1]

    declining_regions = declining.get("regions") or []
    weakest_declining_region = None
    if declining_regions:
        weakest_declining_region = min(
            declining_regions,
            key=lambda item: (
                item.get("change_pct")
                if item.get("change_pct") is not None
                else 0
            ),
        )

    strongest_month = None
    weakest_month = None
    trend_change_pct = None

    if monthly:
        strongest_month = max(monthly, key=lambda item: float(item["sales"]))
        weakest_month = min(monthly, key=lambda item: float(item["sales"]))

        if len(monthly) >= 2:
            first = float(monthly[0]["sales"])
            last = float(monthly[-1]["sales"])
            if first:
                trend_change_pct = round((last - first) / first * 100, 2)

    return {
        "regions": regions,
        "products": products,
        "monthly": monthly,
        "strongest_region": strongest_region,
        "weakest_region": weakest_region,
        "strongest_product": strongest_product,
        "weakest_product": weakest_product,
        "weakest_declining_region": weakest_declining_region,
        "strongest_month": strongest_month,
        "weakest_month": weakest_month,
        "trend_change_pct": trend_change_pct,
    }


def _build_sales_recommendations(sales_pattern):
    """Question-specific recommendation for sales-pattern investigations."""

    weakest_region = sales_pattern.get("weakest_region")
    weakest_product = sales_pattern.get("weakest_product")
    strongest_month = sales_pattern.get("strongest_month")

    targets = []
    if weakest_region:
        targets.append(f"{weakest_region['name']} region underperformance")
    if weakest_product:
        targets.append(
            f"the underperforming product segment ({weakest_product.get('name')})"
        )

    if targets:
        statement = "Investigate the drivers of " + " and ".join(targets)
    else:
        statement = "Investigate regional, product, and time-based sales performance"

    if strongest_month:
        statement += (
            f", then assess the strongest monthly sales period "
            f"({strongest_month.get('month')}) for repeatable growth patterns."
        )
    else:
        statement += " to identify repeatable growth patterns."

    return [
        {
            "statement": statement,
            "reason": "Derived from the strongest/weakest deterministic sales patterns.",
            "supporting_steps": [
                "Compare regional demand drivers.",
                "Review underperforming product margins and volumes.",
                "Validate whether the strongest period is repeatable.",
            ],
        }
    ]


# ---------------------------------------------------------------------------
# Reasoning pack
# ---------------------------------------------------------------------------

def build_reasoning_pack(query, combined):
    """Build the labelled evidence taxonomy for a company investigation."""

    combined = combined or {}
    evidence = combined.get("evidence", {}) or {}
    datasets_used = combined.get("datasets_used", []) or []

    has_workforce = any(d.get("domain") == "workforce" for d in datasets_used)
    has_sales = any(d.get("domain") in SALES_DOMAINS for d in datasets_used)

    growth_pct = parse_growth_pct(query)

    sales_filename, sales_data, sales_metrics = _find_sales_evidence(evidence)
    workforce_items = _find_workforce_evidence(evidence)

    net_sales = sales_metrics.get("net_sales")
    orders = sales_metrics.get("orders")
    aov = sales_metrics.get("average_order_value")

    verified_facts = []
    calculated_results = []
    calculated_scenario = None
    inferences = []
    limitations = []
    recommendations = []
    key_insights = []
    provenance = []

    intent = _sales_intent(query)

    wants_sales_pattern = has_sales and (
        intent["patterns"]
        or intent["time"]
        or intent["weak"]
        or (intent["regions"] and intent["products"])
    )

    sales_pattern = (
        _build_sales_pattern(sales_data) if wants_sales_pattern else None
    )

    def add_fact(statement, source):
        verified_facts.append(
            {
                "label": "VERIFIED FACT",
                "statement": statement,
                "source_dataset": source,
            }
        )
        if source and source not in provenance:
            provenance.append(source)

    # ------------------------------------------------------------------
    # VERIFIED FACTS — sales
    # ------------------------------------------------------------------
    if has_sales and net_sales is not None:
        add_fact(
            f"Current verified net sales are {_money(net_sales)} "
            f"({_compact_money(net_sales)}).",
            sales_filename,
        )

    if has_sales and orders is not None:
        add_fact(
            f"The sales dataset records {_number(orders)} orders.",
            sales_filename,
        )

    if has_sales and aov is not None:
        add_fact(
            f"Average order value is {_money(aov)}.",
            sales_filename,
        )

    # ------------------------------------------------------------------
    # VERIFIED FACTS — workforce
    # ------------------------------------------------------------------
    primary_workforce = None
    for filename, workforce in workforce_items:
        if primary_workforce is None:
            primary_workforce = (filename, workforce)

        headcount = workforce.get("headcount")
        attrition = workforce.get("attrition")
        overtime = workforce.get("overtime")

        if headcount is not None:
            add_fact(
                f"The HR dataset represents {_number(headcount)} employees.",
                filename,
            )

        if attrition:
            add_fact(
                f"The HR dataset records {_number(attrition.get('employees_left'))} "
                f"employees with attrition, representing "
                f"{attrition.get('attrition_rate_pct')}% of the workforce.",
                filename,
            )

        department = _sales_department(workforce)
        if department:
            rate = department.get("attrition_rate_pct")
            count = department.get("headcount")
            recorded_attrition = None
            if rate is not None and count:
                recorded_attrition = round(float(count) * float(rate) / 100)
            detail = (
                f"The Sales department has {_number(count)} employees and a "
                f"recorded attrition rate of {rate}%"
            )
            if recorded_attrition is not None:
                detail += (
                    f" (approximately {_number(recorded_attrition)} employees "
                    f"in the dataset)"
                )
            add_fact(detail + ".", filename)

        if overtime:
            add_fact(
                f"{overtime.get('overtime_rate_pct')}% of employees are recorded "
                f"as working overtime. This is a workforce risk indicator, not "
                f"proof of insufficient capacity.",
                filename,
            )

    # ------------------------------------------------------------------
    # SALES PATTERNS (calculated results — question-aware)
    # ------------------------------------------------------------------
    if sales_pattern:
        strongest_region = sales_pattern.get("strongest_region")
        weakest_region = sales_pattern.get("weakest_region")
        strongest_product = sales_pattern.get("strongest_product")
        weakest_product = sales_pattern.get("weakest_product")
        strongest_month = sales_pattern.get("strongest_month")
        weakest_month = sales_pattern.get("weakest_month")
        trend = sales_pattern.get("trend_change_pct")

        def add_result(statement):
            calculated_results.append(
                {
                    "label": "CALCULATED RESULT",
                    "statement": statement,
                    "source_dataset": sales_filename,
                }
            )

        if strongest_region:
            key_insights.append(
                {
                    "title": "STRONGEST REGION",
                    "statement": (
                        f"{strongest_region['name']} is the strongest region at "
                        f"{_money(strongest_region.get('sales'))}."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )

        if weakest_region:
            key_insights.append(
                {
                    "title": "WEAKEST REGION",
                    "statement": (
                        f"{weakest_region['name']} is the weakest region at "
                        f"{_money(weakest_region.get('sales'))}."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )
            add_result(
                f"{weakest_region['name']} is the lowest net-sales region at "
                f"{_money(weakest_region.get('sales'))}."
            )

        if strongest_product:
            key_insights.append(
                {
                    "title": "STRONGEST PRODUCT",
                    "statement": (
                        f"{strongest_product['name']} is the strongest product at "
                        f"{_money(strongest_product.get('sales'))}."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )

        if weakest_product:
            statement = f"{weakest_product.get('name')} is the weakest product"
            if weakest_product.get("latest_month_sales") is not None:
                statement = (
                    f"{weakest_product.get('name')} declined from "
                    f"{_money(weakest_product.get('first_month_sales'))} to "
                    f"{_money(weakest_product.get('latest_month_sales'))} "
                    f"({weakest_product.get('change_pct')}%)"
                )
            else:
                statement += f" at {_money(weakest_product.get('sales'))}"

            key_insights.append(
                {
                    "title": "UNDERPERFORMING PRODUCT",
                    "statement": statement + ".",
                    "label": "CALCULATED RESULT",
                    "source_dataset": sales_filename,
                }
            )
            add_result(statement + ".")

        if strongest_month and weakest_month:
            key_insights.append(
                {
                    "title": "TIME PATTERN",
                    "statement": (
                        f"Sales peak in {strongest_month.get('month')} "
                        f"({_money(strongest_month.get('sales'))}) and are weakest "
                        f"in {weakest_month.get('month')} "
                        f"({_money(weakest_month.get('sales'))})."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )

        if trend is not None:
            add_result(
                f"Monthly net sales change from "
                f"{_money(sales_pattern['monthly'][0].get('sales'))} in "
                f"{sales_pattern['monthly'][0].get('month')} to "
                f"{_money(sales_pattern['monthly'][-1].get('sales'))} in "
                f"{sales_pattern['monthly'][-1].get('month')} ({trend}%)."
            )

    # ------------------------------------------------------------------
    # CALCULATED SCENARIO
    # ------------------------------------------------------------------
    if growth_pct is not None and net_sales is not None:
        projected_sales = float(net_sales) * (1 + growth_pct / 100)
        statements = [
            f"A {growth_pct:g}% increase in sales would raise current sales of "
            f"{_money(net_sales)} to approximately {_money(projected_sales)}."
        ]
        assumptions = [
            "Average order value remains approximately constant.",
            "The projection is a deterministic arithmetic scenario, not a forecast.",
        ]

        if aov:
            projected_orders = projected_sales / float(aov)
            statements.append(
                f"At the current average order value of {_money(aov)}, this "
                f"corresponds to approximately {_number(projected_orders)} orders."
            )
            assumptions.append(
                "The order estimate assumes the sales mix and average order value "
                "do not change."
            )

        calculated_scenario = {
            "label": "CALCULATED SCENARIO",
            "growth_pct": growth_pct,
            "current_sales": round(float(net_sales), 2),
            "projected_sales": round(projected_sales, 2),
            "statements": statements,
            "assumptions": assumptions,
            "source_dataset": sales_filename,
        }

    # ------------------------------------------------------------------
    # INFERENCE
    # ------------------------------------------------------------------
    if has_workforce:
        inferences.append(
            {
                "label": "INFERENCE",
                "statement": (
                    "The available evidence indicates meaningful workforce "
                    "capacity risks."
                ),
                "basis": "Recorded attrition and overtime rates in the HR dataset.",
            }
        )
        inferences.append(
            {
                "label": "INFERENCE",
                "statement": (
                    "Employee productivity, workload per employee, and the direct "
                    "relationship between headcount and order volume are not "
                    "measured, so workforce capacity cannot be linked to order "
                    "volume with certainty."
                ),
                "basis": "No shared capacity/productivity-to-order dimension exists "
                "across the connected datasets.",
            }
        )

    # ------------------------------------------------------------------
    # LIMITATIONS / UNKNOWN
    # ------------------------------------------------------------------
    if has_workforce and growth_pct is not None:
        limitations.append(
            {
                "label": "LIMITATION",
                "statement": (
                    f"The current datasets are insufficient to determine "
                    f"definitively whether the existing workforce can support a "
                    f"{growth_pct:g}% sales increase."
                ),
            }
        )

    if has_workforce:
        limitations.append(
            {
                "label": "LIMITATION",
                "statement": (
                    "Attrition is recorded as a static count/rate in the HR dataset; "
                    "there is no time dimension, so it cannot be expressed as an "
                    "annual or per-year forecast."
                ),
            }
        )

    if has_sales:
        for item in sales_data.get("limitations", []) or []:
            limitations.append({"label": "LIMITATION", "statement": item})

    # ------------------------------------------------------------------
    # RECOMMENDATION (question-aware, evidence-grounded)
    # ------------------------------------------------------------------
    if has_workforce:
        department = _sales_department(primary_workforce[1]) if primary_workforce else None
        sales_rate = department.get("attrition_rate_pct") if department else None

        if sales_rate is not None:
            recommendations.append(
                {
                    "statement": (
                        "Conduct Sales workforce capacity and retention planning "
                        f"because the Sales department records {sales_rate}% attrition."
                    ),
                    "reason": (
                        f"The Sales department records {sales_rate}% attrition."
                    ),
                    "supporting_steps": [
                        "Measure workload per Sales employee.",
                        "Identify roles with elevated attrition.",
                        "Measure overtime by department.",
                        "Estimate staffing requirements using actual productivity "
                        "and capacity data.",
                        "Evaluate retention interventions.",
                    ],
                }
            )
        else:
            recommendations.append(
                {
                    "statement": (
                        "Conduct workforce capacity and retention planning."
                    ),
                    "reason": "Recorded attrition and overtime indicate capacity risk.",
                    "supporting_steps": [
                        "Measure workload per employee.",
                        "Measure overtime by department.",
                        "Estimate staffing requirements using actual productivity "
                        "and capacity data.",
                    ],
                }
            )

        recommendations.append(
            {
                "statement": (
                    "Assess other departments using workload, productivity, and "
                    "capacity data before committing to additional hiring."
                ),
                "reason": (
                    "Department size alone does not establish a hiring requirement."
                ),
                "supporting_steps": [],
            }
        )
    elif sales_pattern:
        recommendations.extend(_build_sales_recommendations(sales_pattern))
    else:
        recommendations.append(
            {
                "statement": "Monitor expenses.",
                "reason": "Sales and cost evidence is available.",
                "supporting_steps": [],
            }
        )
        recommendations.append(
            {
                "statement": "Review the drivers of sales and profitability.",
                "reason": "Current verified sales evidence is available.",
                "supporting_steps": [],
            }
        )

    # ------------------------------------------------------------------
    # QUESTION-AWARE KEY INSIGHTS
    # ------------------------------------------------------------------
    if calculated_scenario:
        key_insights.append(
            {
                "title": "GROWTH TARGET",
                "statement": calculated_scenario["statements"][0],
                "label": "CALCULATED SCENARIO",
                "source_dataset": sales_filename,
            }
        )

    if primary_workforce:
        filename, workforce = primary_workforce
        headcount = workforce.get("headcount")
        attrition = workforce.get("attrition")

        if headcount is not None and attrition:
            key_insights.append(
                {
                    "title": "WORKFORCE",
                    "statement": (
                        f"{_number(headcount)} employees are represented in the HR "
                        f"dataset, with {_number(attrition.get('employees_left'))} "
                        f"recorded attritions "
                        f"({attrition.get('attrition_rate_pct')}%)."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": filename,
                }
            )

        department = _sales_department(workforce)
        if department:
            key_insights.append(
                {
                    "title": "SALES WORKFORCE RISK",
                    "statement": (
                        f"Sales has {_number(department.get('headcount'))} employees "
                        f"and a recorded attrition rate of "
                        f"{department.get('attrition_rate_pct')}%."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": filename,
                }
            )

        overtime = workforce.get("overtime")
        if overtime:
            key_insights.append(
                {
                    "title": "OVERTIME",
                    "statement": (
                        f"{overtime.get('overtime_rate_pct')}% of employees are "
                        f"recorded as working overtime."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": filename,
                }
            )

        if growth_pct is not None:
            key_insights.append(
                {
                    "title": "EVIDENCE GAP",
                    "statement": (
                        "The datasets do not contain a direct "
                        "employee-capacity/productivity-to-order-volume relationship."
                    ),
                    "label": "LIMITATION",
                    "source_dataset": None,
                }
            )

    # Complement non-pattern sales questions with a couple of relevant facts.
    if has_sales and not sales_pattern:
        regions = sales_data.get("regions", []) or []
        products = sales_data.get("products", []) or []

        if regions and len(key_insights) < 6:
            key_insights.append(
                {
                    "title": "TOP REGION",
                    "statement": (
                        f"{regions[0].get('name')} is the highest net-sales region "
                        f"at {_money(regions[0].get('sales'))}."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )

        if products and len(key_insights) < 6:
            key_insights.append(
                {
                    "title": "TOP PRODUCT",
                    "statement": (
                        f"{products[0].get('name')} is the highest net-sales product "
                        f"at {_money(products[0].get('sales'))}."
                    ),
                    "label": "VERIFIED FACT",
                    "source_dataset": sales_filename,
                }
            )

    # ------------------------------------------------------------------
    # EXECUTIVE SUMMARY DRAFT
    # ------------------------------------------------------------------
    executive_summary_draft = _build_executive_summary(
        growth_pct=growth_pct,
        net_sales=net_sales,
        aov=aov,
        calculated_scenario=calculated_scenario,
        primary_workforce=primary_workforce,
        sales_pattern=sales_pattern,
    )

    all_limitations = []
    seen_limitations = set()

    for item in list(limitations) + [
        {"label": "LIMITATION", "statement": statement}
        for statement in (combined.get("limitations", []) or [])
    ]:
        statement = item.get("statement")
        if not statement or statement in seen_limitations:
            continue
        seen_limitations.add(statement)
        all_limitations.append(item)

    return {
        "question": query,
        "growth_pct": growth_pct,
        "asks_for_scenario": asks_for_scenario(query),
        "verified_facts": verified_facts,
        "calculated_results": calculated_results,
        "calculated_scenario": calculated_scenario,
        "inferences": inferences,
        "limitations": all_limitations,
        "recommendations": recommendations,
        "key_insights": key_insights,
        "sales_pattern": sales_pattern,
        "executive_summary_draft": executive_summary_draft,
        "provenance": provenance or [d.get("filename") for d in datasets_used],
    }


def _build_executive_summary(
    growth_pct,
    net_sales,
    aov,
    calculated_scenario,
    primary_workforce,
    sales_pattern=None,
):
    """Compose a deterministic, uncertainty-preserving executive summary."""

    parts = []

    if net_sales is not None:
        parts.append(f"Current verified sales are {_money(net_sales)}.")

    if calculated_scenario:
        parts.append(
            f"A {growth_pct:g}% increase would bring sales to approximately "
            f"{_money(calculated_scenario['projected_sales'])}; at the current "
            f"average order value of {_money(aov)}, this corresponds to roughly "
            f"{_number(calculated_scenario['projected_sales'] / float(aov))} "
            f"orders as a scenario."
        )

    if sales_pattern:
        strongest_region = sales_pattern.get("strongest_region")
        weakest_region = sales_pattern.get("weakest_region")
        strongest_product = sales_pattern.get("strongest_product")
        weakest_product = sales_pattern.get("weakest_product")
        strongest_month = sales_pattern.get("strongest_month")
        weakest_month = sales_pattern.get("weakest_month")
        trend = sales_pattern.get("trend_change_pct")

        if strongest_region and weakest_region:
            parts.append(
                f"{strongest_region['name']} is the strongest region "
                f"({_money(strongest_region.get('sales'))}) while "
                f"{weakest_region['name']} is the weakest "
                f"({_money(weakest_region.get('sales'))})."
            )
        elif strongest_region:
            parts.append(
                f"{strongest_region['name']} is the strongest region "
                f"({_money(strongest_region.get('sales'))})."
            )

        if strongest_product and weakest_product:
            parts.append(
                f"{strongest_product['name']} is the strongest product "
                f"({_money(strongest_product.get('sales'))}), while "
                f"{weakest_product.get('name')} is the weakest/underperforming "
                f"product segment."
            )
        elif strongest_product:
            parts.append(
                f"{strongest_product['name']} is the strongest product "
                f"({_money(strongest_product.get('sales'))})."
            )

        if strongest_month and weakest_month:
            sentence = (
                f"Sales peak in {strongest_month.get('month')} "
                f"({_money(strongest_month.get('sales'))}) and are weakest in "
                f"{weakest_month.get('month')} "
                f"({_money(weakest_month.get('sales'))})"
            )
            if trend is not None:
                sentence += f", a {trend}% change from first to last period"
            parts.append(sentence + ".")

        parts.append(
            "Management should investigate the drivers of the weakest region "
            "and underperforming product segment first, then assess whether the "
            "strongest sales period is repeatable."
        )

    if primary_workforce:
        _, workforce = primary_workforce
        attrition = workforce.get("attrition") or {}
        overtime = workforce.get("overtime") or {}
        department = _sales_department(workforce) or {}

        workforce_sentence = []
        if attrition.get("attrition_rate_pct") is not None:
            workforce_sentence.append(
                f"{attrition.get('attrition_rate_pct')}% attrition"
            )
        if overtime.get("overtime_rate_pct") is not None:
            workforce_sentence.append(
                f"{overtime.get('overtime_rate_pct')}% overtime participation"
            )
        if department.get("attrition_rate_pct") is not None:
            workforce_sentence.append(
                f"Sales showing {department.get('attrition_rate_pct')}% recorded "
                f"attrition"
            )

        if workforce_sentence:
            parts.append(
                "The HR dataset records " + ", ".join(workforce_sentence) + "."
            )

        parts.append(
            "These are meaningful capacity-risk indicators, but the available "
            "data does not establish whether the existing workforce can "
            "definitively support the additional order volume because employee "
            "productivity and workload capacity are not directly measured."
        )

        parts.append(
            "Management should prioritize Sales retention and workforce-capacity "
            "analysis before committing to a specific hiring target."
        )

    if not parts:
        return ""

    return " ".join(parts)


def key_insight_strings(reasoning):
    """Format question-aware insights as display strings for the UI."""

    strings = []

    for insight in reasoning.get("key_insights", []) or []:
        title = insight.get("title")
        statement = insight.get("statement")
        if title and statement:
            strings.append(f"{title}: {statement}")
        elif statement:
            strings.append(statement)

    return strings


def recommendation_strings(reasoning):
    """Format recommended actions as display strings."""

    strings = []

    for recommendation in reasoning.get("recommendations", []) or []:
        statement = recommendation.get("statement")
        if statement:
            strings.append(statement)

    return strings
