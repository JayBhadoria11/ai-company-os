"""Intelligence must consume ALL connected Company Workspace datasets."""

import io

import pandas as pd
import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core.company_context import (
    build_company_dataset_evidence,
    get_workspace_datasets,
    select_relevant_datasets,
)
from app.tools.workforce_analysis import analyze_workforce_dataframe


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


def test_workforce_analyzer_computes_hr_fields():
    frame = pd.read_csv(io.BytesIO(HR_CSV))

    result = analyze_workforce_dataframe(frame)

    assert result["domain"] == "workforce"
    assert result["headcount"] == 4
    assert result["attrition"]["attrition_rate_pct"] == 25.0
    assert result["overtime"]["overtime_rate_pct"] == 50.0
    assert result["departments"][0]["name"] == "Sales"
    assert result["departments"][0]["headcount"] == 3
    assert "attrition" in result["available_fields"]


def test_registry_classifies_and_selects_relevant_datasets(workspace):
    _seed()

    datasets = get_workspace_datasets()
    domains = {d["filename"]: d["domain"] for d in datasets}

    assert domains["train.csv"] == "sales"
    assert domains["HR_Analytics.csv"] == "workforce"

    sales_q = (
        "What are our total sales, number of orders, and average order value?"
    )
    selected = {d["filename"] for d in select_relevant_datasets(sales_q, datasets)}
    assert selected == {"train.csv"}

    hr_q = (
        "What are the main workforce risks in our company based on the HR dataset?"
    )
    selected = {d["filename"] for d in select_relevant_datasets(hr_q, datasets)}
    assert "HR_Analytics.csv" in selected
    assert "train.csv" not in selected

    cross_q = (
        "Can our current workforce support significant business growth, and what "
        "staffing risks could prevent us from achieving our sales targets?"
    )
    selected = {d["filename"] for d in select_relevant_datasets(cross_q, datasets)}
    assert selected == {"train.csv", "HR_Analytics.csv"}


def test_evidence_includes_workforce_fields(workspace):
    _seed()

    evidence = build_company_dataset_evidence(
        "What are the main workforce risks based on the HR dataset?"
    )

    assert evidence["source_datasets"] == ["HR_Analytics.csv"]

    payload = evidence["evidence"]["HR_Analytics.csv"]["evidence"]

    assert payload["attrition"]["attrition_rate_pct"] == 25.0
    assert payload["headcount"] == 4


def test_commander_uses_both_datasets_for_cross_question(workspace, monkeypatch):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "CROSS-DATASET ANALYSIS\nQUESTION 1\nANSWER\nVerified evidence."

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    result = commander.run_commander_task(
        "t-cross",
        "Can our current workforce support significant business growth, and what "
        "staffing risks could prevent us from achieving our sales targets?",
    )

    metrics = result["metrics"]
    used = {d["filename"] for d in metrics["datasets_used"]}

    assert used == {"train.csv", "HR_Analytics.csv"}
    assert "hr" in metrics["required_agents"]
    assert "HR_Analytics.csv" in captured["prompt"]
    assert "train.csv" in captured["prompt"]

    assert set(result["findings"][0]["evidence"]["source_datasets"]) == {
        "train.csv",
        "HR_Analytics.csv",
    }

    agents = {response["agent"] for response in metrics["agent_responses"]}
    assert agents == {"analyst", "hr"}


def test_hr_question_uses_workforce_evidence(workspace, monkeypatch):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "VERIFIED EVIDENCE"

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    result = commander.run_commander_task(
        "t-hr",
        "What are the main workforce risks in our company based on the HR dataset?",
    )

    assert "HR_Analytics.csv" in captured["prompt"]
    assert "attrition_rate_pct" in captured["prompt"]
    assert result["metrics"]["datasets_used"][0]["domain"] == "workforce"


def test_sales_question_uses_sales_dataset_and_dynamic_count(
    workspace, monkeypatch
):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "ANSWER"

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    commander.run_commander_task(
        "t-sales",
        "What are our total sales, number of orders, and average order value?",
    )

    assert "train.csv" in captured["prompt"]
    assert "6 QUESTIONS" not in captured["prompt"]
    assert "EXACTLY 1" in captured["prompt"]


def test_empty_question_placeholder_is_removed(workspace, monkeypatch):
    _seed()

    raw = (
        "QUESTION 1\nANSWER\nSales total 1000.\n\n"
        "QUESTION 2\nNo question was provided for this slot."
    )

    monkeypatch.setattr(commander, "get_completion", lambda **kwargs: raw)

    result = commander.run_commander_task(
        "t-sanitize", "What are our total sales?"
    )

    summary = result["metrics"]["nvidia_synthesis"]["executive_summary"]

    assert "No question was provided" not in summary
    assert "Sales total 1000." in summary


def test_missing_information_question_uses_both_datasets(
    workspace, monkeypatch
):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "ANSWER"

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    commander.run_commander_task(
        "t-missing",
        "What important information is missing from our current datasets that "
        "prevents you from making a reliable profitability and workforce-capacity "
        "decision?",
    )

    assert "train.csv" in captured["prompt"]
    assert "HR_Analytics.csv" in captured["prompt"]
