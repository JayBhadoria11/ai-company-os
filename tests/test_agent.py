"""Tests for AI business analysis agent."""

import pytest

from app.core import agent


class TestRunBusinessAnalysis:

    def setup_method(self):
        agent.generate_financial_report = lambda: {
            "summary": {
                "total_revenue": 10000,
                "total_expenses": 6000,
                "total_profit": 4000,
                "profit_margin_pct": 40.0,
                "expense_ratio": {
                    "expense_ratio_pct": 60.0,
                    "status": "attention_needed",
                },
                "revenue_trend": {
                    "trend": "increasing",
                    "change_pct": 23.35,
                },
                "endpoint_growth_pct": 56.0,
                "months_analyzed": 6,
            },
            "monthly_breakdown": [],
        }

    def test_valid_response(self, monkeypatch):
        response = """
        {
            "executive_summary": "Business is profitable.",
            "key_findings": ["Revenue exceeds expenses."],
            "risks": ["Expenses may increase."],
            "recommended_actions": ["Monitor expenses."]
        }
        """

        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: response,
        )

        result = agent.run_business_analysis("Analyze business")

        assert result["insights"]["executive_summary"] == "Business is profitable."
        assert result["model"] == "NVIDIA Nemotron via Nebius"

    def test_invalid_json(self, monkeypatch):
        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: "This is not JSON",
        )

        with pytest.raises(ValueError, match="invalid JSON"):
            agent.run_business_analysis("Analyze business")

    def test_missing_required_field(self, monkeypatch):
        response = """
        {
            "executive_summary": "Business is profitable.",
            "key_findings": [],
            "risks": []
        }
        """

        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: response,
        )

        with pytest.raises(ValueError, match="missing"):
            agent.run_business_analysis("Analyze business")

    def test_non_dictionary_response(self, monkeypatch):
        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: '["not", "an", "object"]',
        )

        with pytest.raises(ValueError, match="JSON object"):
            agent.run_business_analysis("Analyze business")

    def test_wrong_list_type(self, monkeypatch):
        response = """
        {
            "executive_summary": "Business is profitable.",
            "key_findings": "This should be a list",
            "risks": [],
            "recommended_actions": []
        }
        """

        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: response,
        )

        with pytest.raises(ValueError, match="must be a list"):
            agent.run_business_analysis("Analyze business")

    def test_empty_response(self, monkeypatch):
        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: "",
        )

        with pytest.raises(ValueError, match="empty analysis"):
            agent.run_business_analysis("Analyze business")

    def test_invalid_summary_type(self, monkeypatch):
        response = """
        {
            "executive_summary": 123,
            "key_findings": [],
            "risks": [],
            "recommended_actions": []
        }
        """

        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: response,
        )

        with pytest.raises(ValueError, match="must be a string"):
            agent.run_business_analysis("Analyze business")

    def test_invalid_list_item_type(self, monkeypatch):
        response = """
        {
            "executive_summary": "Business is profitable.",
            "key_findings": [123],
            "risks": [],
            "recommended_actions": []
        }
        """

        monkeypatch.setattr(
            agent,
            "get_completion",
            lambda **kwargs: response,
        )

        with pytest.raises(ValueError, match="Every item"):
            agent.run_business_analysis("Analyze business")