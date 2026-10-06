"""Tests for financial calculation tools."""

import pytest

from app.tools.financial import calculate_profit, calculate_profit_margin, calculate_growth_rate


class TestCalculateProfit:
    def test_normal(self):
        assert calculate_profit(100, 60) == 40.0

    def test_zero_expenses(self):
        assert calculate_profit(100, 0) == 100.0

    def test_zero_revenue(self):
        assert calculate_profit(0, 50) == -50.0

    def test_both_zero(self):
        assert calculate_profit(0, 0) == 0.0

    def test_negative_expenses(self):
        assert calculate_profit(100, -20) == 120.0

    def test_negative_revenue(self):
        assert calculate_profit(-50, 30) == -80.0


class TestCalculateProfitMargin:
    def test_normal(self):
        assert calculate_profit_margin(100, 20) == 20.0

    def test_zero_revenue(self):
        assert calculate_profit_margin(0, 10) == 0.0

    def test_zero_profit(self):
        assert calculate_profit_margin(100, 0) == 0.0

    def test_full_margin(self):
        assert calculate_profit_margin(100, 100) == 100.0

    def test_negative_profit(self):
        assert calculate_profit_margin(100, -20) == -20.0

    def test_negative_revenue_negative_profit(self):
        assert calculate_profit_margin(-100, -20) == 20.0


class TestCalculateGrowthRate:
    def test_normal_growth(self):
        assert calculate_growth_rate(150, 100) == 50.0

    def test_decline(self):
        assert calculate_growth_rate(80, 100) == -20.0

    def test_same_value(self):
        assert calculate_growth_rate(100, 100) == 0.0

    def test_zero_previous_positive_current(self):
        assert calculate_growth_rate(50, 0) == 100.0

    def test_zero_previous_zero_current(self):
        assert calculate_growth_rate(0, 0) == 0.0

    def test_zero_previous_negative_current(self):
        assert calculate_growth_rate(-50, 0) == 0.0

    def test_negative_previous_positive_current(self):
        assert calculate_growth_rate(50, -100) == 150.0

    def test_negative_previous_negative_current_less_magnitude(self):
        assert calculate_growth_rate(-50, -100) == 50.0

    def test_negative_previous_negative_current_more_magnitude(self):
        assert calculate_growth_rate(-20, -100) == 80.0