from pathlib import Path

import pandas as pd

from app.core.company_analysis import analyze_sales_dataset


def test_generic_dataset_uses_quantity_order_id_profit_and_percentage_discount(tmp_path):
    path = tmp_path / "superstore_like.csv"
    pd.DataFrame(
        {
            "Order ID": ["O1", "O1", "O2"],
            "Order Date": ["2018-01-01", "2018-01-01", "2018-02-01"],
            "Category": ["Technology", "Office Supplies", "Technology"],
            "Region": ["West", "East", "West"],
            "Sales": [100, 50, 200],
            "Quantity": [2, 3, 4],
            "Discount": [0.1, 0.2, 0.0],
            "Profit": [20, 5, 50],
        }
    ).to_csv(path, index=False)

    analysis = analyze_sales_dataset(path)
    metrics = analysis["metrics"]

    assert metrics["orders"] == 2
    assert metrics["total_units"] == 9
    assert metrics["net_sales"] == 350.0
    assert metrics["average_order_value"] == 175.0
    assert metrics["discounts"] is None
    assert metrics["discount_rate_pct"] == 10.0
    assert metrics["profit"] == 75.0
    assert analysis["breakdowns"]["monthly"] == [
        {"month": "2018-01", "sales": 150.0},
        {"month": "2018-02", "sales": 200.0},
    ]
