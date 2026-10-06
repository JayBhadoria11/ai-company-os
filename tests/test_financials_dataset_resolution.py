"""Financials must resolve the connected sales dataset (never the HR dataset)."""

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
import app.main as main
from app.core.company_context import get_company_dataset_record


SALES_CSV = (
    b"Row ID,Order ID,Order Date,Region,Product Name,Sales\n"
    b"1,O1,2024-01-05,North,Alpha,1000\n"
    b"2,O2,2024-01-15,South,Beta,100\n"
    b"3,O3,2024-02-10,North,Alpha,800\n"
    b"4,O4,2024-02-20,South,Beta,60\n"
)

HR_CSV = (
    b"EmployeeNumber,Department,Attrition,OverTime,MonthlyIncome,YearsAtCompany\n"
    b"1,Sales,Yes,Yes,5000,3\n"
    b"2,Sales,No,No,6000,5\n"
    b"3,HR,No,Yes,4000,2\n"
    b"4,Sales,No,No,7000,7\n"
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


def _seed_both():
    company_workspace.save_dataset_bytes("train.csv", SALES_CSV)
    company_workspace.save_dataset_bytes("HR_Analytics.csv", HR_CSV)


def test_financials_resolves_sales_dataset_not_generic(workspace):
    _seed_both()

    payload = main.company()

    assert payload["dataset"] == "train.csv"
    assert payload["dataset"] != "generic"

    record = get_company_dataset_record(require_sales=True)
    assert record is not None
    assert record["filename"] == "train.csv"


def test_financials_metrics_are_preserved(workspace):
    _seed_both()

    payload = main.company()

    assert payload["metrics"]["net_sales"] == 1960.0
    assert payload["metrics"]["orders"] == 4
    assert payload["metrics"]["aov"] == 490.0
    assert payload["rows"] == 4

    region_names = {region["name"] for region in payload["regions"]}
    assert region_names == {"North", "South"}


def test_hr_dataset_is_not_selected_for_financials(workspace):
    _seed_both()

    record = get_company_dataset_record(require_sales=True)

    assert record["filename"] == "train.csv"
    assert "HR" not in record["filename"]


def test_hr_only_workspace_has_no_financial_dataset(workspace):
    company_workspace.save_dataset_bytes("HR_Analytics.csv", HR_CSV)

    assert get_company_dataset_record(require_sales=True) is None

    payload = main.company()

    # The HR dataset must never be presented as the Financials dataset.
    assert payload["dataset"] != "HR_Analytics.csv"


def test_discount_limitation_wording_is_corrected(workspace):
    _seed_both()

    limitations = " ".join(main.company()["limitations"])

    assert "discounted net sales cannot be independently verified" in limitations
    assert "net sales equal gross sales" not in limitations


def test_financials_provenance_is_train_csv(workspace):
    _seed_both()

    record = get_company_dataset_record(require_sales=True)

    listed = {
        dataset["id"]: dataset["filename"]
        for dataset in company_workspace.list_datasets()
    }

    assert record["filename"] == "train.csv"
    assert listed[record["id"]] == "train.csv"


def test_profit_and_cost_limitations_preserved(workspace):
    _seed_both()

    limitations = " ".join(main.company()["limitations"]).lower()

    assert "profit is unavailable" in limitations
    assert "costs, cac, roi and profit margin" in limitations
