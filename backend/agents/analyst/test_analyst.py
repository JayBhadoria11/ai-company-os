from pathlib import Path

import pytest

from analyst import analyze_revenue


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "revenue.csv"


def test_analyze_revenue_returns_latest_product_changes():
    result = analyze_revenue(str(DATA_PATH))

    assert result["month"] == "March"
    assert result["previous_month"] == "February"
    assert isinstance(result["products"], list)
    assert len(result["products"]) == 3

    product_c = next(
        product for product in result["products"] if product["product"] == "Product C"
    )

    assert product_c["previous_revenue"] == 108000
    assert product_c["latest_revenue"] == 62000
    assert product_c["change"] == pytest.approx(-0.43)


def test_analyze_revenue_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        analyze_revenue(str(DATA_PATH.with_name("missing.csv")))
