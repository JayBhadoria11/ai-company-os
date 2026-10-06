import streamlit as st
import pandas as pd
import altair as alt

from app.ui.theme import page_header
from app.ui.shared import (
    financial_report,
    kpis,
    current_company_financial_data,
)


# ============================================================
# MONTHLY FINANCIAL VISUALS
# ============================================================

def _render_financial_visuals(report):

    data = pd.DataFrame(
        report.get(
            "monthly_breakdown",
            [],
        )
    )

    if data.empty:

        st.info(
            "No monthly financial data is connected yet."
        )

        return

    if "month" in data.columns:

        data["month"] = pd.to_datetime(
            data["month"],
            errors="coerce",
        )

    # ========================================================
    # CHART
    # ========================================================

    st.markdown(
        "### Monthly Performance"
    )

    # Company analysis emits monthly sales as `sales`; legacy reports may
    # use `revenue`. Normalize the display layer without changing evidence.
    if "sales" in data.columns and "revenue" not in data.columns:
        data["revenue"] = data["sales"]

    has_expenses = (
        "expenses" in data.columns
        and data["expenses"].notna().any()
    )

    if has_expenses:

        value_columns = [
            column
            for column in [
                "revenue",
                "expenses",
                "profit",
            ]
            if column in data.columns
            and data[column].notna().any()
        ]

        plot = data.melt(
            id_vars=["month"],
            value_vars=value_columns,
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
            .properties(
                height=360,
            )
        )

    else:

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
                    "revenue:Q",
                    title="Net Sales ($)",
                ),
                tooltip=[
                    alt.Tooltip(
                        "month:T",
                        title="Month",
                        format="%Y-%m",
                    ),
                    alt.Tooltip(
                        "revenue:Q",
                        title="Net Sales",
                        format=",.0f",
                    ),
                ],
            )
            .properties(
                height=360,
            )
        )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    # ========================================================
    # MONTHLY TABLE
    # ========================================================

    st.markdown(
        "### Monthly Financial Data"
    )

    display = data.copy()

    # `revenue` is only a chart compatibility alias for verified `sales`;
    # keep the table to one financial column.
    if "sales" in display.columns and "revenue" in display.columns:
        display = display.drop(columns=["revenue"])

    if "month" in display.columns:

        display["month"] = display["month"].dt.strftime("%Y-%m")

    rename = {
        "month": "Month",
        "revenue": "Net Sales ($)",
        "sales": "Net Sales ($)",
        "expenses": "Expenses",
        "profit": "Profit",
        "profit_margin_pct": "Profit Margin %",
        "revenue_growth_pct": "Growth %",
    }

    display = display.rename(
        columns=rename
    )

    numeric_cols = [
        column
        for column in display.columns
        if column != "Month"
    ]

    for column in numeric_cols:

        display[column] = pd.to_numeric(
            display[column],
            errors="coerce",
        ).round(2)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# VERIFIED COMPANY TABLES
# ============================================================

def _render_company_breakdowns(analysis):

    breakdowns = analysis.get(
        "breakdowns",
        {},
    )

    # ========================================================
    # PRODUCT PERFORMANCE
    # ========================================================

    products = breakdowns.get(
        "products",
        [],
    )

    if products:

        st.markdown(
            "### Product Performance"
        )

        product_df = pd.DataFrame(
            products
        )

        st.dataframe(
            product_df,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # REGION PERFORMANCE
    # ========================================================

    regions = breakdowns.get(
        "regions",
        [],
    )

    if regions:

        st.markdown(
            "### Regional Performance"
        )

        region_df = pd.DataFrame(
            regions
        )

        st.dataframe(
            region_df,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # MARKETING CHANNEL PERFORMANCE
    # ========================================================

    channels = breakdowns.get(
        "channels",
        [],
    )

    if channels:

        st.markdown(
            "### Marketing Channel Performance"
        )

        channel_df = pd.DataFrame(
            channels
        )

        st.dataframe(
            channel_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# VERIFIED METRICS
# ============================================================

def _render_verified_metrics(analysis):

    metrics = analysis.get(
        "metrics",
        {},
    )

    if not metrics:
        return

    st.markdown(
        "### Verified Company Metrics"
    )

    metric_rows = []

    metric_definitions = [
        (
            "Net Sales",
            metrics.get("net_sales"),
            "currency",
        ),
        (
            "Orders",
            metrics.get("orders"),
            "integer",
        ),
        (
            "Units",
            metrics.get("total_units"),
            "integer",
        ),
        (
            "Average Order Value",
            metrics.get("average_order_value"),
            "currency2",
        ),
        (
            "Total Discounts",
            metrics.get("discounts"),
            "currency",
        ),
    ]

    # Only show unavailable financial fields when they
    # actually exist in the uploaded dataset.
    if metrics.get("expenses") is not None:

        metric_definitions.append(
            (
                "Expenses",
                metrics.get("expenses"),
                "currency",
            )
        )

    if metrics.get("profit") is not None:

        metric_definitions.append(
            (
                "Profit",
                metrics.get("profit"),
                "currency",
            )
        )

    for label, value, value_type in metric_definitions:

        if value is None:
            continue

        try:

            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if value_type == "currency":

            display_value = (
                f"${numeric_value:,.0f}"
            )

        elif value_type == "currency2":

            display_value = (
                f"${numeric_value:,.2f}"
            )

        else:

            display_value = (
                f"{int(numeric_value):,}"
            )

        metric_rows.append(
            {
                "Metric": label,
                "Value": display_value,
            }
        )

    if metric_rows:

        st.dataframe(
            pd.DataFrame(
                metric_rows
            ),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MAIN PAGE
# ============================================================

def render():

    page_header(
        "FINANCIALS",
        "Financial intelligence",
        "Verified financial and sales signals generated from the active Company Workspace.",
    )

    report = financial_report()

    if not report:

        st.info(
            "No financial dataset is connected. "
            "Go to Company Workspace and upload your sales or finance data."
        )

        return

    # ========================================================
    # COMPANY WORKSPACE
    # ========================================================

    if report.get(
        "source"
    ) == "company_workspace":

        company = report.get(
            "company",
            "Company",
        )

        st.success(
            f"LIVE COMPANY DATA · {company}"
        )

        # ----------------------------------------------------
        # MAIN KPI CARDS
        # ----------------------------------------------------

        kpis(
            report.get(
                "summary",
                {},
            )
        )

        analysis = report.get(
            "company_analysis",
            {},
        )

        metrics = analysis.get(
            "metrics",
            {},
        )

        # ----------------------------------------------------
        # SECONDARY METRICS
        # ----------------------------------------------------

        c1, c2, c3 = st.columns(3)

        with c1:

            discounts = metrics.get(
                "discounts"
            )

            st.metric(
                "Discounts",
                (
                    f"${float(discounts):,.0f}"
                    if discounts is not None
                    else "—"
                ),
            )

        with c2:

            discount_rate = metrics.get(
                "discount_rate_pct"
            )

            if discount_rate is None:

                st.metric(
                    "Discount Rate",
                    "—",
                )

            else:

                st.metric(
                    "Discount Rate",
                    f"{float(discount_rate):.2f}%",
                )

        with c3:

            rows = analysis.get("rows")
            if rows is None:
                rows = metrics.get("data_rows")

            st.metric(
                "Data Rows",
                (
                    f"{int(rows):,}"
                    if rows is not None
                    else "—"
                ),
            )

        st.caption(
            "All figures below are generated from the verified company workspace dataset. "
            "Profit, expenses, CAC, ROI and margin remain unavailable unless the uploaded "
            "dataset contains the required fields."
        )

        # ----------------------------------------------------
        # VERIFIED METRICS
        # ----------------------------------------------------

        _render_verified_metrics(
            analysis
        )

        # ----------------------------------------------------
        # MONTHLY PERFORMANCE
        # ----------------------------------------------------

        _render_financial_visuals(
            report
        )

        # ----------------------------------------------------
        # PRODUCT / REGION / CHANNEL TABLES
        # ----------------------------------------------------

        _render_company_breakdowns(
            analysis
        )

        # ----------------------------------------------------
        # VERIFIED BUSINESS SIGNALS
        # ----------------------------------------------------

        insights = analysis.get(
            "insights",
            [],
        )

        if insights:

            st.markdown(
                "### Verified Business Signals"
            )

            for insight in insights:

                if insight:

                    st.markdown(
                        f"- {insight}"
                    )

        return

    # ========================================================
    # LEGACY / FULL FINANCIAL DATA
    # ========================================================

    kpis(
        report.get(
            "summary",
            {},
        )
    )

    _render_financial_visuals(
        report
    )