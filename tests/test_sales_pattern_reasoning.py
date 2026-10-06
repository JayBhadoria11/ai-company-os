"""Question-aware sales-pattern reasoning tests (no unrelated scenarios)."""

import json

import pytest

import app.core.commander as commander
import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core.company_context import build_company_dataset_evidence
from app.core.evidence_reasoning import build_reasoning_pack


SALES_CSV = (
    b"Row ID,Order ID,Order Date,Region,Product Name,Sales\n"
    b"1,O1,2024-01-05,North,Alpha,1000\n"
    b"2,O2,2024-01-15,South,Beta,100\n"
    b"3,O3,2024-02-10,North,Alpha,800\n"
    b"4,O4,2024-02-20,South,Beta,60\n"
    b"5,O5,2024-03-05,North,Alpha,600\n"
    b"6,O6,2024-03-15,South,Beta,20\n"
)

PATTERN_QUESTION = (
    "What are the strongest and weakest sales patterns in the current dataset "
    "across regions, products, and time, and what should management investigate "
    "first to improve sales performance?"
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


def _pack(query=PATTERN_QUESTION):
    return build_reasoning_pack(
        query, build_company_dataset_evidence(query)
    )


def _insights(pack):
    return {
        insight["title"]: insight["statement"]
        for insight in pack["key_insights"]
    }


def test_no_scenario_for_descriptive_sales_question(workspace):
    _seed()
    pack = _pack()

    assert pack["asks_for_scenario"] is False
    assert pack["calculated_scenario"] is None

    text = json.dumps(pack)

    assert "projected_sales" not in text
    assert "$2,939" not in text
    assert "6,399" not in text


def test_strongest_and_weakest_region_and_product(workspace):
    _seed()
    insights = _insights(_pack())

    assert "North" in insights["STRONGEST REGION"]
    assert "South" in insights["WEAKEST REGION"]
    assert "Alpha" in insights["STRONGEST PRODUCT"]
    assert "Beta" in insights["UNDERPERFORMING PRODUCT"]
    assert insights["UNDERPERFORMING PRODUCT"].startswith("Beta declined")


def test_time_analysis_is_present(workspace):
    _seed()
    pack = _pack()

    assert pack["sales_pattern"]["strongest_month"]["month"] == "2024-01"
    assert pack["sales_pattern"]["weakest_month"]["month"] == "2024-03"

    time_insight = _insights(pack)["TIME PATTERN"]

    assert "2024-01" in time_insight
    assert "2024-03" in time_insight

    result_text = " ".join(
        item["statement"] for item in pack["calculated_results"]
    )
    assert "Monthly net sales change" in result_text


def test_recommendation_is_question_specific(workspace):
    _seed()
    pack = _pack()

    statements = " ".join(
        item["statement"] for item in pack["recommendations"]
    )

    assert "South" in statements
    assert "underperforming product segment" in statements
    assert "2024-01" in statements
    assert "Monitor expenses" not in statements


def test_discount_limitation_wording_corrected(workspace):
    _seed()
    pack = _pack()

    limitations = " ".join(
        item["statement"] for item in pack["limitations"]
    )

    assert "discounted net sales cannot be independently verified" in limitations
    assert "net sales equal gross sales" not in limitations


def test_evidence_hierarchy_labels_preserved(workspace):
    _seed()
    pack = _pack()

    labels = set()

    for fact in pack["verified_facts"]:
        labels.add(fact["label"])
    for result in pack["calculated_results"]:
        labels.add(result["label"])
    for limitation in pack["limitations"]:
        labels.add(limitation["label"])
    for recommendation in pack["recommendations"]:
        labels.add(recommendation["label"]) if "label" in recommendation else None

    assert "VERIFIED FACT" in labels
    assert "CALCULATED RESULT" in labels
    assert "LIMITATION" in labels
    assert pack["calculated_scenario"] is None


def test_provenance_is_train_csv(workspace):
    _seed()
    pack = _pack()

    assert pack["provenance"] == ["train.csv"]


def test_commander_sales_pattern_output(workspace, monkeypatch):
    _seed()

    captured = {}

    def fake_completion(**kwargs):
        captured["prompt"] = kwargs.get("prompt")
        return "Executive summary text."

    monkeypatch.setattr(commander, "get_completion", fake_completion)

    result = commander.run_commander_task("t-pattern", PATTERN_QUESTION)

    metrics = result["metrics"]
    reasoning = metrics["reasoning"]

    assert reasoning["calculated_scenario"] is None
    assert reasoning["sales_pattern"]["weakest_region"]["name"] == "South"

    recommendations = " ".join(result["recommendations"])
    assert "South" in recommendations
    assert "Monitor expenses." not in result["recommendations"]

    insights = " ".join(metrics["nvidia_synthesis"]["key_insights"])
    assert "WEAKEST REGION" in insights
    assert "TIME PATTERN" in insights

    assert result["findings"][0]["evidence"]["source_datasets"] == ["train.csv"]

    prompt = captured["prompt"]
    assert "Do NOT introduce any growth, forecast" in prompt
    assert "strongest region" in prompt.lower()
    assert "weakest region" in prompt.lower()
