from pathlib import Path

import pandas as pd


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
