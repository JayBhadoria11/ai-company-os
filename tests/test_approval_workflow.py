"""End-to-end approval workflow via the FastAPI investigate/approval routes.

Covers: investigation persistence to /api/history, genuine pending approval
creation, approval retrieval, approve/reject persistence, duplicate prevention,
and workspace isolation. Isolated to a temporary DB/workspace so real persisted
state is untouched.
"""

import pytest

import app.core.company_workspace as company_workspace
import app.database.db as database
import app.main as main
from app.core.approval import get_approval, list_pending_approvals


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "history.db")
    workspace = tmp_path / "company_workspace"
    monkeypatch.setattr(company_workspace, "WORKSPACE_DIR", workspace)
    monkeypatch.setattr(
        company_workspace, "UPLOAD_DIR", workspace / "datasets"
    )
    monkeypatch.setattr(
        company_workspace,
        "PROFILE_PATH",
        workspace / "company_profile.json",
    )
    return tmp_path


def _fake_commander_result(task_id):
    return {
        "task_id": task_id,
        "agent": "commander",
        "status": "success",
        "findings": [],
        "metrics": {
            "nvidia_synthesis": {
                "executive_summary": "Executive summary text.",
                "key_insights": [],
                "risks": [],
                "recommended_actions": ["Recommended action one."],
            }
        },
        "recommendations": ["Recommended action one."],
    }


def _run(query):
    return main.investigate(main.InvestigationRequest(query=query))


def test_investigate_persists_to_history_and_creates_approval(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    response = _run("Analyze the company sales.")

    assert response["status"] == "success"
    task_id = response["task_id"]

    # Persisted so it appears in /api/history.
    analyses = database.get_recent_analyses(limit=5)
    assert len(analyses) >= 1
    assert analyses[0]["task_id"] == task_id
    assert analyses[0]["result"]["recommendations"] == ["Recommended action one."]

    # A genuine pending approval record exists.
    approval = get_approval(task_id)
    assert approval is not None
    assert approval["status"] == "pending"
    assert approval["summary"] == "Recommended action one."

    pending = list_pending_approvals()
    assert any(item["task_id"] == task_id for item in pending)


def test_approval_endpoint_returns_pending_record(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_id = _run("Analyze the company.")["task_id"]

    payload = main.approvals()

    assert payload["status"] == "success"
    assert any(item["task_id"] == task_id for item in payload["approvals"])


def test_decision_route_persists_approve_and_removes_from_pending(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_id = _run("Analyze the company.")["task_id"]

    result = main.decide_approval(
        task_id, main.ApprovalDecisionRequest(status="approved")
    )

    assert result["status"] == "success"
    assert result["approval"]["status"] == "approved"
    assert get_approval(task_id)["status"] == "approved"
    assert not any(
        item["task_id"] == task_id for item in list_pending_approvals()
    )


def test_decision_route_persists_reject(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_id = _run("Analyze the company.")["task_id"]

    result = main.decide_approval(
        task_id, main.ApprovalDecisionRequest(status="rejected")
    )

    assert result["status"] == "success"
    assert result["approval"]["status"] == "rejected"
    assert get_approval(task_id)["status"] == "rejected"
    assert not any(
        item["task_id"] == task_id for item in list_pending_approvals()
    )


def test_decision_route_rejects_invalid_status(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_id = _run("Analyze the company.")["task_id"]

    result = main.decide_approval(
        task_id, main.ApprovalDecisionRequest(status="maybe")
    )

    assert result["status"] == "error"
    assert get_approval(task_id)["status"] == "pending"


def test_retry_of_same_task_does_not_duplicate_approval(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_id = _run("Analyze the company.")["task_id"]

    # Simulate a retry/refresh re-running approval creation for the same task.
    from app.core.approval import create_approval_request

    create_approval_request(task_id, "Recommended action one.")

    matching = [
        item for item in list_pending_approvals() if item["task_id"] == task_id
    ]
    assert len(matching) == 1


def test_workspace_isolation_between_investigations(isolated, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_commander_task",
        lambda task_id, query: _fake_commander_result(task_id),
    )

    task_a = _run("First investigation.")["task_id"]
    task_b = _run("Second investigation.")["task_id"]

    # Each task gets its own approval record; approving one does not touch the
    # other's pending state.
    main.decide_approval(task_a, main.ApprovalDecisionRequest(status="approved"))

    assert get_approval(task_a)["status"] == "approved"
    assert get_approval(task_b)["status"] == "pending"

    pending_tasks = [item["task_id"] for item in list_pending_approvals()]
    assert task_a not in pending_tasks
    assert task_b in pending_tasks