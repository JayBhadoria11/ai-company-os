"""Tests for the Company Workshop workspace APIs.

These call the FastAPI endpoint functions directly (no HTTP client required)
against an isolated temporary workspace and database so the real persisted
company state is never touched.
"""

import asyncio

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
import app.main as main


SAMPLE_CSV = (
    b"date,order_id,product,region,units,unit_price,discount\n"
    b"2024-01-01,O1,Widget,North,2,10,0\n"
    b"2024-01-02,O2,Gadget,South,1,20,1\n"
)


class FakeUpload:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "company_workspace"
    monkeypatch.setattr(company_workspace, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(company_workspace, "UPLOAD_DIR", workspace / "datasets")
    monkeypatch.setattr(company_workspace, "PROFILE_PATH", workspace / "company_profile.json")
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    return workspace


def upload(filename, content):
    return asyncio.run(main.upload_company_dataset(FakeUpload(filename, content)))


def test_profile_defaults_then_update(isolated_workspace):
    profile = main.get_company_profile()["profile"]
    assert profile["name"] == ""
    assert profile["currency"] == "USD"

    response = main.update_company_profile(
        {"name": "Acme AI", "industry": "SaaS", "revenue_target": "1000000"}
    )
    assert response["status"] == "success"
    assert response["profile"]["name"] == "Acme AI"
    assert response["profile"]["currency"] == "USD"

    reloaded = main.get_company_profile()["profile"]
    assert reloaded["name"] == "Acme AI"
    assert reloaded["revenue_target"] == "1000000"


def test_dataset_upload_get_and_delete(isolated_workspace):
    empty = main.get_company_dataset()
    assert empty["has_dataset"] is False

    uploaded = upload("sales.csv", SAMPLE_CSV)
    assert uploaded["status"] == "success"
    assert uploaded["count"] == 1
    assert uploaded["active"]["filename"] == "sales.csv"
    assert uploaded["active"]["rows"] == 2
    assert uploaded["active"]["columns"] == 7
    assert uploaded["preview"]["rows"][0]["product"] == "Widget"

    fetched = main.get_company_dataset()
    assert fetched["has_dataset"] is True
    assert fetched["active"]["filename"] == "sales.csv"

    removed = main.remove_company_dataset(fetched["active"]["id"])
    assert removed["status"] == "success"
    assert removed["removed"] == 1
    assert removed["has_dataset"] is False


def test_dataset_upload_replaces_same_filename(isolated_workspace):
    upload("sales.csv", SAMPLE_CSV)
    second = upload("sales.csv", SAMPLE_CSV)

    assert second["count"] == 1
    assert second["active"]["filename"] == "sales.csv"


def test_dataset_rejects_unsupported_type(isolated_workspace):
    rejected = upload("notes.txt", b"hello world")
    assert rejected["status"] == "error"
    assert "supported" in rejected["message"].lower()


def test_workspace_reflects_profile_and_dataset(isolated_workspace):
    main.update_company_profile({"name": "Acme AI", "industry": "Retail"})
    upload("sales.csv", SAMPLE_CSV)

    workspace = main.get_company_workspace()
    assert workspace["status"] == "success"
    assert workspace["active"] is True
    assert workspace["has_profile"] is True
    assert workspace["profile"]["name"] == "Acme AI"
    assert workspace["configuration"]["currency"] == "USD"
    assert workspace["objectives"]["revenue_target"] == ""
    assert workspace["dataset"]["has_dataset"] is True
    assert workspace["dataset"]["active"]["filename"] == "sales.csv"

    connected = {item["name"]: item["connected"] for item in workspace["connections"]}
    assert connected["Intelligence"] is True
    assert connected["Financials"] is True


def test_workspace_reset_clears_everything(isolated_workspace):
    main.update_company_profile({"name": "Acme AI", "revenue_target": "5000"})
    upload("sales.csv", SAMPLE_CSV)

    reset = main.reset_company_workspace()
    assert reset["status"] == "success"
    assert reset["workspace"]["active"] is False
    assert reset["workspace"]["dataset"]["has_dataset"] is False
    assert reset["workspace"]["profile"]["name"] == ""

    # No stale state remains after re-reading.
    assert main.get_company_profile()["profile"]["name"] == ""
    assert main.get_company_dataset()["has_dataset"] is False
    assert main.get_company_workspace()["active"] is False


def test_dataset_does_not_appear_in_normal_workspace_payload(isolated_workspace):
    upload("sales.csv", SAMPLE_CSV)
    workspace = main.get_company_workspace()

    # The workspace must expose metadata + a small preview, never the full rows.
    assert "rows" in workspace["dataset"]["active"]
    assert workspace["dataset"]["preview"]["preview_rows"] <= 8
