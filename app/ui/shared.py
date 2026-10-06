"""Shared UI helpers for AI Company OS."""

import html
import json

import altair as alt
import pandas as pd
import streamlit as st

from app.core.company_context import (
    company_name,
    get_active_company,
    get_company_dataset_analysis,
)
from app.database.db import (
    get_recent_analyses,
)


# ============================================================
# FINANCIAL DATA
# ============================================================

def financial_report():
    """
    Return financial data for the active company.

    Company Workspace is the source of truth for company data.
    Do not reconstruct or modify the verified analysis here.
    """

    company = get_active_company()

    if company.get("active"):
        analysis = get_company_dataset_analysis()

        if not analysis:
            return None

        return {
            "source": "company_workspace",
            "company": company_name(),
            "summary": analysis.get("metrics", {}),
            "monthly_breakdown": analysis.get(
                "breakdowns", {}
            ).get("monthly", []),
            "company_analysis": analysis,
        }

    analyses = get_recent_analyses(limit=20)

    if not analyses:
        return None

    return analyses[0]


def current_company_financial_data():
    """
    Return the exact verified company analysis.
    """

    company = get_active_company()

    if not company.get("active"):
        return None

    analysis = get_company_dataset_analysis()

    if not analysis:
        return None

    return {
        "source": "company_workspace",
        "company": company_name(),
        "summary": analysis.get("summary", {}),
        "monthly_breakdown": analysis.get(
            "monthly_breakdown",
            [],
        ),
        "company_analysis": analysis,
    }


# ============================================================
# KPI DISPLAY
# ============================================================

def _first_value(data, keys, default=None):
    """Return the first available value from a dictionary."""
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


def kpis(summary):
    """
    Render the main financial/company KPIs.

    Supports both the current company-analysis structure and
    older financial-analysis structures.
    """

    summary = summary or {}

    net_sales = _first_value(
        summary,
        [
            "net_sales",
            "revenue",
            "sales",
            "total_sales",
        ],
    )

    orders = _first_value(
        summary,
        [
            "orders",
            "order_count",
            "total_orders",
        ],
    )

    units = _first_value(
        summary,
        [
            "total_units",
            "units",
            "unit_count",
        ],
    )

    aov = _first_value(
        summary,
        [
            "average_order_value",
            "aov",
        ],
    )

    expenses = _first_value(
        summary,
        [
            "expenses",
            "total_expenses",
        ],
    )

    profit = _first_value(
        summary,
        [
            "profit",
            "net_profit",
        ],
    )

    discounts = _first_value(
        summary,
        [
            "discounts",
            "total_discounts",
        ],
    )

    discount_rate = _first_value(
        summary,
        [
            "discount_rate_pct",
            "discount_percentage",
        ],
    )

    columns = st.columns(4)

    # --------------------------------------------------------
    # Net Sales
    # --------------------------------------------------------

    if net_sales is None:
        columns[0].metric("Net Sales", "—")
    else:
        columns[0].metric(
            "Net Sales",
            f"${float(net_sales):,.0f}",
        )

    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    if orders is None:
        columns[1].metric("Orders", "—")
    else:
        columns[1].metric(
            "Orders",
            f"{int(orders):,}",
        )

    # --------------------------------------------------------
    # Units
    # --------------------------------------------------------

    if units is None:
        columns[2].metric("Units", "—")
    else:
        columns[2].metric(
            "Units",
            f"{int(units):,}",
        )

    # --------------------------------------------------------
    # AOV
    # --------------------------------------------------------

    if aov is None:
        columns[3].metric("AOV", "—")
    else:
        columns[3].metric(
            "AOV",
            f"${float(aov):,.2f}",
        )

    # --------------------------------------------------------
    # Optional financial fields
    # --------------------------------------------------------

    if expenses is not None or profit is not None:
        c1, c2 = st.columns(2)

        if expenses is not None:
            c1.metric(
                "Expenses",
                f"${float(expenses):,.0f}",
            )

        if profit is not None:
            c2.metric(
                "Profit",
                f"${float(profit):,.0f}",
            )

    if discounts is not None or discount_rate is not None:
        c1, c2 = st.columns(2)

        if discounts is not None:
            c1.metric(
                "Discounts",
                f"${float(discounts):,.0f}",
            )

        if discount_rate is not None:
            c2.metric(
                "Discount Rate",
                f"{float(discount_rate):.2f}%",
            )


# ============================================================
# FINANCIAL CHART
# ============================================================

def financial_chart(report):
    """
    Render the financial/performance timeline.

    Company Workspace currently provides monthly net sales.
    Expenses/profit are shown only when they genuinely exist.
    """

    if not report:
        st.info("No financial data available.")
        return

    data = pd.DataFrame(
        report.get("monthly_breakdown", [])
    )

    if data.empty:
        st.info("No monthly financial data available.")
        return

    if "month" not in data.columns:
        st.info("Monthly timeline is unavailable.")
        return

    data = data.copy()

    data["month"] = pd.to_datetime(
        data["month"],
        errors="coerce",
    )

    data = data.dropna(subset=["month"])

    if data.empty:
        st.info("No valid monthly financial data available.")
        return

    # --------------------------------------------------------
    # Determine available metrics
    # --------------------------------------------------------

    revenue_column = None

    for candidate in [
        "revenue",
        "net_sales",
        "sales",
    ]:
        if candidate in data.columns:
            revenue_column = candidate
            break

    expense_available = (
        "expenses" in data.columns
        and data["expenses"].notna().any()
    )

    profit_available = (
        "profit" in data.columns
        and data["profit"].notna().any()
    )

    # --------------------------------------------------------
    # Financial dataset with expenses
    # --------------------------------------------------------

    if revenue_column and expense_available:

        plot_columns = [
            revenue_column,
            "expenses",
        ]

        plot = data[
            ["month"] + plot_columns
        ].melt(
            id_vars=["month"],
            value_vars=plot_columns,
            var_name="metric",
            value_name="amount",
        )

        chart = (
            alt.Chart(plot)
            .mark_bar()
            .encode(
                x=alt.X(
                    "month:T",
                    title="Month",
                    axis=alt.Axis(format="%Y-%m"),
                ),
                y=alt.Y(
                    "amount:Q",
                    title="Amount ($)",
                ),
                xOffset="metric:N",
                color="metric:N",
                tooltip=[
                    alt.Tooltip(
                        "month:T",
                        title="Month",
                        format="%Y-%m",
                    ),
                    alt.Tooltip(
                        "metric:N",
                        title="Metric",
                    ),
                    alt.Tooltip(
                        "amount:Q",
                        title="Amount",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=360)
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

        return

    # --------------------------------------------------------
    # Profit available but no expenses
    # --------------------------------------------------------

    if revenue_column and profit_available:

        plot = data[
            ["month", revenue_column, "profit"]
        ].melt(
            id_vars=["month"],
            value_vars=[
                revenue_column,
                "profit",
            ],
            var_name="metric",
            value_name="amount",
        )

        chart = (
            alt.Chart(plot)
            .mark_line(point=True)
            .encode(
                x=alt.X(
                    "month:T",
                    title="Month",
                    axis=alt.Axis(format="%Y-%m"),
                ),
                y=alt.Y(
                    "amount:Q",
                    title="Amount ($)",
                ),
                color="metric:N",
                tooltip=[
                    alt.Tooltip(
                        "month:T",
                        title="Month",
                        format="%Y-%m",
                    ),
                    "metric:N",
                    alt.Tooltip(
                        "amount:Q",
                        title="Amount",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=360)
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

        return

    # --------------------------------------------------------
    # Company Workspace sales-only chart
    # --------------------------------------------------------

    if revenue_column:

        chart = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X(
                    "month:T",
                    title="Month",
                    axis=alt.Axis(format="%Y-%m"),
                ),
                y=alt.Y(
                    f"{revenue_column}:Q",
                    title="Net Sales ($)",
                ),
                tooltip=[
                    alt.Tooltip(
                        "month:T",
                        title="Month",
                        format="%Y-%m",
                    ),
                    alt.Tooltip(
                        f"{revenue_column}:Q",
                        title="Net Sales",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=360)
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

        return

    st.info("No supported financial metric is available for the chart.")


# ============================================================
# INVESTIGATION STATE
# ============================================================

def set_current_investigation(item):
    """Set the currently active investigation."""

    st.session_state["current_investigation"] = item


def current_investigation():
    """Return the currently active investigation."""

    return st.session_state.get(
        "current_investigation"
    )


def clear_current_investigation():
    """Clear the active investigation."""

    st.session_state.pop(
        "current_investigation",
        None,
    )


# ============================================================
# INVESTIGATION LOADING
# ============================================================

def _normalise_saved_investigation(item):
    """
    Convert a database analysis record into the structure
    expected by the Intelligence and Command Center pages.
    """

    if not item:
        return None

    result = item.get("result") or {}

    synthesis = (
        item.get("synthesis")
        or result.get("synthesis")
        or {}
    )

    if not isinstance(synthesis, dict):
        synthesis = {
            "executive_summary": str(synthesis),
            "key_insights": [],
            "risks": [],
            "recommended_actions": [],
        }

    return {
        "id": item.get("id"),
        "task_id": item.get("task_id"),
        "query": item.get(
            "query_text",
            item.get("query", ""),
        ),
        "result": result,
        "synthesis": synthesis,
        "timestamp": item.get(
            "created_at",
            item.get("timestamp"),
        ),
    }


def load_investigation_by_task(task_id):
    """
    Load an investigation from saved OS history by task ID.
    """

    if not task_id:
        return None

    analyses = get_recent_analyses(limit=100)

    for item in analyses:
        if item.get("task_id") == task_id:

            investigation = (
                _normalise_saved_investigation(item)
            )

            if investigation:
                set_current_investigation(
                    investigation
                )

            return investigation

    return None


def load_latest_investigation():
    """
    Load the latest saved investigation.
    """

    analyses = get_recent_analyses(limit=100)

    if not analyses:
        return None

    # Prefer the newest record that actually has a task ID.
    for item in analyses:
        if item.get("task_id"):

            investigation = (
                _normalise_saved_investigation(item)
            )

            if investigation:
                set_current_investigation(
                    investigation
                )

            return investigation

    return None


# ============================================================
# RUN INVESTIGATION
# ============================================================

def run_investigation(query):
    """
    Run the Commander investigation pipeline and save its result.
    """

    query = (query or "").strip()

    if not query:
        raise ValueError(
            "Investigation question cannot be empty."
        )

    from app.core.commander import run_commander_task
    from app.database.db import log_analysis
    from datetime import datetime, timezone

    task_id = (
        "investigation-"
        + datetime.now(timezone.utc).strftime(
            "%Y%m%d%H%M%S%f"
        )
    )

    response = run_commander_task(
        task_id=task_id,
        query=query,
    )

    if response is None:
        raise RuntimeError(
            "Commander returned no response."
        )

    # --------------------------------------------------------
    # Extract response fields safely
    # --------------------------------------------------------

    result = response

    if hasattr(response, "model_dump"):
        result = response.model_dump()

    elif hasattr(response, "dict"):
        result = response.dict()

    if not isinstance(result, dict):
        try:
            result = dict(result)
        except Exception:
            result = {
                "response": str(result)
            }

    metrics = result.get(
        "metrics",
        {},
    )

    findings = result.get(
        "findings",
        [],
    )

    recommendations = result.get(
        "recommendations",
        [],
    )

    # Commander stores the final Nemotron synthesis here.
    synthesis = metrics.get(
        "nvidia_synthesis"
    )

    if not isinstance(synthesis, dict):
        synthesis = {
            "executive_summary": "",
            "key_insights": [],
            "risks": [],
            "recommended_actions": recommendations,
        }

    # --------------------------------------------------------
    # Save investigation to database
    # --------------------------------------------------------

    log_analysis(
        query_text=query,
        metrics_calculated=metrics,
        insights=synthesis,
        model="NVIDIA Nemotron",
        tools_used={
            "source": "commander",
        },
        user_approval=0,
        result=result,
        synthesis=synthesis,
        task_id=task_id,
        context_type=(
            "company"
            if get_active_company().get("active")
            else "general"
        ),
    )

    # --------------------------------------------------------
    # Create active investigation
    # --------------------------------------------------------

    item = {
        "task_id": task_id,
        "query": query,
        "result": result,
        "synthesis": synthesis,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    set_current_investigation(item)

    return item


# ============================================================
# INVESTIGATION VIEW
# ============================================================

def _safe_text(value):
    """Safely convert arbitrary values to displayable text."""
    if value is None:
        return ""

    return html.escape(str(value))


def investigation_view(item):
    """
    Render the active investigation.
    """

    if not item:
        return

    synthesis = item.get(
        "synthesis",
        {},
    )

    if not isinstance(synthesis, dict):
        synthesis = {
            "executive_summary": str(synthesis),
            "key_insights": [],
            "risks": [],
            "recommended_actions": [],
        }

    st.subheader("Executive Intelligence")
    st.caption(
        "Commander → specialist agents → final synthesis"
    )

    summary = synthesis.get(
        "executive_summary",
        "No executive summary available.",
    )

    st.markdown(
        f"""
        <div class="panel panel-lime">
            <div class="eyebrow">EXECUTIVE SUMMARY</div>
            <p>{_safe_text(summary)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Key insights
    # --------------------------------------------------------

    insights = synthesis.get(
        "key_insights",
        synthesis.get(
            "key_findings",
            [],
        ),
    )

    if insights:
        st.markdown("### Key Insights")

        for insight in insights:
            st.markdown(
                f"- {_safe_text(insight)}"
            )

    # --------------------------------------------------------
    # Risks
    # --------------------------------------------------------

    risks = synthesis.get(
        "risks",
        [],
    )

    if risks:
        st.markdown("### Risks / Limitations")

        for risk in risks:
            st.markdown(
                f"- {_safe_text(risk)}"
            )

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    actions = synthesis.get(
        "recommended_actions",
        [],
    )

    if actions:
        st.markdown("### Recommended Actions")

        for index, action in enumerate(
            actions,
            start=1,
        ):
            st.markdown(
                f"{index}. {_safe_text(action)}"
            )

    # --------------------------------------------------------
    # Investigation metadata
    # --------------------------------------------------------

    query = item.get(
        "query",
        "",
    )

    if query:
        with st.expander(
            "Investigation question"
        ):
            st.write(query)

    # --------------------------------------------------------
    # Verified result data
    # --------------------------------------------------------

    result = item.get(
        "result",
        {},
    )

    if result:
        with st.expander(
            "Verified investigation data"
        ):
            st.json(result)