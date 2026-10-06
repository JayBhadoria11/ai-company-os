"""Tests for the idempotent demo workspace seeder.

Runs against an isolated temporary workspace/database so the real persisted
company state is never touched.
"""

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
from app.core import demo_seed


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


def test_seed_demo_populates_empty_workspace(isolated_workspace):
    result = demo_seed.seed_demo_workspace()

    assert result["status"] == "success"
    assert result["dataset"] == demo_seed.DEMO_DATASET_FILENAME

    datasets = company_workspace.list_datasets()
    assert len(datasets) == 1
    assert datasets[0]["filename"] == demo_seed.DEMO_DATASET_FILENAME

    profile = company_workspace.load_company_profile()
    assert profile["name"] == demo_seed.DEMO_PROFILE["name"]


def test_seed_demo_is_idempotent(isolated_workspace):
    first = demo_seed.seed_demo_workspace()
    second = demo_seed.seed_demo_workspace()

    assert first["status"] == "success"
    assert second["status"] == "skipped"

    # Seeding again must not duplicate or replace anything.
    assert len(company_workspace.list_datasets()) == 1


def test_seed_demo_respects_existing_profile(isolated_workspace):
    company_workspace.save_company_profile({"name": "Existing Co"})

    result = demo_seed.seed_demo_workspace()

    assert result["status"] == "skipped"
    assert company_workspace.list_datasets() == []
