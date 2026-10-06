from pathlib import Path

import pytest

import app.core.company_context as company_context

OLIST_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


def test_olist_workspace_analysis_uses_relational_joins():
    root = Path(__file__).resolve().parents[1]
    data = root / "app" / "data" / "company_workspace" / "datasets"

    missing = [name for name in OLIST_FILES if not (data / name).exists()]
    if missing:
        pytest.skip(
            "Olist dataset is not bundled with this checkout "
            f"(missing: {', '.join(missing)})."
        )

    datasets = [
        {"filename": p.name, "path": str(p), "metadata": {}}
        for p in data.glob("*.csv")
    ]

    original = company_context.get_active_company
    company_context.get_active_company = lambda: {
        "active": True,
        "profile": {"name": "Test"},
        "datasets": datasets,
        "analysis": None,
    }
    try:
        analysis = company_context.get_company_dataset_analysis()
    finally:
        company_context.get_active_company = original

    assert analysis["dataset"] == "olist"
    assert analysis["rows"] == 112650
    assert analysis["metrics"]["net_sales"] == 13591643.70
    assert analysis["metrics"]["discounts"] is None
    assert len(analysis["breakdowns"]["monthly"]) == 24
    assert round(sum(x["sales"] for x in analysis["breakdowns"]["monthly"]), 2) == 13591643.70
    assert len(analysis["breakdowns"]["regions"]) == 27
    assert len(analysis["breakdowns"]["products"]) == 72
    assert len(analysis["breakdowns"]["sellers"]) == 3095
