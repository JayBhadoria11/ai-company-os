"""Tests for business analytics tools."""

import pytest

from app.tools.business_analytics import analyze_revenue_trend, analyze_expense_ratio


class TestAnalyzeRevenueTrend:
    def test_empty_input(self):
        result = analyze_revenue_trend([])
        assert result == {"direction": "stable", "change_pct": 0.0, "strength": "none"}

    def test_one_record(self):
        result = analyze_revenue_trend([{"date": "2024-01-01", "revenue": 100}])
        assert result == {"direction": "stable", "change_pct": 0.0, "strength": "none"}

    def test_increasing_revenue(self):
        data = [
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 150},
            {"date": "2024-03-01", "revenue": 200},
            {"date": "2024-04-01", "revenue": 250},
            {"date": "2024-05-01", "revenue": 300},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "growing"
        assert result["change_pct"] > 0

    def test_decreasing_revenue(self):
        data = [
            {"date": "2024-01-01", "revenue": 300},
            {"date": "2024-02-01", "revenue": 250},
            {"date": "2024-03-01", "revenue": 200},
            {"date": "2024-04-01", "revenue": 150},
            {"date": "2024-05-01", "revenue": 100},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "declining"
        assert result["change_pct"] < 0

    def test_stable_revenue(self):
        data = [
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 100},
            {"date": "2024-03-01", "revenue": 100},
            {"date": "2024-04-01", "revenue": 100},
            {"date": "2024-05-01", "revenue": 100},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "stable"

    def test_zero_first_half_average(self):
        data = [
            {"date": "2024-01-01", "revenue": 0},
            {"date": "2024-02-01", "revenue": 0},
            {"date": "2024-03-01", "revenue": 100},
            {"date": "2024-04-01", "revenue": 200},
        ]
        result = analyze_revenue_trend(data)
        assert result["change_pct"] == 0.0

    def test_date_sorting(self):
        data = [
            {"date": "2024-03-01", "revenue": 200},
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 150},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "growing"

    def test_stable_weak_change(self):
        data = [
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 104},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "stable"
        assert result["strength"] == "weak"

    def test_moderate_change(self):
        data = [
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 110},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "growing"
        assert result["strength"] == "moderate"

    def test_strong_growth(self):
        data = [
            {"date": "2024-01-01", "revenue": 100},
            {"date": "2024-02-01", "revenue": 120},
        ]
        result = analyze_revenue_trend(data)
        assert result["direction"] == "growing"
        assert result["strength"] == "strong"


class TestAnalyzeExpenseRatio:
    def test_zero_revenue(self):
        result = analyze_expense_ratio(50, 0)
        assert result == {"ratio_pct": 0.0, "assessment": "no revenue"}

    def test_healthy(self):
        result = analyze_expense_ratio(20, 100)
        assert result["ratio_pct"] == 20.0
        assert result["assessment"] == "healthy"

    def test_attention_needed(self):
        result = analyze_expense_ratio(50, 100)
        assert result["ratio_pct"] == 50.0
        assert result["assessment"] == "attention needed"

    def test_critical(self):
        result = analyze_expense_ratio(80, 100)
        assert result["ratio_pct"] == 80.0
        assert result["assessment"] == "critical"

    def test_exact_30_percent_boundary(self):
        result = analyze_expense_ratio(30, 100)
        assert result["ratio_pct"] == 30.0
        assert result["assessment"] == "attention needed"

    def test_exact_70_percent_boundary(self):
        result = analyze_expense_ratio(70, 100)
        assert result["ratio_pct"] == 70.0
        assert result["assessment"] == "critical"