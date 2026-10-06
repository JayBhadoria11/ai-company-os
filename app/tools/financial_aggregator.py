"""Aggregate company financial data into structured business metrics."""

from app.tools.data_loader import load_financial_data
from app.tools.financial import (
    calculate_profit,
    calculate_profit_margin,
    calculate_growth_rate,
)
from app.tools.business_analytics import (
    analyze_revenue_trend,
    analyze_expense_ratio,
)


def _company_financial_report():
    """
    Build a financial-style report from the active company workspace.

    Company sales datasets do NOT automatically contain:
    - expenses
    - profit
    - profit margin
    - CAC
    - ROI

    Those values remain unavailable rather than being fabricated.
    """

    from app.core.company_context import (
        get_active_company,
        get_company_dataset_analysis,
    )

    ctx = get_active_company()

    if not ctx.get("active"):
        return None

    analysis = get_company_dataset_analysis()

    if not analysis:
        return None

    metrics = analysis.get(
        "metrics",
        {},
    )

    breakdowns = analysis.get(
        "breakdowns",
        {},
    )

    monthly = breakdowns.get(
        "monthly",
        [],
    )

    # ---------------------------------------------------------
    # Overall sales metrics
    # ---------------------------------------------------------

    total_revenue = float(
        metrics.get(
            "net_sales",
            0,
        )
        or 0
    )

    orders = int(
        metrics.get(
            "orders",
            0,
        )
        or 0
    )

    total_units = int(
        metrics.get(
            "total_units",
            0,
        )
        or 0
    )

    average_order_value = float(
        metrics.get(
            "average_order_value",
            0,
        )
        or 0
    )

    raw_discounts = metrics.get("discounts")
    discounts = (
        float(raw_discounts)
        if raw_discounts is not None
        else None
    )

    # ---------------------------------------------------------
    # Monthly sales
    # ---------------------------------------------------------

    monthly_report = []

    previous_sales = None

    for row in monthly:

        raw_sales = row.get("sales", row.get("revenue"))
        sales = float(raw_sales or 0)

        month = row.get(
            "month",
            "",
        )

        # Month-over-month growth.
        if previous_sales is None:
            growth = None

        elif previous_sales == 0:
            growth = None

        else:
            growth = round(
                (
                    (sales - previous_sales)
                    / previous_sales
                )
                * 100,
                2,
            )

        monthly_report.append(
            {
                "month": month,
                "revenue": round(
                    sales,
                    2,
                ),
                "revenue_growth_pct": growth,
            }
        )

        previous_sales = sales

    # ---------------------------------------------------------
    # Overall endpoint growth
    # ---------------------------------------------------------

    if len(monthly) >= 2:

        first_sales = float(monthly[0].get("sales", monthly[0].get("revenue")) or 0)
        last_sales = float(monthly[-1].get("sales", monthly[-1].get("revenue")) or 0)

        if first_sales != 0:

            endpoint_growth = round(
                (
                    (last_sales - first_sales)
                    / first_sales
                )
                * 100,
                2,
            )

        else:
            endpoint_growth = None

    else:
        endpoint_growth = None

    # ---------------------------------------------------------
    # Revenue trend
    # ---------------------------------------------------------

    if endpoint_growth is None:
        direction = "unavailable"

    elif endpoint_growth > 0:
        direction = "up"

    elif endpoint_growth < 0:
        direction = "down"

    else:
        direction = "flat"

    # ---------------------------------------------------------
    # Company workspace report
    # ---------------------------------------------------------

    return {
        "source": "company_workspace",

        "company": (
            ctx.get("profile", {}).get(
                "name",
                "Company",
            )
        ),

        "summary": {
            # Sales metrics
            "total_revenue": total_revenue,
            "orders": orders,
            "total_units": total_units,
            "average_order_value": average_order_value,
            "discounts": discounts,

            # These are intentionally unavailable.
            "total_expenses": None,
            "total_profit": None,
            "profit_margin_pct": None,

            "expense_ratio": {
                "ratio_pct": None,
                "assessment": "unavailable",
            },

            "revenue_trend": {
                "direction": direction,
                "change_pct": endpoint_growth,
            },

            "endpoint_growth_pct": endpoint_growth,

            "months_analyzed": len(
                monthly_report
            ),
        },

        "monthly_breakdown": monthly_report,

        "company_analysis": analysis,
    }


def generate_financial_report():
    """
    Generate the financial report.

    Priority:
    1. Active company workspace
    2. Legacy/default financial dataset
    """

    company_report = _company_financial_report()

    if company_report:
        return company_report

    # ---------------------------------------------------------
    # Legacy/default financial dataset
    # ---------------------------------------------------------

    df = load_financial_data()

    if df is None or df.empty:
        return None

    total_revenue = float(
        df["revenue"].sum()
    )

    total_expenses = float(
        df["expenses"].sum()
    )

    total_profit = calculate_profit(
        total_revenue,
        total_expenses,
    )

    profit_margin = calculate_profit_margin(
        total_revenue,
        total_profit,
    )

    expense_ratio = analyze_expense_ratio(
        total_expenses,
        total_revenue,
    )

    revenue_trend = analyze_revenue_trend(
        df[
            [
                "month",
                "revenue",
            ]
        ]
        .rename(
            columns={
                "month": "date",
            }
        )
        .to_dict(
            orient="records"
        )
    )

    monthly_report = []

    for index, row in df.iterrows():

        revenue = float(
            row["revenue"]
        )

        expenses = float(
            row["expenses"]
        )

        profit = calculate_profit(
            revenue,
            expenses,
        )

        margin = calculate_profit_margin(
            revenue,
            profit,
        )

        if index == 0:

            growth = None

        else:

            growth = calculate_growth_rate(
                revenue,
                float(
                    df.iloc[
                        index - 1
                    ]["revenue"]
                ),
            )

        monthly_report.append(
            {
                "month": row["month"],
                "revenue": revenue,
                "expenses": expenses,
                "profit": profit,
                "profit_margin_pct": round(
                    margin,
                    2,
                ),
                "revenue_growth_pct": (
                    round(
                        growth,
                        2,
                    )
                    if growth is not None
                    else None
                ),
            }
        )

    if len(monthly_report) >= 2:

        endpoint_growth_pct = round(
            calculate_growth_rate(
                monthly_report[-1]["revenue"],
                monthly_report[0]["revenue"],
            ),
            2,
        )

    else:
        endpoint_growth_pct = None

    return {
        "source": "default_financial_dataset",

        "summary": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "total_profit": total_profit,
            "profit_margin_pct": round(
                profit_margin,
                2,
            ),
            "expense_ratio": expense_ratio,
            "revenue_trend": revenue_trend,
            "endpoint_growth_pct": endpoint_growth_pct,
            "months_analyzed": len(df),
        },

        "monthly_breakdown": monthly_report,
    }