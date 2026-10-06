"""Tests for persisted Intelligence (Past Questions) storage.

Isolated to a temporary database/workspace so real persisted state is untouched.
"""

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
import app.main as main


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    workspace = tmp_path / "company_workspace"
    monkeypatch.setattr(company_workspace, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(company_workspace, "UPLOAD_DIR", workspace / "datasets")
    monkeypatch.setattr(company_workspace, "PROFILE_PATH", workspace / "company_profile.json")
    return tmp_path


def test_questions_are_newest_first_and_allow_duplicates(isolated_state):
    database.save_intelligence_question("How can I improve my sales?")
    database.save_intelligence_question("When was the company profitable?")
    database.save_intelligence_question("How can I improve my sales?")

    questions = database.get_intelligence_questions()

    assert [q["question"] for q in questions] == [
        "How can I improve my sales?",
        "When was the company profitable?",
        "How can I improve my sales?",
    ]
    # Every investigation event keeps its own id.
    assert len({q["id"] for q in questions}) == 3
    assert all(q["created_at"] for q in questions)


def test_investigate_persists_question(isolated_state, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: {"status": "success", "task_id": task_id},
    )

    response = main.investigate(
        main.InvestigationRequest(query="How can I improve my sales?")
    )

    assert response["status"] == "success"

    questions = database.get_intelligence_questions()

    assert len(questions) == 1
    assert questions[0]["question"] == "How can I improve my sales?"
    assert questions[0]["task_id"] == response["task_id"]
    assert questions[0]["status"] == "success"


def test_empty_investigation_does_not_persist(isolated_state):
    response = main.investigate(main.InvestigationRequest(query="   "))

    assert response["status"] == "error"
    assert database.get_intelligence_questions() == []


def test_questions_endpoint_returns_newest_first(isolated_state):
    database.save_intelligence_question("First question")
    database.save_intelligence_question("Second question")

    payload = main.intelligence_questions()

    assert payload["status"] == "success"
    assert payload["questions"][0]["question"] == "Second question"


def test_reset_workspace_clears_questions(isolated_state):
    database.save_intelligence_question("How can I improve my sales?")
    assert len(database.get_intelligence_questions()) == 1

    database.clear_company_workspace_state()

    assert database.get_intelligence_questions() == []


def test_reset_history_does_not_clear_questions(isolated_state):
    database.save_intelligence_question("How can I improve my sales?")

    # Reset History clears decision/audit history only.
    database.clear_analysis_history()

    questions = database.get_intelligence_questions()
    assert len(questions) == 1
    assert questions[0]["question"] == "How can I improve my sales?"


def test_delete_single_question_only_removes_that_question(isolated_state):
    first = database.save_intelligence_question("First question")
    second = database.save_intelligence_question("Second question")
    third = database.save_intelligence_question("Third question")

    assert database.delete_intelligence_question(second) is True

    remaining = database.get_intelligence_questions()
    assert [q["id"] for q in remaining] == [third, first]
    assert all(q["id"] != second for q in remaining)


def test_delete_nonexistent_question_returns_false(isolated_state):
    assert database.delete_intelligence_question(9999) is False


def test_delete_question_endpoint(isolated_state):
    question_id = database.save_intelligence_question("How can I improve my sales?")

    response = main.remove_intelligence_question(question_id)
    assert response["status"] == "success"
    assert database.get_intelligence_questions() == []

    # Deleting again reports a clear not-found error.
    missing = main.remove_intelligence_question(question_id)
    assert missing["status"] == "error"


def test_delete_question_does_not_touch_dataset_or_workspace(isolated_state):
    company_workspace.save_dataset_bytes(
        "sales.csv",
        b"date,order_id,product\n2024-01-01,O1,Widget\n",
    )
    question_id = database.save_intelligence_question("How can I improve my sales?")

    database.delete_intelligence_question(question_id)

    datasets = company_workspace.list_datasets()
    assert len(datasets) == 1
    assert datasets[0]["filename"] == "sales.csv"

