from pathlib import Path

import pandas as pd

from app.core.company_analysis import analyze_sales_dataset


def test_generic_single_table_sales_schema(tmp_path):
    path = tmp_path / "sales.csv"
    pd.DataFrame(
        {
            "transaction_id": ["A", "B", "C", "D"],
            "date": ["2026-01-02", "2026-01-10", "2026-02-03", "2026-02-20"],
            "category": ["Phone", "Phone", "Laptop", "Laptop"],
            "country": ["IN", "IN", "US", "US"],
            "revenue": [100, 150, 400, 350],
        }
    ).to_csv(path, index=False)

    analysis = analyze_sales_dataset(path)

    assert analysis["dataset"] == "generic"
    assert analysis["metrics"]["net_sales"] == 1000.0
    assert analysis["metrics"]["total_units"] is None
    assert analysis["metrics"]["orders"] == 4
    assert analysis["metrics"]["average_order_value"] == 250.0
    assert analysis["metrics"]["discounts"] is None
    assert len(analysis["breakdowns"]["monthly"]) == 2
    assert analysis["breakdowns"]["products"][0]["name"] == "Laptop"
    assert analysis["breakdowns"]["regions"][0]["name"] == "US"


def test_apex_style_single_table_still_works(tmp_path):
    path = tmp_path / "apex.csv"
    pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "order_id": ["O1", "O2"],
            "product": ["A", "B"],
            "category": ["X", "Y"],
            "region": ["North", "South"],
            "units": [2, 3],
            "unit_price": [100, 200],
            "discount": [10, 20],
            "marketing_channel": ["Google", "Instagram"],
        }
    ).to_csv(path, index=False)

    analysis = analyze_sales_dataset(path)

    assert analysis["dataset"] == "apexmt"
    assert analysis["metrics"]["gross_sales"] == 800.0
    assert analysis["metrics"]["discounts"] == 30.0
    assert analysis["metrics"]["net_sales"] == 770.0
    assert analysis["metrics"]["orders"] == 2
    assert analysis["metrics"]["total_units"] == 5


def test_superstore_schema_preserves_unavailable_units_and_product_names(tmp_path):
    path = tmp_path / "train.csv"
    pd.DataFrame(
        {
            "Row ID": [1, 2, 3],
            "Order ID": ["A", "A", "B"],
            "Order Date": ["08/11/2017", "08/11/2017", "09/11/2017"],
            "Ship Date": ["11/11/2017"] * 3,
            "Region": ["South", "West", "West"],
            "Product ID": ["P1", "P2", "P3"],
            "Category": ["Furniture", "Technology", "Technology"],
            "Product Name": ["Chair", "Phone", "Laptop"],
            "Sales": [100, 200, 300],
        }
    ).to_csv(path, index=False)

    analysis = analyze_sales_dataset(path)

    assert analysis["rows"] == 3
    assert analysis["metrics"]["total_units"] is None
    assert analysis["metrics"]["orders"] == 2
    assert analysis["metrics"]["net_sales"] == 600.0
    assert analysis["breakdowns"]["products"][0]["name"] == "Laptop"
    assert all(item["units"] is None for item in analysis["breakdowns"]["products"])
    assert analysis["breakdowns"]["monthly"] == [
        {"month": "2017-08", "sales": 300.0},
        {"month": "2017-09", "sales": 300.0},
    ]
    assert not any("unit volume" in insight for insight in analysis["insights"])
