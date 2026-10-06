import pandas as pd
import pytest

from app.tools import marketing


@pytest.fixture
def sample_marketing_data():
    return pd.DataFrame(
        {
            "campaign": ["A", "B"],
            "impressions": [10000, 15000],
            "clicks": [500, 600],
            "conversions": [50, 45],
            "spend": [2500, 3000],
        }
    )


def test_marketing_metrics_calculation(monkeypatch, sample_marketing_data):
    monkeypatch.setattr(
        marketing,
        "load_marketing_data",
        lambda: sample_marketing_data.copy(),
    )

    result = marketing.calculate_marketing_metrics()

    assert result[0]["ctr_pct"] == 5.0
    assert result[0]["conversion_rate_pct"] == 10.0
    assert result[0]["cost_per_conversion"] == 50.0

    assert result[1]["ctr_pct"] == 4.0
    assert result[1]["conversion_rate_pct"] == 7.5
    assert result[1]["cost_per_conversion"] == pytest.approx(66.6666667)


def test_zero_denominators(monkeypatch):
    df = pd.DataFrame(
        {
            "campaign": ["Zero"],
            "impressions": [1000],
            "clicks": [0],
            "conversions": [0],
            "spend": [100],
        }
    )

    monkeypatch.setattr(
        marketing,
        "load_marketing_data",
        lambda: df.copy(),
    )

    result = marketing.calculate_marketing_metrics()

    assert result[0]["ctr_pct"] == 0
    assert result[0]["conversion_rate_pct"] is None
    assert result[0]["cost_per_conversion"] is None


def test_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(marketing, "MARKETING_FILE", tmp_path / "missing.csv")

    with pytest.raises(FileNotFoundError):
        marketing.load_marketing_data()


def test_missing_columns(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    pd.DataFrame(
        {
            "campaign": ["A"],
            "clicks": [10],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="missing required columns"):
        marketing.load_marketing_data()


def test_empty_csv(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    file_path.write_text(
        "campaign,impressions,clicks,conversions,spend\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="empty"):
        marketing.load_marketing_data()


def test_invalid_numeric_data(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    pd.DataFrame(
        {
            "campaign": ["A"],
            "impressions": ["invalid"],
            "clicks": [10],
            "conversions": [2],
            "spend": [100],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="invalid numeric"):
        marketing.load_marketing_data()


def test_clicks_cannot_exceed_impressions(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    pd.DataFrame(
        {
            "campaign": ["A"],
            "impressions": [100],
            "clicks": [120],
            "conversions": [10],
            "spend": [100],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="Clicks cannot exceed impressions"):
        marketing.load_marketing_data()


def test_conversions_cannot_exceed_clicks(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    pd.DataFrame(
        {
            "campaign": ["A"],
            "impressions": [100],
            "clicks": [20],
            "conversions": [25],
            "spend": [100],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="Conversions cannot exceed clicks"):
        marketing.load_marketing_data()


def test_negative_values_rejected(monkeypatch, tmp_path):
    file_path = tmp_path / "marketing.csv"

    pd.DataFrame(
        {
            "campaign": ["A"],
            "impressions": [100],
            "clicks": [20],
            "conversions": [5],
            "spend": [-100],
        }
    ).to_csv(file_path, index=False)

    monkeypatch.setattr(marketing, "MARKETING_FILE", file_path)

    with pytest.raises(ValueError, match="cannot be negative"):
        marketing.load_marketing_data()