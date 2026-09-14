from pathlib import Path

import pandas as pd

from backend.schemas.agent import AgentResponse, Finding


REQUIRED_COLUMNS = {"month", "product", "revenue"}


def analyze_revenue(file_path: str) -> dict:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Revenue CSV not found: {path}")

    df = pd.read_csv(path)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"Revenue CSV is missing required columns: {columns}")

    if df.empty:
        raise ValueError("Revenue CSV does not contain any rows.")

    df = df.copy()
    df["revenue"] = pd.to_numeric(df["revenue"], errors="raise")

    month_order = df["month"].drop_duplicates().tolist()
    if len(month_order) < 2:
        raise ValueError("Revenue CSV must contain at least two months.")

    latest_month = month_order[-1]
    previous_month = month_order[-2]

    compared = df[df["month"].isin([previous_month, latest_month])]
    duplicate_rows = compared.duplicated(subset=["month", "product"], keep=False)
    if duplicate_rows.any():
        raise ValueError("Revenue CSV contains duplicate product rows for a month.")

    latest = compared[compared["month"] == latest_month].set_index("product")
    previous = compared[compared["month"] == previous_month].set_index("product")

    products = sorted(set(latest.index) & set(previous.index))
    if not products:
        raise ValueError(
            f"No matching products found for {previous_month} and {latest_month}."
        )

    results = []
    for product in products:
        latest_revenue = latest.loc[product, "revenue"]
        previous_revenue = previous.loc[product, "revenue"]

        if previous_revenue == 0:
            change = None
        else:
            change = float(
                round((latest_revenue - previous_revenue) / previous_revenue, 2)
            )

        results.append(
            {
                "product": product,
                "previous_revenue": int(previous_revenue),
                "latest_revenue": int(latest_revenue),
                "change": change,
            }
        )

    return {
        "month": latest_month,
        "previous_month": previous_month,
        "products": results,
    }


def analyze_revenue_as_agent(task_id: str, file_path: str) -> AgentResponse:
    analysis = analyze_revenue(file_path)
    products = analysis["products"]

    previous_total = sum(product["previous_revenue"] for product in products)
    latest_total = sum(product["latest_revenue"] for product in products)
    total_change = None
    if previous_total != 0:
        total_change = float(round((latest_total - previous_total) / previous_total, 2))

    product_metrics = {
        product["product"]: {
            "previous_revenue": product["previous_revenue"],
            "latest_revenue": product["latest_revenue"],
            "change": product["change"],
        }
        for product in products
    }

    findings = [
        Finding(
            finding=(
                f"{product['product']} revenue changed by {product['change']:.0%} "
                f"from {analysis['previous_month']} to {analysis['month']}."
            ),
            evidence=(
                f"{analysis['previous_month']} revenue was "
                f"{product['previous_revenue']}; {analysis['month']} revenue was "
                f"{product['latest_revenue']}."
            ),
        )
        for product in products
        if product["change"] is not None and product["change"] <= -0.1
    ]

    if not findings:
        findings.append(
            Finding(
                finding=(
                    f"No product revenue decline of 10% or more was found from "
                    f"{analysis['previous_month']} to {analysis['month']}."
                ),
                evidence=f"Analyzed {len(products)} products in the revenue dataset.",
            )
        )

    recommendations = [
        (
            f"Investigate {product['product']} retention, pipeline, and customer "
            "feedback before finalizing the recovery plan."
        )
        for product in products
        if product["change"] is not None and product["change"] <= -0.1
    ]

    if not recommendations:
        recommendations.append("Continue monitoring revenue by product each month.")

    return AgentResponse(
        task_id=task_id,
        agent="analyst",
        status="completed",
        findings=findings,
        metrics={
            "previous_month": analysis["previous_month"],
            "latest_month": analysis["month"],
            "previous_total_revenue": previous_total,
            "latest_total_revenue": latest_total,
            "total_change": total_change,
            "products": product_metrics,
        },
        recommendations=recommendations,
    )
