"""Deterministic marketing campaign analytics."""

from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MARKETING_FILE = DATA_DIR / "marketing.csv"


def load_marketing_data():
    """Load and validate marketing campaign data."""

    if not MARKETING_FILE.exists():
        raise FileNotFoundError(
            f"Marketing file not found: {MARKETING_FILE}"
        )

    df = pd.read_csv(MARKETING_FILE)

    required_columns = {
        "campaign",
        "impressions",
        "clicks",
        "conversions",
        "spend",
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            "Marketing CSV is missing required columns."
        )

    if df.empty:
        raise ValueError("Marketing CSV is empty.")

    numeric_columns = [
        "impressions",
        "clicks",
        "conversions",
        "spend",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    if df[numeric_columns].isna().any().any():
        raise ValueError(
            "Marketing data contains missing or invalid numeric values."
        )

    if (df[numeric_columns] < 0).any().any():
        raise ValueError(
            "Marketing metrics cannot be negative."
        )

    if df["campaign"].isna().any():
        raise ValueError("Campaign names cannot be missing.")

    if df["campaign"].duplicated().any():
        raise ValueError("Campaign names must be unique.")

    if (df["clicks"] > df["impressions"]).any():
        raise ValueError("Clicks cannot exceed impressions.")

    if (df["conversions"] > df["clicks"]).any():
        raise ValueError("Conversions cannot exceed clicks.")

    return df


def calculate_marketing_metrics():
    """Calculate campaign performance using Python."""

    df = load_marketing_data()

    df["ctr_pct"] = (
        df["clicks"]
        .div(df["impressions"].where(df["impressions"] != 0))
        .mul(100)
    )

    df["conversion_rate_pct"] = (
        df["conversions"]
        .div(df["clicks"].where(df["clicks"] != 0))
        .mul(100)
    )

    df["cost_per_conversion"] = (
        df["spend"]
        .div(df["conversions"].where(df["conversions"] != 0))
    )

    # Replace undefined calculations (NaN) with None.
    # This makes them JSON-compatible as null.
    df = df.astype(object).where(pd.notna(df), None)

    return df.to_dict(orient="records")