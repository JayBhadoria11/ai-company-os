
"""Load and validate company financial data."""

from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[2] / "app" / "data"


def load_revenue_data():
    """Load monthly revenue records."""
    file_path = DATA_DIR / "revenue.csv"

    if not file_path.exists():
        raise FileNotFoundError(f"Revenue file not found: {file_path}")

    df = pd.read_csv(file_path)

    required_columns = {"month", "revenue"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Revenue CSV must contain month and revenue columns")

    if df.empty:
        raise ValueError("Revenue CSV is empty")

    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")

    if df["revenue"].isna().any():
        raise ValueError("Revenue contains missing or invalid values")

    if (df["revenue"] < 0).any():
        raise ValueError("Revenue cannot be negative")

    if df["month"].isna().any() or df["month"].duplicated().any():
        raise ValueError("Revenue contains missing or duplicate months")

    return df


def load_expense_data():
    """Load monthly expense records."""
    file_path = DATA_DIR / "expenses.csv"

    if not file_path.exists():
        raise FileNotFoundError(f"Expense file not found: {file_path}")

    df = pd.read_csv(file_path)

    required_columns = {"month", "expenses"}

    if not required_columns.issubset(df.columns):
        raise ValueError("Expenses CSV must contain month and expenses columns")

    if df.empty:
        raise ValueError("Expenses CSV is empty")

    df["expenses"] = pd.to_numeric(df["expenses"], errors="coerce")

    if df["expenses"].isna().any():
        raise ValueError("Expenses contain missing or invalid values")

    if (df["expenses"] < 0).any():
        raise ValueError("Expenses cannot be negative")

    if df["month"].isna().any() or df["month"].duplicated().any():
        raise ValueError("Expenses contain missing or duplicate months")

    return df


def load_financial_data():
    """Load and combine revenue and expenses by month."""
    revenue = load_revenue_data()
    expenses = load_expense_data()

    df = pd.merge(
        revenue,
        expenses,
        on="month",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    unmatched = df[df["_merge"] != "both"]

    if not unmatched.empty:
        raise ValueError(
            "Revenue and expense data must contain matching months"
        )

    df = df.drop(columns=["_merge"])
    df = df.sort_values("month").reset_index(drop=True)

    return df
