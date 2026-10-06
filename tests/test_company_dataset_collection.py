"""Regression tests: the dataset collection the React frontend consumes.

The React Company Workshop renders ``payload["datasets"]``. These tests assert
that the API always returns the complete collection in newest-first order and
that uploading a new dataset never removes an older one.
"""

import asyncio

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
import app.main as main


CSV_FILE1 = (
    b"date,order_id,product,region,units,unit_price,discount\n"
    b"2024-01-01,O1,Widget,North,2,10,0\n"
)
CSV_HR = (
    b"employee_id,department,location,employee_count\n"
    b"1,Sales,North,10\n"
)
CSV_FILE3 = (
    b"month,region,employees\n"
    b"2024-01,North,10\n"
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
    monkeypatch.setattr(
        company_workspace, "PROFILE_PATH", workspace / "company_profile.json"
    )
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    return workspace


def upload(filename, content):
    return asyncio.run(main.upload_company_dataset(FakeUpload(filename, content)))


def filenames(payload):
    return [item["filename"] for item in payload["datasets"]]


def test_collection_grows_newest_first_and_is_never_replaced(isolated_workspace):
    first = upload("File1.csv", CSV_FILE1)
    assert filenames(first) == ["File1.csv"]
    assert first["count"] == 1

    second = upload("HR_Analytics.csv", CSV_HR)
    assert filenames(second) == ["HR_Analytics.csv", "File1.csv"]
    assert second["count"] == 2
    assert second["active"]["filename"] == "HR_Analytics.csv"

    third = upload("File3.csv", CSV_FILE3)
    assert filenames(third) == ["File3.csv", "HR_Analytics.csv", "File1.csv"]
    assert third["count"] == 3
    assert third["active"]["filename"] == "File3.csv"

    # File1 must still exist on disk and in the API collection.
    assert (company_workspace.UPLOAD_DIR / "File1.csv").exists()

    # Simulate a page refresh: the persisted collection stays intact.
    refreshed = main.get_company_dataset()
    assert filenames(refreshed) == [
        "File3.csv",
        "HR_Analytics.csv",
        "File1.csv",
    ]


def test_individual_delete_removes_only_that_dataset(isolated_workspace):
    upload("File1.csv", CSV_FILE1)
    upload("HR_Analytics.csv", CSV_HR)
    upload("File3.csv", CSV_FILE3)

    payload = main.get_company_dataset()
    hr = next(
        item
        for item in payload["datasets"]
        if item["filename"] == "HR_Analytics.csv"
    )

    removed = main.remove_company_dataset(hr["id"])

    assert removed["status"] == "success"
    assert removed["removed"] == 1
    assert filenames(removed) == ["File3.csv", "File1.csv"]
    assert removed["has_dataset"] is True


def test_reset_workspace_empties_the_collection(isolated_workspace):
    upload("File1.csv", CSV_FILE1)
    upload("HR_Analytics.csv", CSV_HR)
    upload("File3.csv", CSV_FILE3)

    reset = main.reset_company_workspace()

    assert reset["status"] == "success"
    assert filenames(reset["workspace"]["dataset"]) == []
    assert reset["workspace"]["dataset"]["has_dataset"] is False
    assert main.get_company_dataset()["datasets"] == []
