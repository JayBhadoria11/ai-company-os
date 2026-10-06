from pathlib import Path

import pandas as pd
import pytest


def test_olist_monthly_order_id_join():
    root = Path(__file__).resolve().parents[1]
    data = root / "app" / "data" / "company_workspace" / "datasets"

    orders_file = data / "olist_orders_dataset.csv"
    items_file = data / "olist_order_items_dataset.csv"

    if not orders_file.exists() or not items_file.exists():
        pytest.skip(
            "Olist dataset is not bundled with this checkout "
            "(olist_orders_dataset.csv / olist_order_items_dataset.csv missing)."
        )

    orders = pd.read_csv(orders_file)
    items = pd.read_csv(items_file)
    merged = items.merge(
        orders[["order_id", "order_purchase_timestamp"]],
        on="order_id", how="left", validate="many_to_one"
    )
    merged["order_purchase_timestamp"] = pd.to_datetime(
        merged["order_purchase_timestamp"], errors="coerce"
    )
    monthly = (
        merged.dropna(subset=["order_purchase_timestamp"])
        .assign(month=lambda x: x["order_purchase_timestamp"].dt.to_period("M"))
        .groupby("month")["price"].sum()
    )
    assert len(merged) == 112650
    assert len(monthly) == 24
    assert round(float(monthly.sum()), 2) == 13591643.70
