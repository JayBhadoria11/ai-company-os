"""Tests for evidence classification and reasoning cleanup."""

import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core.company_context import build_company_dataset_evidence
from app.core.evidence_reasoning import (
    build_reasoning_pack,
    parse_growth_pct,
)


SALES_CSV = (
    b"Row ID,Order ID,Order Date,Region,Category,Sales\n"
    b"1,CA-1,01/05/2024,South,Furniture,100.0\n"
    b"2,CA-2,02/10/2024,North,Technology,200.0\n"
    b"3,CA-3,03/15/2024,South,Office Supplies,300.0\n"
    b"4,CA-4,04/20/2024,West,Furniture,400.0\n"
)

HR_CSV = (
    b"EmployeeNumber,Department,Attrition,OverTime,MonthlyIncome,YearsAtCompany,Gender,JobRole\n"
    b"1,Sales,Yes,Yes,5000,3,Female,Sales Executive\n"
    b"2,Sales,No,No,6000,5,Male,Sales Executive\n"
    b"3,HR,No,Yes,4000,2,Female,HR Specialist\n"
    b"4,Sales,No,No,7000,7,Male,Sales Executive\n"
)

VALIDATION_QUESTION = (
    "If we want to increase sales by 30% over the next year, can our current "
    "workforce support that growth, what are the biggest operational and "
    "staffing risks, and what should management prioritize first?"
)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    workspace_dir = tmp_path / "company_workspace"
    monkeypatch.setattr(company_workspace, "WORKSPACE_DIR", workspace_dir)
    monkeypatch.setattr(
        company_workspace, "UPLOAD_DIR", workspace_dir / "datasets"
    )
    monkeypatch.setattr(
        company_workspace,
        "PROFILE_PATH",
        workspace_dir / "company_profile.json",
    )
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    company_workspace.initialize_workspace()
    return tmp_path


def _seed():
    company_workspace.save_dataset_bytes("train.csv", SALES_CSV)
    company_workspace.save_dataset_bytes("HR_Analytics.csv", HR_CSV)


def _pack(query=VALIDATION_QUESTION):
    return build_reasoning_pack(
        query, build_company_dataset_evidence(query)
    )


def test_parse_growth_pct():
    assert parse_growth_pct(VALIDATION_QUESTION) == 30.0
    assert parse_growth_pct("What are our total sales?") is None


def test_growth_is_a_labelled_scenario_with_assumptions(workspace):
    _seed()
    pack = _pack()

    scenario = pack["calculated_scenario"]

    assert scenario["label"] == "CALCULATED SCENARIO"
    assert scenario["growth_pct"] == 30.0
    assert scenario["current_sales"] == 1000.0
    assert scenario["projected_sales"] == 1300.0
    assert any("approximately" in s for s in scenario["statements"])
    assert any(
        "average order value remains approximately constant" in assumption.lower()
        for assumption in scenario["assumptions"]
    )


def test_attrition_is_not_an_annual_forecast(workspace):
    _seed()
    pack = _pack()

    text = " ".join(
        fact["statement"] for fact in pack["verified_facts"]
    ).lower()

    assert "per year" not in text
    assert "annually" not in text

    assert any(
        "employees with attrition" in fact["statement"]
        for fact in pack["verified_facts"]
    )


def test_overtime_is_an_indicator_not_proof(workspace):
    _seed()
    pack = _pack()

    overtime_facts = [
        fact["statement"]
        for fact in pack["verified_facts"]
        if "overtime" in fact["statement"].lower()
    ]

    assert overtime_facts
    assert all(
        "recorded as working overtime" in statement
        for statement in overtime_facts
    )
    assert all(
        "insufficient capacity" not in statement
        or "not proof of insufficient capacity" in statement
        for statement in overtime_facts
    )


def test_capacity_conclusion_preserves_uncertainty(workspace):
    _seed()
    pack = _pack()

    summary = pack["executive_summary_draft"]

    assert "does not establish" in summary
    assert "cannot" in summary or "not directly measured" in summary
    assert "cannot sustain" not in summary.lower()


def test_recommendations_are_question_aware(workspace):
    _seed()
    pack = _pack()

    joined = " ".join(
        item["statement"] for item in pack["recommendations"]
    )

    assert "Sales workforce capacity and retention planning" in joined
    assert "20.63" not in joined  # small fixture rate, ensure not hardcoded
    assert "R&D" not in joined
    assert "Monitor expenses." not in joined


def test_key_insights_are_question_aware(workspace):
    _seed()
    pack = _pack()

    titles = [insight["title"] for insight in pack["key_insights"]]

    assert "GROWTH TARGET" in titles
    assert "WORKFORCE" in titles
    assert "SALES WORKFORCE RISK" in titles
    assert "OVERTIME" in titles
    assert "EVIDENCE GAP" in titles


def test_sales_only_question_keeps_financial_recommendation(workspace):
    _seed()

    query = "What are our total sales, number of orders, and average order value?"
    pack = build_reasoning_pack(query, build_company_dataset_evidence(query))

    statements = [item["statement"] for item in pack["recommendations"]]

    assert "Monitor expenses." in statements
    assert not any("workforce" in s.lower() for s in statements)


def test_commander_reasoning_output_is_labelled(workspace, monkeypatch):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "Executive summary text."

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    result = commander.run_commander_task("t-reason", VALIDATION_QUESTION)

    metrics = result["metrics"]
    reasoning = metrics["reasoning"]

    assert reasoning["calculated_scenario"]["label"] == "CALCULATED SCENARIO"
    assert reasoning["verified_facts"]
    assert reasoning["limitations"]

    # No annual forecast language anywhere in the deterministic pack.
    pack_text = " ".join(
        [f["statement"] for f in reasoning["verified_facts"]]
        + reasoning["executive_summary_draft"].split()
    ).lower()
    assert "per year" not in pack_text
    assert "annually" not in pack_text

    # Recommendations directly address workforce capacity and avoid R&D.
    recommendations = " ".join(result["recommendations"])
    assert "Sales workforce capacity and retention planning" in recommendations
    assert "R&D" not in recommendations
    assert "Monitor expenses." not in result["recommendations"]

    # Evidence taxonomy preserved for the UI / synthesis.
    synth = metrics["nvidia_synthesis"]
    assert synth["evidence_labels"] == [
        "VERIFIED FACT",
        "CALCULATED RESULT",
        "CALCULATED SCENARIO",
        "INFERENCE",
        "LIMITATION",
        "RECOMMENDATION",
    ]
    assert "does not establish" in synth["verified_summary"]

    # Prompt enforces the rules.
    prompt = captured["prompt"]
    assert "CALCULATED SCENARIO" in prompt
    assert "Never describe attrition as an annual" in prompt
    assert "never as proof of insufficient capacity" in prompt
    assert "do not contradict" in prompt.lower()


def test_commander_preserves_source_dataset_provenance(workspace, monkeypatch):
    _seed()

    monkeypatch.setattr(
        commander, "get_completion", lambda **kwargs: "summary"
    )

    result = commander.run_commander_task("t-prov", VALIDATION_QUESTION)

    sources = result["findings"][0]["evidence"]["source_datasets"]

    assert set(sources) == {"train.csv", "HR_Analytics.csv"}
