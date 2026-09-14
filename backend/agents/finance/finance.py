from pathlib import Path

import pandas as pd

from backend.schemas.agent import AgentResponse, Finding


REQUIRED_COLUMNS = {"month", "category", "amount"}


def analyze_finances(file_path: str) -> dict:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Expenses CSV not found: {path}")

    df = pd.read_csv(path)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValueError(f"Expenses CSV is missing required columns: {columns}")

    if df.empty:
        raise ValueError("Expenses CSV does not contain any rows.")

    df = df.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="raise")

    month_order = df["month"].drop_duplicates().tolist()
    if len(month_order) < 2:
        raise ValueError("Expenses CSV must contain at least two months.")

    latest_month = month_order[-1]
    previous_month = month_order[-2]

    compared = df[df["month"].isin([previous_month, latest_month])]
    monthly_categories = (
        compared.groupby(["month", "category"], as_index=False)["amount"].sum()
    )

    previous = monthly_categories[
        monthly_categories["month"] == previous_month
    ].set_index("category")
    latest = monthly_categories[monthly_categories["month"] == latest_month].set_index(
        "category"
    )

    categories = sorted(set(previous.index) | set(latest.index))
    previous_total = int(previous["amount"].sum())
    latest_total = int(latest["amount"].sum())
    expense_change = latest_total - previous_total
    expense_change_percent = None
    if previous_total != 0:
        expense_change_percent = float(round(expense_change / previous_total, 2))

    category_results = []
    for category in categories:
        previous_amount = _amount_for_category(previous, category)
        latest_amount = _amount_for_category(latest, category)
        amount_change = latest_amount - previous_amount
        change = None
        if previous_amount != 0:
            change = float(round(amount_change / previous_amount, 2))

        category_results.append(
            {
                "category": category,
                "previous_amount": previous_amount,
                "latest_amount": latest_amount,
                "amount_change": amount_change,
                "change": change,
            }
        )

    largest_category_increase = max(
        category_results, key=lambda category: category["amount_change"]
    )

    return {
        "month": latest_month,
        "previous_month": previous_month,
        "previous_total_expenses": previous_total,
        "latest_total_expenses": latest_total,
        "expense_change": expense_change,
        "expense_change_percent": expense_change_percent,
        "categories": category_results,
        "largest_category_increase": largest_category_increase,
    }


def analyze_finances_as_agent(task_id: str, file_path: str) -> AgentResponse:
    analysis = analyze_finances(file_path)
    largest_increase = analysis["largest_category_increase"]
    expense_change_text = "unknown percentage"
    if analysis["expense_change_percent"] is not None:
        expense_change_text = f"{analysis['expense_change_percent']:.0%}"

    findings = [
        Finding(
            finding=(
                f"Total expenses changed by {expense_change_text} from "
                f"{analysis['previous_month']} to {analysis['month']}."
            ),
            evidence=(
                f"{analysis['previous_month']} expenses were "
                f"{analysis['previous_total_expenses']}; {analysis['month']} "
                f"expenses were {analysis['latest_total_expenses']}."
            ),
        ),
        Finding(
            finding=(
                f"{largest_increase['category']} had the largest expense increase."
            ),
            evidence=(
                f"{largest_increase['category']} increased by "
                f"{largest_increase['amount_change']} from "
                f"{analysis['previous_month']} to {analysis['month']}."
            ),
        ),
    ]

    recommendations = [
        (
            f"Review {largest_increase['category']} spending drivers before "
            "committing to a recovery plan."
        ),
        "Compare expense growth against revenue movement by category and month.",
    ]

    return AgentResponse(
        task_id=task_id,
        agent="finance",
        status="completed",
        findings=findings,
        metrics={
            "previous_month": analysis["previous_month"],
            "latest_month": analysis["month"],
            "previous_total_expenses": analysis["previous_total_expenses"],
            "latest_total_expenses": analysis["latest_total_expenses"],
            "expense_change": analysis["expense_change"],
            "expense_change_percent": analysis["expense_change_percent"],
            "categories": {
                category["category"]: {
                    "previous_amount": category["previous_amount"],
                    "latest_amount": category["latest_amount"],
                    "amount_change": category["amount_change"],
                    "change": category["change"],
                }
                for category in analysis["categories"]
            },
            "largest_category_increase": analysis["largest_category_increase"],
        },
        recommendations=recommendations,
    )


def _amount_for_category(df: pd.DataFrame, category: str) -> int:
    if category not in df.index:
        return 0

    return int(df.loc[category, "amount"])
